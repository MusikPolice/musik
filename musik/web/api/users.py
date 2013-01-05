import cherrypy
import json

from musik import log
from musik.db import DatabaseWrapper, User
from musik.util import DateTimeEncoder


def check_password(realm, username, password):
	"""Verifies that the supplied username and password are valid.
	If so, a username header is added to the request object"""
	db = DatabaseWrapper()
	session = db.get_session()

	user1 = session.query(User).filter(User.name == username).first()
	if user1 is None:
		# bad username
		return False

	user2 = User(username, password)
	if user1.passhash == user2.passhash:
		# valid user
		cherrypy.request.headers['username'] = username
		return True
	else:
		# bad password
		return False


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


class CurrentUser():
	log = None
	exposed = True

	def __init__(self):
		self.log = log.Log(__name__)

	def GET(self):
		"""Gets information about the currently logged in user"""
		cherrypy.response.headers['Content-Type'] = 'application/json'

		user = cherrypy.request.db.query(User).filter(User.name == cherrypy.request.headers['username']).first()
		return json.dumps(user.as_dict(), cls=DateTimeEncoder)
