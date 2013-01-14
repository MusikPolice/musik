import datetime

import musik
import musik.config
from musik import log
from musik.db import DatabaseWrapper, User

import cherrypy
from cherrypy.process import plugins
from sqlalchemy.orm import scoped_session, sessionmaker


class SAEnginePlugin(plugins.SimplePlugin):
    """A plugin to help SQLAlchemy bind correctly to CherryPy threads.
    See http://www.defuze.org/archives/222-integrating-sqlalchemy-into-a-cherrypy-application.html
    """
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)
        self.sa_engine = None
        self.bus.subscribe(u'bind', self.bind)

    def start(self):
        self.db = DatabaseWrapper()
        self.sa_engine = self.db.get_engine()

    def stop(self):
        if self.sa_engine:
            self.sa_engine.dispose()
            self.sa_engine = None

    def bind(self, session):
        session.configure(bind=self.sa_engine)


class SATool(cherrypy.Tool):
    """A tool to help SQLAlchemy correctly dole out and clean up db connections
    See http://www.defuze.org/archives/222-integrating-sqlalchemy-into-a-cherrypy-application.html
    """
    def __init__(self):
        cherrypy.Tool.__init__(self, 'on_start_resource', self.bind_session, priority=20)
        self.session = scoped_session(sessionmaker(autoflush=True, autocommit=False))

    def _setup(self):
        cherrypy.Tool._setup(self)
        cherrypy.request.hooks.attach('on_end_resource', self.commit_transaction, priority=80)

    def bind_session(self):
        cherrypy.engine.publish('bind', self.session)
        cherrypy.request.db = self.session

    def commit_transaction(self):
        cherrypy.request.db = None
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise
        finally:
            self.session.remove()


class AuthTool(cherrypy.Tool):
    """This tool intercepts application requests and checks to see if the user is logged in.
    The cherrypy.request.authorized flag will be set with the results of the test."""
    log = None

    def __init__(self):
        self.log = log.Log(__name__)
        cherrypy.Tool.__init__(self, 'before_handler', self.auth_check, priority=30)

    def auth_check(self):
        """Returns true if the user's credentials have been stored in a session and they can
        be authenticated"""
        token = cherrypy.session.get('token')

        if token is not None:
            musik.web.api.users.check_password(token, None)

        if cherrypy.request.authorized:
            cherrypy.session['token'] = cherrypy.request.user.token
            return True
        else:
            return False


class WebService(object):
    """Application entry point for the web interface and restful API
    """
    log = None
    threads = None

    def __init__(self, threads):
        self.log = log.Log(__name__)
        self.threads = threads

        # Subscribe specifically to the 'stop' method passed by cherrypy.
        # This lets us cleanly stop all threads executed by the application.
        SAEnginePlugin(cherrypy.engine).subscribe()
        cherrypy.engine.subscribe("stop", self.stop_threads)

        # make a database transaction available to every request
        cherrypy.tools.db = SATool()

        # authenticate the user before every request
        cherrypy.tools.auth = AuthTool()

        app_config = {'/':
            {
                'tools.db.on': True,
                'tools.auth.on': True,
                'tools.sessions.on': True,
                'tools.staticdir.root': musik.config.get_root_directory(),
            },
            '/static':
            {
                # don't do authentication for static files
                'tools.auth.on': False,
                'tools.staticdir.on': True,
                'tools.staticdir.dir': "static",
            },
        }

        api_config = {
            '/':
            {
                'tools.db.on': True,
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),

                # all api calls require that the client passes HTTP basic authentication
                'tools.auth_basic.on': True,
                'tools.auth_basic.realm': 'api',
                'tools.auth_basic.checkpassword': musik.web.api.users.check_password,
            },

            '/users':
            {
                # anybody can list existing user accounts or create a new one
                'tools.auth_basic.on': False,
            }
        }

        cherrypy.tree.mount(musik.web.application.Musik(), '/', config=app_config)
        cherrypy.tree.mount(musik.web.api.API(), '/api', config=api_config)

    # a blocking call that starts the web application listening for requests
    def start(self, port=8080):
        cherrypy.config.update({'server.socket_host': '0.0.0.0', })
        cherrypy.config.update({'server.socket_port': port, })
        cherrypy.engine.start()
        cherrypy.engine.block()

    # stops the web application
    def stop(self):
        self.log.info(u"Trying to stop main web application")
        cherrypy.engine.stop()

    # stop all threads before closing out this thread
    def stop_threads(self):
        self.log.info(u"Trying to stop all threads")
        for thread in self.threads:
            if thread.is_alive():
                thread.stop()
