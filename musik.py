#!/usr/bin/env python

import signal
import sys

from musik import config
from musik import log
import musik.audiotranscode
import musik.importer
import musik.web


# cleans up and safely stops the application
def cleanup(signum=None, frame=None):
    global log, importThread, app

    if type(signum) == type(None):
        pass
    else:
        log.info(u'Signal %i caught, saving and exiting...' % int(signum))

    log.info(u'Stopping worker threads')
    if importThread != None:
        importThread.stop()
        importThread.join(5)
        if importThread.isAlive():
            log.error(u'Failed to clean up importThread')

    log.info(u'Stopping CherryPy Engine')
    app.stop()

    log.info(u'Clean up complete')
    sys.exit(0)


# application entry - starts the database connection and dev server
if __name__ == '__main__':
    global log, importThread, app

    threads = []

    log = log.Log(__name__)

    # TODO: also register for CherryPy shutdown messages
    log.info(u'Registering for shutdown signals')
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
        signal.signal(sig, cleanup)

    # start worker threads
    log.info(u'Starting worker threads')
    importThread = musik.importer.ImportThread()
    importThread.start()
    threads.append(importThread)

    # query audiotranscode for available codecs
    transcode = musik.audiotranscode.AudioTranscode()
    row_format = "{:>10}" * 3
    log.info(u'Supported Encoders:')
    log.info(row_format.format('ENCODER', 'INSTALLED', 'FILETYPE'))
    for enc in transcode.Encoders:
        avail = 'yes' if enc.available() else 'no'
        log.info(row_format.format(enc.command[0], avail, enc.filetype))

    log.info(u'Supported Decoders:')
    log.info(row_format.format('ENCODER', 'INSTALLED', 'FILETYPE'))
    for dec in transcode.Decoders:
        avail = 'yes' if dec.available() else 'no'
        log.info(row_format.format(dec.command[0], avail, dec.filetype))

    # this is a blocking call
    log.info(u'Starting Web App')
    app = musik.web.WebService(threads=threads)

    # start the web app
    port = config.get_server_port()
    app.start(port=port)
