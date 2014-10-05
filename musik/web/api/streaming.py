from musik import log
from musik import audiotranscode
from musik import db

import cherrypy
import json
import os


class DecoderEnumerator():
	"""Functions for enumerating the decoders that the server supports"""
	exposed=True

	def GET(self):
		"""Returns an array of audio mime types that the server can decode audio files from"""
		transcode = audiotranscode.AudioTranscode()
		mimetypes = []
		for dec in transcode.Decoders:
			if dec.available():
				mimetypes.append(audiotranscode.MIMETYPES[dec.filetype])
		return json.dumps(mimetypes)


class EncoderEnumerator():
	"""Functions for enumerating the encoders that the server supports"""
	exposed=True

	def GET(self):
		"""Returns an array of audio mime types that the server can encode audio files to"""
		transcode = audiotranscode.AudioTranscode()
		mimetypes = []
		for enc in transcode.Encoders:
			if enc.available():
				mimetypes.append(audiotranscode.MIMETYPES[enc.filetype])
		return json.dumps(mimetypes)


class Track():
	"""Functions for streaming single audio tracks"""
	exposed = True
	decoders = DecoderEnumerator()
	encoders = EncoderEnumerator()
	log = None

	def __init__(self):
		self.log = log.Log(__name__)


	def transcodeStream(self, uri, mimetype, targetFormat, targetMimeType):
		"""Reads the file at the specified uri, transcodes it into the targetFormat (a short-hand
		version of targetMimeType), and yields the data out as it's ready.
		* uri: The uri of the file to transcode.
		* mimetype: the mime type of the file. Used for logging.
		* targetFormat: the target format. One of mp3, ogg, flac, aac, m4a, or wav.
		* targetMimeType: the target mime type. Must match targetFormat. Used for logging.
		NOTE: this function silently eats exceptions, which will just cause the
		audio stream to end, and the client player to choke. Ideally, we would notify
		the user of the error as well.
		"""
		try:
			transcode = audiotranscode.AudioTranscode()
			for data in transcode.transcode_stream(uri, targetFormat):
				yield data

		except audiotranscode.TranscodeError as e:
			self.log.error(u'Failed to open audio stream %s' % uri)
		except audiotranscode.EncodeError as e:
			self.log.error(u'Missing encoder for %s' % targetMimeType)
		except audiotranscode.DecodeError as e:
			self.log.error(u'Missing decoder for %s' % mimetype)
		finally:
			self.log.info(u'Streaming is complete. Closing stream.')


	def GET(self, id, accept=None):
		"""Transcodes the track with the specified unique id to the specified accept type and
		streams it to the client. 
		* id: the unique identifier of a track in the database
		* accept: the target format. One of mp3, ogg, flac, aac, m4a, or wav. 
		If accept is undefined or matches the native type of the file, no transcoding will take place.
		Streaming begins immediately, even if the entire file has not yet been transcoded.
		"""

		# look up the track in the database
		track = cherrypy.request.db.query(db.Track).filter(db.Track.id == id).first()
		uri = track.uri

		targetFormat = None
		targetMimeType = None

		if accept != None:
			# convert the accept type into a target file type format that audiotranscode understands
			for key, value in audiotranscode.MIMETYPES.iteritems():
				if (value.endswith(accept)):
					targetFormat = key
					targetMimeType = value

			if targetFormat == None:
				self.log.error(u'Unsupported accept type specified: %s' % accept)
				return

		# if accept wasn't specified or matches original encoding, no need to transcode
		if accept == None or targetMimeType == track.mimetype:
			sizeInBytes = os.path.getsize(uri)
			cherrypy.response.headers['Content-Length'] = sizeInBytes
			cherrypy.response.headers['Content-Type'] = track.mimetype
			self.log.info(u'Started streaming %s without transcoding' % unicode(uri))
			return open(uri, 'rb')

		# otherwise, go ahead and transcode into the desired format
		# in this case, we can't set a content-length header, so player has to get length elsewhere
		cherrypy.response.headers['Content-Type'] = targetMimeType
		self.log.info(u'Started streaming %s as %s' % (unicode(uri), targetMimeType))
		return self.transcodeStream(uri, track.mimetype, targetFormat, targetMimeType)

	GET._cp_config = {'response.stream': True}