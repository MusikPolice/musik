import musik
import musik.config
from musik.web import api
from musik.web import application
from musik import log
from musik.db import DatabaseWrapper

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

        # a request handler that checks the request credentials
        cherrypy.tools.authorize = cherrypy._cptools.HandlerTool(api.users.check_password)

        app_config = {'/':
            {
                'tools.db.on': True,
            },
            '/static':
            {
                'tools.staticdir.root': musik.config.get_root_directory(),
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
                'tools.authorize.on': True,
            },

            '/users':
            {
                # anybody can list existing user accounts or create a new one
                'tools.authorize.on': False,
            }
        }

        cherrypy.tree.mount(application.Musik(), '/', config=app_config)
        cherrypy.tree.mount(api.API(), '/api', config=api_config)

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
