#!/usr/bin/env python

import signal
import sys
import os

from musik import log
import musik.library.importer
import musik.web.application


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

	log.info(u'Starting worker threads')
	importThread = musik.library.importer.ImportThread()
	importThread.start()
	threads.append(importThread)

	# this is a blocking call
	log.info(u'Starting Web App')
	app = musik.web.application.MusikWebApplication(threads=threads)

	port = int(os.environ.get('PORT', '8080'))
	app.start(port=port)
