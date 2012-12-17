import json
import sys
import os

import cherrypy

from mako.template import Template
from mako.lookup import TemplateLookup

import requests

from musik import config
from musik import log


# Template looker-upper that handles loading and caching of mako templates
templates = TemplateLookup(directories=['templates'], module_directory='templates/compiled')

# defines the web application that is the default client
class Musik:
	log = None

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

		# include the header, footer in the template list
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

			albums = self._api_request('%s/api/albums/' % config.get_site_root())
			if albums:
				return self._render("albums.html", **{"albums": albums,})
		else:
			self.log.info(u'albums was called with id %d' % int(id))

			album = self._api_request('%s/api/albums/id/%s' % (config.get_site_root(), str(id)))[0]
			artist = self._api_request('%s/api/artists/id/%s' % (config.get_site_root(), album['artist_id']))[0]
			tracks = self._api_request('%s/api/tracks/album_id/%s' % (config.get_site_root(), album['id']))

			if album and artist and tracks:
				return self._render("album.html", **{"album": album, "artist": artist, "tracks": tracks,})


	@cherrypy.expose
	def artists(self, id=None):
		"""Renders the artists template.
		"""
		if id == None:
			self.log.info(u'artists was called with no id')

			artists = self._api_request('%s/api/artists/' % config.get_site_root())
			if artists:
				return self._render("artists.html", **{"artists": artists,})
		else:
			self.log.info(u'artists was called with id %d' % int(id))

			artist = self._api_request('%s/api/artists/id/%s' % (config.get_site_root(), str(id)))[0]
			albums = self._api_request('%s/api/albums/artist_id/%s' % (config.get_site_root(), str(id)))

			if artist and albums:
				return self._render("artist.html", **{"artist": artist, "albums": albums,})


	@cherrypy.expose
	def importmedia(self):
		self.log.info(u'importmedia was called')

		return self._render("importmedia.html", **{
			"js_appends": ['importmedia.js'],
		})

