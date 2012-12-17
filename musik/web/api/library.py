from musik import log

import cherrypy
from musik.db import Album, Artist, Disc, Track
import musik.web.api.library

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

		#the first item in the url is the object that is being queried
		#the remainder are key value pairs of the things to query and their desired ids
		#split them into a list of dictionary pairs prior to processing
		query = []
		for index in range(0, len(params) - 1, 2):
			query.append(dict([(params[index],params[index + 1])]))

		self.log.info(u'queryAlbums called with params %s' % unicode(query))

		q = cherrypy.request.db.query(Album)

		for d in query:
			key = d.keys()[0]
			value = d[key]

			if key == 'id':
				q = q.filter(Album.id == value)
			elif key == 'title':
				q = q.filter(Album.title.like('%' + value + '%'))
			elif key == 'title_sort':
				q = q.filter(Album.title_sort.like('%' + value + '%'))
			elif key == 'artist_id':
				q = q.filter(Album.artist_id == value)
			elif key == 'asin':
				q = q.filter(Album.asin.like('%' + value + '%'))
			elif key == 'barcode':
				q = q.filter(Album.barcode.like('%' + value + '%'))
			elif key == 'compilation':
				q = q.filter(Album.compilation == value)
			elif key == 'media_type':
				q = q.filter(Album.media_type.like('%' + value + '%'))
			elif key == 'musicbrainz_albumid':
				q = q.filter(Album.musicbrainz_albumid.like('%' + value + '%'))
			elif key == 'musicbrainz_albumstatus':
				q = q.filter(Album.musicbrainz_albumstatus.like('%' + value + '%'))
			elif key == 'musicbrainz_albumtype':
				q = q.filter(Album.musicbrainz_albumtype.like('%' + value + '%'))
			elif key == 'organization':
				q = q.filter(Album.organization.like('%' + value + '%'))
			elif key == 'releasecountry':
				q = q.filter(Album.releasecountry.like('%' + value + '%'))

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

		#the first item in the url is the object that is being queried
		#the remainder are key value pairs of the things to query and their desired ids
		#split them into a list of dictionary pairs prior to processing
		query = []
		for index in range(0, len(params) - 1, 2):
			query.append(dict([(params[index],params[index + 1])]))

		self.log.info(u'queryArtists called with params %s' % unicode(query))

		q = cherrypy.request.db.query(Artist)

		for d in query:
			key = d.keys()[0]
			value = d[key]

			if key == 'id':
				q = q.filter(Artist.id == value)
			elif key == 'name':
				q = q.filter(Artist.name.like('%' + value + '%'))
			elif key == 'name_sort':
				q = q.filter(Artist.name_sort.like('%' + value + '%'))
			elif key == 'musicbrainz_artistid':
				q = q.filter(Artist.musicbrainz_artistid.like('%' + value + '%'))

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

		#the first item in the url is the object that is being queried
		#the remainder are key value pairs of the things to query and their desired ids
		#split them into a list of dictionary pairs prior to processing
		query = []
		for index in range(0, len(params) - 1, 2):
			query.append(dict([(params[index],params[index + 1])]))

		self.log.info(u'queryDiscs called with params %s' % unicode(query))

		q = cherrypy.request.db.query(Disc)

		for d in query:
			key = d.keys()[0]
			value = d[key]

			if key == 'id':
				q = q.filter(Disc.id == value)
			elif key == 'album_id':
				q = q.filter(Disc.album_id == value)
			elif key == 'discnumber':
				q = q.filter(Disc.discnumber.like('%' + value + '%'))
			elif key == 'disc_subtitle':
				q = q.filter(Disc.disc_subtitle.like('%' + value + '%'))
			elif key == 'musicbrainz_discid':
				q = q.filter(Disc.musicbrainz_discid.like('%' + value + '%'))

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

		#the first item in the url is the object that is being queried
		#the remainder are key value pairs of the things to query and their desired ids
		#split them into a list of dictionary pairs prior to processing
		query = []
		for index in range(0, len(params) - 1, 2):
			query.append(dict([(params[index],params[index + 1])]))

		self.log.info(u'queryTracks called with params %s' % unicode(query))

		q = cherrypy.request.db.query(Track)

		for d in query:
			key = d.keys()[0]
			value = d[key]

			if key == 'id':
				q = q.filter(Track.id == value)
			elif key == 'uri':
				q = q.filter(Track.uri.like('%' + value + '%'))
			elif key == 'artist_id':
				q = q.filter(Track.artist_id == value)
			elif key == 'album_id':
				q = q.filter(Track.album_id == value)
			elif key == 'album_artist_id':
				q = q.filter(Track.album_artist_id == value)
			elif key == 'arranger_id':
				q = q.filter(Track.arranger_id == value)
			elif key == 'author_id':
				q = q.filter(Track.author_id == value)
			elif key == 'bpm':
				q = q.filter(Track.bpm == value)
			elif key == 'composer_id':
				q = q.filter(Track.composer_id == value)
			elif key == 'conductor_id':
				q = q.filter(Track.conductor_id == value)
			elif key == 'copyright':
				q = q.filter(Track.copyright.like('%' + value + '%'))
			elif key == 'date':
				q = q.filter(Track.date.like('%' + value + '%'))
			elif key == 'disc_id':
				q = q.filter(Track.disc_id == value)
			elif key == 'encodedby':
				q = q.filter(Track.encodedby.like('%' + value + '%'))
			elif key == 'genre':
				q = q.filter(Track.genre.like('%' + value + '%'))
			elif key == 'isrc':
				q = q.filter(Track.isrc.like('%' + value + '%'))
			elif key == 'length':
				q = q.filter(Track.length == value)
			elif key == 'lyricist_id':
				q = q.filter(Track.lyricist_id == value)
			elif key == 'mood':
				q = q.filter(Track.mood.like('%' + value + '%'))
			elif key == 'musicbrainz_trackid':
				q = q.filter(Track.musicbrainz_trackid.like('%' + value + '%'))
			elif key == 'musicbrainz_trmid':
				q = q.filter(Track.musicbrainz_trmid.like('%' + value + '%'))
			elif key == 'musicip_fingerprint':
				q = q.filter(Track.musicip_fingerprint.like('%' + value + '%'))
			elif key == 'musicip_puid':
				q = q.filter(Track.musicip_puid.like('%' + value + '%'))
			elif key == 'performer_id':
				q = q.filter(Track.performer_id == value)
			elif key == 'title':
				q = q.filter(Track.title.like('%' + value + '%'))
			elif key == 'title_sort':
				q = q.filter(Track.title_sort.like('%' + value + '%'))
			elif key == 'tracknumber':
				q = q.filter(Track.tracknumber == value)
			elif key == 'subtitle':
				q = q.filter(Track.subtitle.like('%' + value + '%'))
			elif key == 'website':
				q = q.filter(Track.website.like('%' + value + '%'))
			elif key == 'playcount':
				q = q.filter(Track.playcount == value)
			elif key == 'rating':
				q = q.filter(Track.rating == value)

		track_list = []
		for a in q.order_by(Track.title_sort).all():
			track_list.append(a.as_dict())
		return json.dumps(track_list)


	def random_track(self):
		"""Returns a random track from the library."""

		cherrypy.response.headers['Content-Type'] = 'application/json'
		self.log.info(u'RandomTracks called.')

		q = cherrypy.request.db.query(Track).all()
		track = q[random.randint(0, len(q) - 1)]

		return json.dumps(track.as_dict())