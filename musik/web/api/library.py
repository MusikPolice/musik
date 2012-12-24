from musik import log

import cherrypy
from musik.db import Album, Artist, Disc, Track
import musik.web.api.library
from musik.util import DateTimeEncoder

import json
import random

class Albums():
	log = None
	exposed = True

	def __init__(self):
		self.log = log.Log(__name__)

	def GET(self, *params):
		"""Assembles an album query by appending query parameters as filters.
		The result is a query that satisfies all of the parameters that were
		passed on the url string.
		Returns the results of the query sorted by title_sort property
		"""

		cherrypy.response.headers['Content-Type'] = 'application/json'

		#get the set of fields that makes up a Album object
		fields = {c.name: c for c in Album.__table__.columns}

		#split the query into key:value pairs
		query = []
		for index in range(0, len(params) - 1, 2):
			query.append(dict([(params[index],params[index + 1])]))

		self.log.info(u'queryAlbums called with params %s' % unicode(query))

		q = cherrypy.request.db.query(Album)

		for d in query:
			key = d.keys()[0]
			value = d[key]

			if str(fields[key].type) == 'VARCHAR':
				# allow for partial string matching
				q = q.filter(fields[key].like('%' + value + '%'))
			else:
				# all other data types must be exact matches
				q = q.filter(fields[key] == value)

		album_list = []
	 	for a in q.order_by(Album.title_sort).all():
	 		album_list.append(a.as_dict())
		return json.dumps(album_list)


class Artists():
	log = None
	exposed = True

	def __init__(self):
		self.log = log.Log(__name__)

	def GET(self, *params):
		"""Assembles an artist query by appending query parameters as filters.
		The result is a query that satisfies all of the parameters that were
		passed on the url string.
		Returns the results of the query sorted by name_sort property
		"""

		cherrypy.response.headers['Content-Type'] = 'application/json'

		#get the set of fields that makes up an Artist object
		fields = {c.name: c for c in Artist.__table__.columns}

		#split the query into key:value pairs
		query = []
		for index in range(0, len(params) - 1, 2):
			query.append(dict([(params[index],params[index + 1])]))

		self.log.info(u'queryArtists called with params %s' % unicode(query))

		q = cherrypy.request.db.query(Artist)
		for d in query:
			key = d.keys()[0]
			value = d[key]

			if str(fields[key].type) == 'VARCHAR':
				# allow for partial string matching
				q = q.filter(fields[key].like('%' + value + '%'))
			else:
				# all other data types must be exact matches
				q = q.filter(fields[key] == value)

		artist_list = []
	 	for a in q.order_by(Artist.name_sort).all():
	 		artist_list.append(a.as_dict())
		return json.dumps(artist_list)


class Discs():
	log = None
	exposed = True

	def __init__(self):
		self.log = log.Log(__name__)

	def GET(self, *params):
		"""Assembles an disc query by appending query parameters as filters.
		The result is a query that satisfies all of the parameters that were
		passed on the url string.
		Returns the results of the query sorted by id property
		TODO: sort by album
		"""

		cherrypy.response.headers['Content-Type'] = 'application/json'

		#get the set of fields that makes up a Disc object
		fields = {c.name: c for c in Disc.__table__.columns}

		#split the query into key:value pairs
		query = []
		for index in range(0, len(params) - 1, 2):
			query.append(dict([(params[index],params[index + 1])]))

		self.log.info(u'queryDiscs called with params %s' % unicode(query))

		q = cherrypy.request.db.query(Disc)
		for d in query:
			key = d.keys()[0]
			value = d[key]

			if str(fields[key].type) == 'VARCHAR':
				# allow for partial string matching
				q = q.filter(fields[key].like('%' + value + '%'))
			else:
				# all other data types must be exact matches
				q = q.filter(fields[key] == value)

		disc_list = []
	 	for d in q.order_by(Disc.id).all():
	 		disc_list.append(d.as_dict())
		return json.dumps(disc_list)


class Tracks():
	log = None
	exposed = True

	def __init__(self):
		self.log = log.Log(__name__)

	def GET(self, *params):
		"""Assembles an track query by appending query parameters as filters.
		The result is a query that satisfies all of the parameters that were
		passed on the url string.
		Returns the results of the query sorted by title_sort property
		"""
		cherrypy.response.headers['Content-Type'] = 'application/json'

		#catch random track requests
		if len(params) == 1 and params[0] == 'random':
			return self.random_track()

		#get the set of fields that makes up a Track object
		fields = {c.name: c for c in Track.__table__.columns}

		#split the query into key:value pairs
		query = []
		for index in range(0, len(params) - 1, 2):
			query.append(dict([(params[index],params[index + 1])]))

		self.log.info(u'A GET request was received by Tracks with params %s' % unicode(query))

		q = cherrypy.request.db.query(Track)
		for d in query:
			key = d.keys()[0]
			value = d[key]

			if str(fields[key].type) == 'VARCHAR':
				# allow for partial string matching
				q = q.filter(fields[key].like('%' + value + '%'))
			else:
				# all other data types must be exact matches
				q = q.filter(fields[key] == value)

		# return the results as JSON
		track_list = []
		for a in q.order_by(Track.title).all():
			track_list.append(a.as_dict())
		return json.dumps(track_list, cls=DateTimeEncoder)


	def random_track(self):
		"""Returns a random track from the library."""

		cherrypy.response.headers['Content-Type'] = 'application/json'
		self.log.info(u'RandomTracks called.')

		q = cherrypy.request.db.query(Track).all()
		track = q[random.randint(0, len(q) - 1)]

		return json.dumps(track.as_dict(), cls=DateTimeEncoder)