import json
import sys
import os

import cherrypy
from cherrypy.process import wspbus, plugins

from mako.template import Template
from mako.lookup import TemplateLookup

import requests

from sqlalchemy.orm import scoped_session, sessionmaker

from musik import log
from musik.db import DatabaseWrapper
from musik.web import api


# Template looker-upper that handles loading and caching of mako templates
templates = TemplateLookup(directories=['templates'], module_directory='templates/compiled')


# A plugin to help SQLAlchemy bind correctly to CherryPy threads
# See http://www.defuze.org/archives/222-integrating-sqlalchemy-into-a-cherrypy-application.html
class SAEnginePlugin(plugins.SimplePlugin):
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

# A tool to help SQLAlchemy correctly dole out and clean up db connections
# See http://www.defuze.org/archives/222-integrating-sqlalchemy-into-a-cherrypy-application.html
class SATool(cherrypy.Tool):
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

# defines the web application that is the default client
class Musik:
	log = None
	api = api.API()

	def __init__(self):
		self.log = log.Log(__name__)


	def _api_request(self, url):
		self.log.info(u'_api_request was called with url %s' % url)

		r = requests.get(url)

		if r.status_code != 200:
			log.error(u'_api_request to url %s returned status code %d' % (url, int(r.status_code)))
			return False
		elif r.headers['content-type'] != 'application/json':
			log.error(u'_api_request to url %s returned an unsupported content-type %s' % (url, r.headers['content-type']))
			return False

		return json.loads(r.content)


	def _render(self, template_names, **kwargs):
		"""Renders the specified template.
        template_names arg can be a single template name or a list of templates that
        will be rendered in order.
        """
		result = []

		if type(template_names) != list:
			# Create one-element list
			template_names = [template_names]

		# Make sure mandatory variables are always in kwargs
		# These will cause the page to fail miserably if not present
		mandatory_vars = ('title', 'js_appends')
		for var in mandatory_vars:
			if var not in kwargs:
				kwargs[var] = u''

		for template in template_names:
			result.append(templates.get_template(template).render(**kwargs))

		return result


	def _render_page(self, template_names, **kwargs):
		"""Renders the specified template as a page complete with header and footer.
        template_names arg can be a single template name or a list of templates that
        will be rendered in order.
        Available kwargs are as follows
        * title - the title of the page that will appear in the title bar of the browser.
        * js_appends - a list of javascript files to append in the footer of the page.
        """
		if type(template_names) != list:
			# Create one-element list
			template_names = [template_names]

		# include the header, sidebar and footer in the template list
		template_names.insert(0, 'sidebar.html')
		template_names.insert(0, 'header.html')
		template_names.append('footer.html')

		return self._render(template_names, **kwargs)


	@cherrypy.expose
	def index(self):
		"""Renders the index.html template along with
		a page header and footer.
		"""
		self.log.info(u'index was called')

		return self._render_page("index.html", **{
			"title": "Home",
		})


	@cherrypy.expose
	def main(self):
		"""Renders the index template without a header or footer.
		"""
		self.log.info(u'main was called')

		return self._render("index.html")


	@cherrypy.expose
	def albums(self, id=None):
		"""Renders the albums template.
		"""
		if id == None:
			self.log.info(u'albums was called with no id')

			#TODO: make this url configurable!
			albums = self._api_request('http://localhost:8080/api/albums/')
			if albums:
				return self._render("albums.html", **{"albums": albums,})
		else:
			self.log.info(u'albums was called with id %d' % int(id))

			#TODO: make this url configurable!
			albums = self._api_request('http://localhost:8080/api/albums/id/' + id)
			if albums:
				return self._render("album.html", **{"album": albums[0],})


	@cherrypy.expose
	def artists(self, id=None):
		"""Renders the artists template.
		"""
		if id == None:
			self.log.info(u'artists was called with no id')

			#TODO: make this url configurable!
			artists = self._api_request('http://localhost:8080/api/artists/')
			if artists:
				return self._render("artists.html", **{"artists": artists,})
		else:
			self.log.info(u'artists was called with id %d' % int(id))

			#TODO: make this url configurable!
			artists = self._api_request('http://localhost:8080/api/artists/id/' + id)
			if artists:
				return self._render("artist.html", **{"artist": artists[0],})


	@cherrypy.expose
	def importmedia(self):
		self.log.info(u'importmedia was called')

		return self._render("importmedia.html", **{
			"js_appends": ['importmedia.js'],
		})


# starts the web app. this call will block until the server goes down
class MusikWebApplication:
	log = None
	threads = None

	def __init__(self, threads):
		self.log = log.Log(__name__)
		self.threads = threads

		# Subscribe specifically to the 'stop' method passed by cherrypy.
		# This lets us cleanly stop all threads executed by the application.
		SAEnginePlugin(cherrypy.engine).subscribe()
		cherrypy.engine.subscribe("stop", self.stop_threads)
		cherrypy.tools.db = SATool()

		config = {'/':
			{
				'tools.db.on': True,
				'tools.staticdir.root': os.path.dirname(os.path.realpath(sys.argv[0])),
			},
			'/static':
			{
				'tools.staticdir.on': True,
				'tools.staticdir.dir': "static",
			},
		}
		cherrypy.tree.mount(Musik(), '/', config=config)


	# a blocking call that starts the web application listening for requests
	def start(self, port=8080):
		cherrypy.config.update({'server.socket_host': '0.0.0.0',})
		cherrypy.config.update({'server.socket_port': port,})
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
