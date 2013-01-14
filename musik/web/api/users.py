import cherrypy
import datetime
import json

from musik import log
from musik.db import DatabaseWrapper, User
from musik.util import DateTimeEncoder


def check_password(realm, username, password):
    """Returns true if the supplied username and password are valid.
    The username is first tested as a session token. On failure, it is tested as a username.
    If either test passes, the cherrypy.request.authorized member is set to True and the
    cherrypy.request.user member is set to the authenticated user."""
    db = DatabaseWrapper()
    session = db.get_session()
    logg = log.Log(__name__)

    if username is not None:
        logg.info('AuthTool token=%s' % username)
        user = session.query(User).filter(User.token == username and User.token_expires > datetime.datetime.utcnow()).first()
        if user is not None:
            user.update_token_expiry()
            session.commit()
            cherrypy.request.user = user

    if cherrypy.request.user is None and username is not None and password is not None:
        logg.info('AuthTool username=%s, password=%s' % (username, password))
        user = session.query(User).filter(User.name == username).first()
        if user is not None and user.passhash == user.password_hash(username, password):
            cherrypy.request.user = user

    if cherrypy.request.user is not None:
        cherrypy.request.authorized = True
        return True
    else:
        cherrypy.request.authorized = False
        return False


class CurrentUser():
    exposed = True

    def GET(self):
        """Gets information about the user that is currently logged in.
        Note that the password hash is not returned."""
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps(cherrypy.request.user.as_dict(), cls=DateTimeEncoder)

    def PUT(self):
        """Generates a new session token for the user that was authenticated in
        the pre-request hook. Returns account information. Note that the password
        hash is not returned."""
        cherrypy.response.headers['Content-Type'] = 'application/json'
        cherrypy.request.user.generate_token()
        cherrypy.request.db.commit()
        return json.dumps(cherrypy.request.user.as_dict(), cls=DateTimeEncoder)


class UserAccounts():
    """The methods in this class are NOT protected by HTTP authentication"""
    log = None
    exposed = True

    def __init__(self):
        self.log = log.Log(__name__)

    def POST(self):
        """Creates a new user account with the specified user name and password"""
        cherrypy.response.headers['Content-Type'] = 'application/json'

        # ensure that a valid username and password were specified
        request = json.loads(cherrypy.request.body.read())
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

        # return the user to the calling function.
        # Note that the password hash is not returned
        return json.dumps(user.as_dict, cls=DateTimeEncoder)

    def GET(self):
        """Returns a list of registered usernames"""
        cherrypy.response.headers['Content-Type'] = 'application/json'

        usernames = [u.name for u in cherrypy.request.db.query(User).all()]
        return json.dumps(usernames)
