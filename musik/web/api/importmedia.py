from musik import log
from musik.db import ImportTask, LogEntry
from musik.util import DateTimeEncoder

import cherrypy
import json
import os

class Importer():
	log = None
	exposed = True

	def __init__(self):
		self.log = log.Log(__name__)

	def POST(self):
		"""Queues the specified path for import into the media library.
		"""
		cherrypy.response.headers['Content-Type'] = 'application/json'

		# get the path from the request and make sure that it exists on the local machine
		path = json.loads(cherrypy.request.body.read())['path']
		if not path or not os.path.isdir(path):
			raise cherrypy.HTTPError("404 Not Found", "Couldn't find the path " + str(path) + " on the target system")

		task = ImportTask(path)
		cherrypy.request.db.add(task)

		# this is an http 200 ok with no data
		return json.dumps(None)


	def GET(self):
		"""Gets the status of the importer"""

		cherrypy.response.headers['Content-Type'] = 'application/json'

		# query for the number of outstanding importer tasks as well as the task that is currently being processed
		current_task = cherrypy.request.db.query(ImportTask).filter(ImportTask.completed == None).order_by(ImportTask.created).first()
		if current_task is not None:
			current_task = current_task.as_dict()

		warnings = cherrypy.request.db.query(LogEntry).filter(LogEntry.classpath == 'musik.importer').filter(LogEntry.severity == 'WARNING').order_by(LogEntry.created).all()
		errors = cherrypy.request.db.query(LogEntry).filter(LogEntry.classpath == 'musik.importer').filter(LogEntry.severity == 'ERROR').order_by(LogEntry.created).all()

		status = {
			'outstanding_tasks': cherrypy.request.db.query(ImportTask).filter(ImportTask.completed == None).count(),
			'current_task': current_task,

			# each result set is turned into a list of json objects and then reversed so more recent messages come first
			'warnings': [warning.as_dict() for warning in warnings][::-1],
			'errors': [error.as_dict() for error in errors][::-1]
		}

		# using a special JSONEncoder that can handle datetime objects
		return json.dumps(status, cls=DateTimeEncoder)