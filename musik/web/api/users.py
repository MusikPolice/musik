import datetime
import json

import cherrypy
from cherrypy.lib import httpauth

from musik import log
from musik.db import DatabaseWrapper, User
from musik.util import DateTimeEncoder


def check_password():
    """If the supplied username and password are valid, returns False, indicating that the request has not been 
    handled, and other request handlers should be allowed to execute.
    
    If the supplied username and password are not valid, returns True, indicating that the request has been 
    handled, and other request handlers should not be allowed to execute. An HTTP 401/403 error will also be
    thrown in this case.
    
    The password argument is first treated as a session token. If this check fails, then it is treated as a 
    password. If either test passes, the cherrypy.request.authorized member is set to True and the 
    cherrypy.request.user member is set to the authenticated user."""
    db = DatabaseWrapper()
    session = db.get_session()

    if 'authorization' in cherrypy.request.headers:
        auth = httpauth.parseAuthorization(cherrypy.request.headers['authorization'])
        if auth is None:
            raise cherrypy.HTTPError(400, 'Invalid Authorization Header.')

        username = auth['username']
        password = auth['password']
        user = None

        # try to treat username as a session token
        if username is not None:
            user = session.query(User).filter(User.username == username and User.token == password and User.token_expires > datetime.datetime.utcnow()).first()
            if user is not None:
                user.update_token_expiry()
                session.commit()
                cherrypy.request.user = user

        # try to look up username and password in the database
        if user is None and username is not None and password is not None:
            user = session.query(User).filter(User.username == username).first()
            if user is not None and user.passhash == user.password_hash(username, password):
                cherrypy.request.user = user

        if user is not None:
            cherrypy.request.authorized = True
            # if the user was authorized, allow other page handlers to run
            return False
        else:
            cherrypy.request.authorized = False
            if cherrypy.request.headers['X-Requested-With'] == 'XMLHttpRequest':
                # if the request came from a browser, don't send a 401 because that will
                # trigger a shitty looking popup. Use a 403 instead.
                raise cherrypy.HTTPError(403, 'Invalid Credentials.')
            else:
                raise cherrypy.HTTPError(401, 'Invalid Credentials.')

            # the user was not authorized, suppress other page handlers from running
            return True
    else:
        raise cherrypy.HTTPError(400, 'Missing Authorization Header.')


class CurrentUser():
    exposed = True

    # GET /api/users/current
    def GET(self):
        """Gets information about the user that is currently logged in.
        Note that the password hash is not returned."""

        # throws an exception if auth fails
        check_password()

        # if auth succeeded, return info about the user
        if (cherrypy.request.authorized):        
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps(cherrypy.request.user.as_dict(), cls=DateTimeEncoder)


    # PUT /api/users/current
    @cherrypy.tools.json_out()
    def PUT(self):
        """Generates a new session token for the user credentials supplied in the basic authentication
        header and returns account information. This is analogous to logging in to the service. Note that 
        the users' password hash is not returned."""

        # throws an exception if auth fails
        check_password()

        # if auth succeeded, generate a new token for the user
        if (cherrypy.request.authorized):
            cherrypy.request.user.generate_token()
            cherrypy.request.db.commit()
            return json.dumps(cherrypy.request.user.as_dict(), cls=DateTimeEncoder)


class UserAccounts():
    """The methods in this class are NOT protected by HTTP authentication"""
    log = None
    exposed = True
    current = CurrentUser()

    def __init__(self):
        self.log = log.Log(__name__)

    #POST /api/users
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):
        """Creates a new user account with the specified user name and password"""
        cherrypy.response.headers['Content-Type'] = 'application/json'

        # ensure that a valid username and password were specified
        #request = json.loads(cherrypy.request.json)
        username = cherrypy.request.json['username']
        password = cherrypy.request.json['token']

        if username is None or username == '':
            raise cherrypy.HTTPError(400, "Unspecified username")

        if password is None or password == '':
            raise cherrypy.HTTPError(400, "Unspecified password")

        # make sure that username doesn't already exist
        if cherrypy.request.db.query(User).filter(User.username == username).first() is not None:
            raise cherrypy.HTTPError(400, "Username already exists")

        # create the user
        user = User(username, password)
        cherrypy.request.db.add(user)
        cherrypy.request.db.commit()

        # return the user to the calling function.
        # Note that the password hash is not returned
        return json.dumps(user.as_dict(), cls=DateTimeEncoder)

    def GET(self):
        """Returns a list of registered usernames"""
        cherrypy.response.headers['Content-Type'] = 'application/json'

        users = [u.as_dict_safe() for u in cherrypy.request.db.query(User).all()]
        return json.dumps(users, cls=DateTimeEncoder)
