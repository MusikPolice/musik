from musik import log
from musik import streaming
from musik import db

import cherrypy

class Track():
	log = None
	exposed = True
	stream = None

	def __init__(self):
		self.log = log.Log(__name__)

	def GET(self, id):
		"""Transcodes the track with the specified unique id to ogg vorbis and
		streams it to the client. Streaming begins immediately, even if the
		entire file has not yet been transcoded."""

		# look up the track in the database
		self.log.info(u'OggStream.track called with id %s' % unicode(id))
		track = cherrypy.request.db.query(db.Track).filter(db.Track.id == id).first()
		uri = track.uri

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
	GET._cp_config = {'response.stream': True}