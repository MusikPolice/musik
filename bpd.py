#!/usr/bin/env python

"""A clone of the Music Player Daemon (MPD) that plays music from a
Beets library. Attempts to implement a compatible protocol to allow
use of the wide range of MPD clients.
"""

import eventlet.api
import re
from string import Template
from beets import Library
import sys



DEFAULT_PORT = 6600
PROTOCOL_VERSION = '0.12.2'
BUFSIZE = 1024

HELLO = 'OK MPD %s' % PROTOCOL_VERSION
CLIST_BEGIN = 'command_list_begin'
CLIST_VERBOSE_BEGIN = 'command_list_ok_begin'
CLIST_END = 'command_list_end'
RESP_OK = 'OK'
RESP_CLIST_VERBOSE = 'list_OK'
RESP_ERR = 'ACK'

NEWLINE = "\n"

ERROR_NOT_LIST = 1
ERROR_ARG = 2
ERROR_PASSWORD = 3
ERROR_PERMISSION = 4
ERROR_UNKNOWN = 5
ERROR_NO_EXIST = 50
ERROR_PLAYLIST_MAX = 51
ERROR_SYSTEM = 52
ERROR_PLAYLIST_LOAD = 53
ERROR_UPDATE_ALREADY = 54
ERROR_PLAYER_SYNC = 55
ERROR_EXIST = 56



def debug(msg):
    print >>sys.stderr, msg



class Server(object):
    """A MPD-compatible music player server.
    
    The functions with the `cmd_` prefix are invoked in response to
    client commands. For instance, if the client says `status`,
    `cmd_status` will be invoked. The arguments to the client's commands
    are used as function arguments (*args). The functions should return
    a `Response` object.
    
    This is a generic superclass and doesn't support many commands.
    """
    
    def __init__(self, host, port=DEFAULT_PORT):
        """Create a new server bound to address `host` and listening
        on port `port`.
        """
        self.host, self.port = host, port
    
    def run(self):
        """Block and start listening for connections from clients. An
        interrupt (^C) closes the server.
        """
        self.listener = eventlet.api.tcp_listener((self.host, self.port))
        while True:
            try:
                sock, address = self.listener.accept()
            except KeyboardInterrupt:
                break # ^C ends the server.
            eventlet.api.spawn(Connection.handle, sock, self)

    def cmd_ping(self):
        return SuccessResponse()
    
    def cmd_commands(self):
        """Just lists the commands available to the user. For the time
        being, lists all commands because no authentication is present.
        """
        out = []
        for key in dir(self):
            if key.startswith('cmd_'):
                out.append('command: ' + key[4:])
        return SuccessResponse(out)
    
    def cmd_notcommands(self):
        """Lists all unavailable commands. Because there's currently no
        authentication, returns no commands.
        """
        return SuccessResponse()

class BGServer(Server):
    """A `Server` using GStreamer to play audio and beets to store its
    library.
    """
    
    def __init__(self, host, port=DEFAULT_PORT, libpath='library.blb'):
        super(BGServer, self).__init__(host, port)
        self.library = Library(libpath)

class Connection(object):
    """A connection between a client and the server. Handles input and
    output from and to the client.
    """
    
    def __init__(self, client, server):
        """Create a new connection for the accepted socket `client`.
        """
        self.client, self.server = client, server
    
    def send(self, data):
        """Send data, which is either a string or an iterable
        consisting of strings, to the client. A newline is added after
        every string.
        """
        if isinstance(data, basestring): # Passed a single string.
            lines = (data,)
        else: # Passed an iterable of strings (for instance, a Response).
            lines = data
        
        for line in lines:
            debug(line)
            self.client.sendall(line + NEWLINE)
    
    line_re = re.compile(r'([^\r\n]*)(?:\r\n|\n\r|\n|\r)')
    def lines(self):
        """A generator yielding lines (delimited by some usual newline
        code) as they arrive from the client.
        """
        buf = ''
        while True:
            # Dump new data on the buffer.
            chunk = self.client.recv(BUFSIZE)
            if not chunk: break # EOF.
            buf += chunk
            
            # Clear out and yield any lines in the buffer.
            while True:
                match = self.line_re.match(buf)
                if not match: break # No lines remain.
                yield match.group(1)
                buf = buf[match.end():] # Remove line from buffer.
    
    def run(self):
        """Send a greeting to the client and begin processing commands
        as they arrive. Blocks until the client disconnects.
        """
        self.send(HELLO)
        
        clist = None # Initially, no command list is being constructed.
        for line in self.lines():
            debug(line)
               
            if clist is not None:
                # Command list already opened.
                if line == CLIST_END:
                    self.send(clist.run(self.server))
                    clist = None
                else:
                    clist.append(Command(line))
            
            elif line == CLIST_BEGIN or line == CLIST_VERBOSE_BEGIN:
                # Begin a command list.
                clist = CommandList([], line == CLIST_VERBOSE_BEGIN)
                
            else:
                # Ordinary command.
                self.send(Command(line).run(self.server))
    
    @classmethod
    def handle(cls, client, server):
        """Creates a new `Connection` for `client` and `server` and runs
        it.
        """
        cls(client, server).run()



class Command(object):
    """A command issued by the client for processing by the server.
    """
    
    command_re = re.compile(r'^([^ \t]+)[ \t]*')
    arg_re = re.compile(r'"((?:\\"|[^"])+)"|([^ \t"]+)')
    
    def __init__(self, s):
        """Creates a new `Command` from the given string, `s`, parsing
        the string for command name and arguments.
        """
        command_match = self.command_re.match(s)
        self.name = command_match.group(1)
        arg_matches = self.arg_re.findall(s[command_match.end():])
        self.args = [m[0] or m[1] for m in arg_matches]
        
    def run(self, server):
        """Executes the command on the given `Sever`, returning a
        `Response` object.
        """
        func_name = 'cmd_' + self.name
        if hasattr(server, func_name):
            return getattr(server, func_name)(*self.args)
        else:
            return ErrorResponse(ERROR_UNKNOWN, self.name, 'unknown command')

class CommandList(list):
    """A list of commands issued by the client for processing by the
    server. May be verbose, in which case the response is delimited, or
    not. Should be a list of `Command` objects.
    """
    def __init__(self, sequence=None, verbose=False):
        """Create a new `CommandList` from the given sequence of
        `Command`s. If `verbose`, this is a verbose command list.
        """
        if sequence:
            for item in sequence:
                self.append(item)
        self.verbose = verbose

    def run(self, server):
        """Execute all the commands in this list, returning a list of
        strings to be sent as a response.
        """
        out = []

        for i, command in enumerate(self):
            resp = command.run(server)
            out.extend(resp.items)

            # If the command failed, stop executing and send the completion
            # code for this command.
            if isinstance(resp, ErrorResponse):
                resp.index = i # Give the error the correct index.
                break

            # Otherwise, possibly send the output delimeter if we're in a
            # verbose ("OK") command list.
            if self.verbose:
                out.append(RESP_CLIST_VERBOSE)

        # Give a completion code matching that of the last command (correct
        # for both success and failure).
        out.append(resp.completion())

        return out



class Response(object):
    """A result of executing a single `Command`. A `Response` is
    iterable and consists of zero or more lines of response data
    (`items`) and a completion code. It is an abstract class.
    """
    def __init__(self, items=None):
        self.items = (items if items else [])
    def __iter__(self):
        """Iterate through the `Response`'s items and then its
        completion code."""
        return iter(self.items + [self.completion()])
    def completion(self):
        """Returns the completion code of the response."""
        raise NotImplementedError

class ErrorResponse(Response):
    """A result of a command that fails.
    """
    template = Template('$resp [$code@$index] {$cmd_name} $message')
    
    def __init__(self, code, cmd_name, message, index=0, items=None):
        """Create a new `ErrorResponse` for error code `code`
        resulting from command with name `cmd_name`. `message` is an
        explanatory error message, `index` is the index of a command
        in a command list, and `items` is the additional data to be
        send to the client.
        """
        super(ErrorResponse, self).__init__(items)
        self.code, self.index, self.cmd_name, self.message = \
             code,      index,      cmd_name,      message
    
    def completion(self):
        return self.template.substitute({'resp':     RESP_ERR,
                                         'code':     self.code,
                                         'index':    self.index,
                                         'cmd_name': self.cmd_name,
                                         'message':  self.message
                                       })

class SuccessResponse(Response):
    """A result of a command that succeeds.
    """
    def completion(self):
        return RESP_OK



if __name__ == '__main__':
    BGServer('0.0.0.0', 6600, 'library.blb').run()