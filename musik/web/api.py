import json
import re
import os

import cherrypy

from musik import log
from musik import streaming
from musik.db import Album, Artist, ImportTask, Track, Disc


class Import:
	@cherrypy.expose
	def directory(self, path):
		"""Queues the specified path for import into the media library.
		"""
		cherrypy.response.headers['Content-Type'] = 'application/json'

		if not path or not os.path.isdir(path):
			raise cherrypy.HTTPError("404 Not Found", "Couldn't find the path " + str(path) + " on the target system")

		task = ImportTask(path)
		cherrypy.request.db.add(task)

		# this is an http 200 ok with no data
		return json.dumps(None)

	@cherrypy.expose
	def status(self):
		# gets the number of outstanding importer tasks
		numtasks = cherrypy.request.db.query(ImportTask).filter(ImportTask.started == None).filter(ImportTask.completed == None).count()

		# get the currently processing task
		currentTask = cherrypy.request.db.query(ImportTask).filter(ImportTask.started != None).filter(ImportTask.completed == None).first()

		ret = u''
		if (currentTask != None):
			ret += u'The importer is currently processing %s.<br />' % unicode(currentTask.uri)

		#TODO: calculate estimated completion time by multiplying average job time by number of outstanding items

		#TODO: return JSON instead of text
		if numtasks == 0:
			ret += u'There are no tasks currently pending'
		else:
			ret += u'There are %d tasks currently pending' % numtasks

		return ret


class OggStream:
	log = None
	stream = None

	def __init__(self):
		self.log = log.Log(__name__)

	@cherrypy.expose
	def track(self, id):
		"""Transcodes the track with the specified unique id to ogg vorbis and
		streams it to the client. Streaming begins immediately, even if the
		entire file has not yet been transcoded."""

		# look up the track in the database
		self.log.info(u'OggStream.track called with id %s' % unicode(id))
		uri = cherrypy.request.db.query(Track).filter(Track.id == id).first().uri

		cherrypy.response.headers['Content-Type'] = 'audio/ogg'

		def yield_data():
			"""TODO: this function silently eats exceptions, which will just cause the
			audio stream to end, and the client player to choke. Ideally, we would notify
			the user of the error as well.
			"""
			try:
				self.log.info(u'OggStream.track trying to open %s for streaming' % unicode(uri))
				self.stream = streaming.audio_open(uri)

				self.log.info(u'OggStream.track started streaming %s' % unicode(uri))
				for block in self.stream:
					yield block
			except streaming.DecodeError as e:
				self.log.error(u'Failed to open audio stream %s' % uri)
			finally:
				self.log.info(u'OggStream.track streaming is complete. Closing stream.')
				if self.stream is not None:
					self.stream.close()
					self.stream = None

		return yield_data()
	track._cp_config = {'response.stream': True}


# defines an api with a dynamic url scheme composed of /<tag>/<value>/ pairs
# these pairs are assembled into an SQL query. Each term is combined with the AND operator.
# unknown <tag> elements are ignored.
class API:
	log = None
	importmedia = Import()
	stream = OggStream()

	def __init__(self):
		self.log = log.Log(__name__)


	@cherrypy.expose
	def default(self, *params):

		cherrypy.response.headers['Content-Type'] = 'application/json'

		#the first item in the url is the object that is being queried
		#the remainder are key value pairs of the things to query and their desired ids
		#split them into a list of dictionary pairs prior to processing
		query = []
		for index in range(1, len(params) - 1, 2):
			query.append(dict([(params[index],params[index + 1])]))

		#figure out data type the user is requesting
		if params[0] == 'albums':
			return json.dumps(self.queryAlbums(query))
		if params[0] == 'artists':
			return json.dumps(self.queryArtists(query))
		if params[0] == 'tracks':
			return json.dumps(self.queryTracks(query))
		if params[0] == 'discs':
			return json.dumps(self.queryDiscs(query))


	def queryAlbums(self, params):
		"""Assembles an album query by appending query parameters as filters.
		The result is a query that satisfies all of the parameters that were
		passed on the url string.
		Returns the results of the query sorted by title_sort property
		"""
		self.log.info(u'queryAlbums called with params %s' % unicode(params))

		q = cherrypy.request.db.query(Album)

		for d in params:
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
		return album_list


	def queryDiscs(self, params):
		"""Assembles an disc query by appending query parameters as filters.
		The result is a query that satisfies all of the parameters that were
		passed on the url string.
		Returns the results of the query sorted by id property
		TODO: sort by album
		"""
		self.log.info(u'queryDiscs called with params %s' % unicode(params))

		q = cherrypy.request.db.query(Disc)

		for d in params:
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
		return disc_list


	def queryArtists(self, params):
		"""Assembles an artist query by appending query parameters as filters.
		The result is a query that satisfies all of the parameters that were
		passed on the url string.
		Returns the results of the query sorted by name_sort property
		"""
		self.log.info(u'queryArtists called with params %s' % unicode(params))

		q = cherrypy.request.db.query(Artist)

		for d in params:
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
		return artist_list


	def queryTracks(self, params):
		"""Assembles an track query by appending query parameters as filters.
		The result is a query that satisfies all of the parameters that were
		passed on the url string.
		Returns the results of the query sorted by title_sort property
		"""
		self.log.info(u'queryTracks called with params %s' % unicode(params))

		q = cherrypy.request.db.query(Track)

		for d in params:
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
		return track_list