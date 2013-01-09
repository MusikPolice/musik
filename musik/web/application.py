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
		"""Performs a get request on the specified url and returns the results. If an error occurs, and empty
		list is returned"""
		self.log.info(u'_api_request was called with url %s' % url)

		r = requests.get(url)

		if r.status_code != 200:
			self.log.error(u'_api_request to url %s returned status code %d' % (url, int(r.status_code)))
			return []
		elif r.headers['content-type'] != 'application/json':
			self.log.error(u'_api_request to url %s returned an unsupported content-type %s' % (url, r.headers['content-type']))
			return []

		return json.loads(r.content)


	def _render(self, template_names, title='Musik', include_header=False, include_footer=False, **kwargs):
		"""Renders the specified template.
		template_names arg can be a single template name or a list of templates that
		will be rendered in order.
		"""
		result = []

		if not cherrypy.request.authorized:
			template_names = 'login.html'

		if type(template_names) != list:
			# Create one-element list
			template_names = [template_names]

		if include_header:
			template_names.insert(0, 'header.html')

		if include_footer:
			template_names.append('footer.html')

		# Make sure mandatory variables are always in kwargs
		# These will cause the page to fail miserably if not present
		kwargs['title'] = title

		for template in template_names:
			result.append(templates.get_template(template).render(**kwargs))

		return result


	@cherrypy.expose
	def index(self):
		"""Renders the index.html template along with a page header and footer."""
		self.log.info(u'index was called')
		return self._render('index.html', include_header=True, include_footer=True)


	@cherrypy.expose
	def main(self):
		"""Renders the index template without a header or footer."""
		self.log.info(u'main was called')
		return self._render('index.html')


	@cherrypy.expose
	def albums(self, id=None):
		"""Renders the albums template."""
		if id == None:
			self.log.info(u'albums was called with no id')

			albums = self._api_request('%s/api/albums/' % config.get_site_root())
			return self._render('albums.html', **{"albums": albums,})
		else:
			self.log.info(u'albums was called with id %d' % int(id))

			album = self._api_request('%s/api/albums/id/%s' % (config.get_site_root(), str(id)))[0]
			artist = self._api_request('%s/api/artists/id/%s' % (config.get_site_root(), album['artist_id']))[0]
			tracks = self._api_request('%s/api/tracks/album_id/%s' % (config.get_site_root(), album['id']))

			return self._render('album.html', **{"album": album, "artist": artist, "tracks": tracks,})


	@cherrypy.expose
	def artists(self, id=None):
		"""Renders the artists template.
		"""
		if id == None:
			self.log.info(u'artists was called with no id')

			artists = self._api_request('%s/api/artists/' % config.get_site_root())
			return self._render("artists.html", **{"artists": artists,})
		else:
			self.log.info(u'artists was called with id %d' % int(id))

			artist = self._api_request('%s/api/artists/id/%s' % (config.get_site_root(), str(id)))[0]
			albums = self._api_request('%s/api/albums/artist_id/%s' % (config.get_site_root(), str(id)))

			return self._render("artist.html", **{"artist": artist, "albums": albums,})


	@cherrypy.expose
	def importmedia(self):
		self.log.info(u'importmedia was called')
		return self._render("importmedia.html")

