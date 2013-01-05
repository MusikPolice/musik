import cherrypy
import json

from musik import log
from musik.db import User

class UserAccounts():
	log = None
	exposed = True

	def __init__(self):
		self.log = log.Log(__name__)


	def POST(self):
		"""Creates a new user account with the specified user name and password"""
		cherrypy.response.headers['Content-Type'] = 'application/json'

		# ensure that a valid username and password were specified
		request = json.loads(cherrypy.request.body.read())
		self.log.info(request)
		username = request['username']
		password = request['password']

		if username is None or username == '':
			raise cherrypy.HTTPError(400, "Unspecified username")

		if password is None or password == '':
			raise cherrypy.HTTPError(400, "Unspecified password")

		# make sure that username doesn't already exist
		if cherrypy.request.db.query(User).filter(User.name == username).first() is not None:
			raise cherrypy.HTTPError(400, "Username already exists")

		# create the user
		user = User(username, password)
		cherrypy.request.db.add(user)
		cherrypy.request.db.commit()

		# this is an http 200 ok with no data
		return json.dumps(None)


	def GET(self):
		"""Returns a list of registered usernames"""
		cherrypy.response.headers['Content-Type'] = 'application/json'

		usernames = [u.name for u in cherrypy.request.db.query(User).all()]
		return json.dumps(usernames)