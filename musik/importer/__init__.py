from datetime import datetime
import mimetypes
import os
import re
import threading
import time

from sqlalchemy.exc import OperationalError

from musik import log
from musik.db import DatabaseWrapper, ImportTask, Track, Album, Artist, Disc
from musik.importer.mediafile import MediaFile
from musik.util import EasygoingDictionary

class ImportThread(threading.Thread):

	running = True		# whether or not the thread should continue to run
	sa_session = None	# database session
	log = None			# logging instance

	def __init__(self):
		"""Creates a new instance of ImportThread and connects to the database.
		This design pattern is important: since the constructor runs synchonously,
		it ensures that two threads don't attempt to initialize the database at
		the same time.
		"""
		super(ImportThread, self).__init__(name=__name__)
		self.log = log.Log(__name__)
		db = DatabaseWrapper()
		self.sa_session = db.get_session()

	def run(self):
		"""Checks for new import tasks once per second and passes them off to
		the appropriate handler functions for completion.
		"""
		try:
			# process 'till you drop
			while self.running:

				# find the first uncompleted import task. This limits the
				# importer to being single-threaded, but ensures that jobs
				# that are stopped while in progress will complete on next
				# startup.
				task = self.sa_session.query(ImportTask).filter(ImportTask.completed == None).order_by(ImportTask.created).first()

				if task != None:
					# start processing it
					task.started = datetime.utcnow()
					self.sa_session.commit()
					self.log.info(u'%s is processing task %s' % (self.getName(), unicode(task)))

					# process the task
					if os.path.isdir(task.uri):
						self.log.info(u'Importing directory %s' % task.uri)
						self.import_directory(task.uri)
					elif os.path.isfile(task.uri):
						self.log.info(u'Importing file %s' % task.uri)
						self.import_file(task.uri)
					else:
						self.log.warning(u'Unrecognized URI %s' % task.uri)

					task.completed = datetime.utcnow()
					self.sa_session.commit()
					self.log.info(u'%s has finished processing task %s' % (self.getName(), unicode(task)))

				time.sleep(1)

		finally:
			# always clean up - your mom doesn't work here
			if self.sa_session != None:
				self.sa_session.close()
				self.sa_session = None


	# adds a directory to the local library
	# in practice, this is a breadth-first searche over the specified directory and its
	# subdirectories that places appropriate files back into the import queue
	# TODO: directory permissions. Make sure that we can read before we try to
	def import_directory(self, uri):
		search_queue = [uri]
		while len(search_queue) > 0:
			# this is the current working directory
			baseuri = search_queue.pop(0)
			if os.path.isdir(baseuri) == False:
				continue

			# iterate over the subdirectories and files in the current working directory
			entries = os.listdir(baseuri)
			for subdir in entries:

				# if we found a directory, put it back on the queue. otherwise, process it
				newuri = os.path.join(baseuri, subdir)
				if os.path.isdir(newuri):
					search_queue.append(newuri)
				elif os.path.isfile(newuri):
					if self.is_mime_type_supported(newuri):
						# create a new import task for useful files
						newtask = ImportTask(newuri)
						self.sa_session.add(newtask)
						self.sa_session.commit()
					else:
						self.log.info(u'Ignoring file %s' % newuri)


	# returns True if the mime type of the specified uri is supported
	# this should only support audio files
	# TODO: query gstreamer (or whatever other backend we're using) to determine support up front
	def is_mime_type_supported(self, uri):
		mtype = mimetypes.guess_type(uri)[0]
		if mtype in (u'audio/mpeg', u'audio/flac', u'audio/ogg', u'audio/x-wav'):
			return True
		else:
			return False


	def import_file(self, uri):
		self.log.info(u'import_file called with uri %s' % uri)

		mtype = mimetypes.guess_type(uri)[0]
		if mtype != u'audio/mpeg':
			self.log.info(u'Unsupported mime type %s. Ignoring file.' % mtype)

		# Try to read the metadata appropriately.
		self.import_track(uri)


	def import_track(self, uri):
		"""Creates a track object out of the specified URI.
		Returns a fully populated musik.db.Track object that has already been
		committed to the database.
		"""
		self.log.info(u'import_track called with uri %s' % uri)

		# check that the uri doesn't already exist in our library
		try:
			track = self.sa_session.query(Track).filter(Track.uri == uri).first()
		except OperationalError as oe:
			error_text = str(oe)
			if error_text.startswith(u"(OperationalError) no such column:"):
				# Database schema has likely changed
				self.log.error(u"One or more columns does not exist in the database. You may be able to repair it yourself.")
				self.log.error(u"If you are developing and don't care about your data, just delete the musik.db file.")
				# Fall through and print exception details so the user can adjust as necessary

			self.log.error(u"An error occurred accessing the database: %s" % error_text)
			return

		if track == None:
			track = Track(uri)
			self.sa_session.add(track)
		else:
			self.log.info(u'Track with uri %s is already in the library. Updating metadata...')

		try:
			# get id3 data from the file
			easyid3 = EasyID3(uri)
		except ID3NoHeaderError as nhe:
			self.log.error(u'Cannot read ID3 data from %s. It cannot be added to the library at this time.' % uri)
			self.log.error(u'Exception message: %s' % unicode(nhe))
			return False

		metadata = EasygoingDictionary()
		for key in easyid3.keys():
			if type(easyid3[key]) == list:
				metadata[key] = easyid3[key][0]
			else:
				metadata[key] = easyid3[key]

		# artist
		artist = self.find_artist(metadata['artist'], metadata['artistsort'], metadata['musicbrainz_artistid'])
		if artist != None:
			if track.artist == None:
				track.artist = artist
				self.sa_session.add(artist)
			elif track.artist.id != artist.id:
				# TODO: conflict!
				self.log.warning(u'Artist conflict for track %s: %s != %s' % (track, track.artist, artist))

		# album artist - use the artist if metadata isn't set
		album_artist = self.find_artist(metadata['albumartist'], metadata['albumartistsort'])
		if album_artist != None:
			if track.album_artist == None:
				track.album_artist = album_artist
				self.sa_session.add(album_artist)
			elif track.album_artist.id != album_artist.id:
				# TODO: conflict!
				self.log.warning(u'Album artist conflict for track %s: %s != %s' % (track, track.album_artist, album_artist))
		elif artist != None:
			if track.album_artist == None:
				track.album_artist = artist
				self.sa_session.add(artist)
			elif track.album_artist.id != artist.id:
				# TODO: conflict!
				self.log.warning(u'Album artist conflict for track %s: %s != %s' % (track, track.album_artist, artist))

		# arranger
		arranger = self.find_artist(metadata['arranger'])
		if arranger != None:
			if track.arranger == None:
				track.arranger = arranger
				self.sa_session.add(arranger)
			elif track.arranger.id != arranger.id:
				# TODO: conflict!
				self.log.warning(u'Arranger conflict for track %s: %s != %s' % (track, track.arranger, arranger))

		# author
		author = self.find_artist(metadata['author'])
		if author != None:
			if track.author == None:
				track.author = author
				self.sa_session.add(author)
			elif track.author.id != author.id:
				# TODO: conflict!
				self.log.warning(u'Author conflict for track %s: %s != %s' % (track, track.author, author))

		# composer
		composer = self.find_artist(metadata['composer'], metadata['composersort'])
		if composer != None:
			if track.composer == None:
				track.composer = composer
				self.sa_session.add(composer)
			elif track.composer.id != composer.id:
				# TODO: conflict!
				self.log.warning(u'Composer conflict for track %s: %s != %s' % (track, track.composer, composer))

		# conductor
		conductor = self.find_artist(metadata['conductor'])
		if conductor != None:
			if track.conductor == None:
				track.conductor = conductor
				self.sa_session.add(conductor)
			elif track.conductor.id != conductor.id:
				# TODO: conflict!
				self.log.warning(u'Conductor conflict for track %s: %s != %s' % (track, track.conductor, conductor))

		# lyricist
		lyricist = self.find_artist(metadata['lyricist'])
		if lyricist != None:
			if track.lyricist == None:
				track.lyricist = lyricist
				self.sa_session.add(lyricist)
			elif track.lyricist.id != lyricist.id:
				# TODO: conflict!
				self.log.warning(u'Lyricist conflict for track %s: %s != %s' % (track, track.lyricist, lyricist))

		# performer
		performer = self.find_artist(metadata['performer'])
		if performer != None:
			if track.performer == None:
				track.performer = performer
				self.sa_session.add(performer)
			elif track.performer.id != performer.id:
				# TODO: conflict!
				self.log.warning(u'Performer conflict for track %s: %s != %s' % (track, track.performer, performer))

		# album
		album = self.find_album(metadata['album'], metadata['albumsort'], metadata['musicbrainz_albumid'], track.artist, metadata)
		if album != None:
			if track.album == None:
				track.album = album
				self.sa_session.add(album)
			elif track.album.id != album.id:
				# TODO: conflict!
				self.log.warning(u'Album conflict for track %s: %s != %s' % (track, track.album, album))

		# disc
		if track.album != None:
			disc = self.find_disc(track.album, metadata['discnumber'], metadata['discsubtitle'], metadata['musicbrainz_discid'])
			for d in track.album.discs:
				if d.id == disc.id:
					# found disc is already linked - don't add it again
					disc = None
			if disc != None:
				track.album.discs.append(disc)

		#bpm
		if metadata['bpm'] != None:
			if track.bpm == None:
				track.bpm = metadata['bpm']
			elif track.bpm != metadata['bpm']:
				# TODO: conflict!
				self.log.warning(u'Track bpm conflict for track %s: %s != %s' % (track, track.bpm, metadata['bpm']))

		#copyright
		if metadata['copyright'] != None:
			if track.copyright == None:
				track.copyright = metadata['copyright']
			elif track.copyright != metadata['copyright']:
				# TODO: conflict!
				self.log.warning(u'Track copyright conflict for track %s: %s != %s' % (track, track.copyright, metadata['copyright']))

		#date
		if metadata['date'] != None:
			if track.date == None:
				track.date = metadata['date']
			elif track.date != metadata['date']:
				# TODO: conflict!
				self.log.warning(u'Track date conflict for track %s: %s != %s' % (track, track.date, metadata['date']))

		#encodedby
		if metadata['encodedby'] != None:
			if track.encodedby == None:
				track.encodedby = metadata['encodedby']
			elif track.encodedby != metadata['encodedby']:
				# TODO: conflict!
				self.log.warning(u'Track encodedby conflict for track %s: %s != %s' % (track, track.encodedby, metadata['encodedby']))

		#genre
		if metadata['genre'] != None:
			if track.genre == None:
				track.genre = metadata['genre']
			elif track.genre != metadata['genre']:
				# TODO: conflict!
				self.log.warning(u'Track genre conflict for track %s: %s != %s' % (track, track.genre, metadata['genre']))

		#isrc
		if metadata['isrc'] != None:
			if track.isrc == None:
				track.isrc = metadata['isrc']
			elif track.isrc != metadata['isrc']:
				# TODO: conflict!
				self.log.warning(u'Track isrc conflict for track %s: %s != %s' % (track, track.isrc, metadata['isrc']))

		#length
		if metadata['length'] != None:
			if track.length == None:
				track.length = metadata['length']
			elif track.length != metadata['length']:
				# TODO: conflict!
				self.log.warning(u'Track length conflict for track %s: %s != %s' % (track, track.length, metadata['length']))

		#mood
		if metadata['mood'] != None:
			if track.mood == None:
				track.mood = metadata['mood']
			elif track.mood != metadata['mood']:
				# TODO: conflict!
				self.log.warning(u'Track mood conflict for track %s: %s != %s' % (track, track.mood, metadata['mood']))

		#musicbrainz_trackid
		if metadata['musicbrainz_trackid'] != None:
			if track.musicbrainz_trackid == None:
				track.musicbrainz_trackid = metadata['musicbrainz_trackid']
			elif track.musicbrainz_trackid != metadata['musicbrainz_trackid']:
				# TODO: conflict!
				self.log.warning(u'Track musicbrainz_trackid conflict for track %s: %s != %s' % (track, track.musicbrainz_trackid, metadata['musicbrainz_trackid']))

		#musicbrainz_trmid
		if metadata['musicbrainz_trmid'] != None:
			if track.musicbrainz_trmid == None:
				track.musicbrainz_trmid = metadata['musicbrainz_trmid']
			elif track.musicbrainz_trmid != metadata['musicbrainz_trmid']:
				# TODO: conflict!
				self.log.warning(u'Track musicbrainz_trmid conflict for track %s: %s != %s' % (track, track.musicbrainz_trmid, metadata['musicbrainz_trmid']))

		#musicip_fingerprint
		if metadata['musicip_fingerprint'] != None:
			if track.musicip_fingerprint == None:
				track.musicip_fingerprint = metadata['musicip_fingerprint']
			elif track.musicip_fingerprint != metadata['musicip_fingerprint']:
				# TODO: conflict!
				self.log.warning(u'Track musicip_fingerprint conflict for track %s: %s != %s' % (track, track.musicip_fingerprint, metadata['musicip_fingerprint']))

		#musicip_puid
		if metadata['musicip_puid'] != None:
			if track.musicip_puid == None:
				track.musicip_puid = metadata['musicip_puid']
			elif track.musicip_puid != metadata['musicip_puid']:
				# TODO: conflict!
				self.log.warning(u'Track musicip_puid conflict for track %s: %s != %s' % (track, track.musicip_puid, metadata['musicip_puid']))

		# title
		if metadata['title'] != None:
			if track.title == None:
				track.title = metadata['title']
			elif track.title != metadata['title']:
				# TODO: conflict!
				self.log.warning(u'Track title conflict for track %s: %s != %s' % (track, track.title, metadata['title']))

		# titlesort
		if metadata['titlesort'] != None:
			if track.title_sort == None:
				track.title_sort = metadata['titlesort']
			elif track.title_sort != metadata['titlesort']:
				# TODO: conflict!
				self.log.warning(u'Track titlesort conflict for track %s: %s != %s' % (track, track.title_sort, metadata['titlesort']))

		# tracknumber
		if metadata['tracknumber'] != None:
			if track.tracknumber == None:
				track.tracknumber = metadata['tracknumber']
			elif track.tracknumber != metadata['tracknumber']:
				# TODO: conflict!
				self.log.warning(u'Track tracknumber conflict for track %s: %s != %s' % (track, track.tracknumber, metadata['tracknumber']))

		# version
		if metadata['version'] != None:
			if track.subtitle == None:
				track.subtitle = metadata['version']
			elif track.subtitle != metadata['version']:
				# TODO: conflict!
				self.log.warning(u'Track version conflict for track %s: %s != %s' % (track, track.subtitle, metadata['version']))

		# website
		if metadata['website'] != None:
			if track.website == None:
				track.website = metadata['website']
			elif track.website != metadata['website']:
				# TODO: conflict!
				self.log.warning(u'Track website conflict for track %s: %s != %s' % (track, track.website, metadata['website']))

		# get id3 data from the file
		id3 = MP3(uri)

		metadata = EasygoingDictionary()
		for key in id3.keys():
			if type(id3[key]) == list:
				metadata[key] = id3[key][0]
			else:
				metadata[key] = id3[key]

		# play count can be stored in either the PCNT or the POPM frames.
		# choose the largest of the two values as our official playcount.
		playcount = 0
		if metadata['PCNT'] != None and metadata['PCNT'].count != None:
			playcount = int(metadata['PCNT'].count)

		if metadata['POPM'] != None and metadata['POPM'].count != None:
			if int(metadata['POPM'].count) > playcount:
				playcount = int(metadata['POPM'].count)

		# always take the largest playcount
		if track.playcount == None or track.playcount < playcount:
			track.playcount = playcount

		# rating is stored in the POPM frame
		# only ever set the rating if it is currently None - we never want to overwrite a user's rating
		if metadata['POPM'] != None and metadata['POPM'].rating != None:
			if track.rating == None:
				track.rating = int(metadata['POPM'].rating)

		# if we couldn't determine track, album, artist from metadata, try
		# to snag it from the path
		# track name = file name, album title = last directory in path,
		# artist name = second last directory in path.
		(dirName, fileName) = os.path.split(uri)
		(fileBaseName, fileExtension)=os.path.splitext(fileName)
		if track.title == None:
			track.title = fileBaseName
			track.title_sort = fileBaseName

		dirs = re.split(os.sep, dirName)
		if len(dirs) > 0:
			album = self.find_album(dirs[-1])
			if album != None:
				if track.album == None:
					track.album = album
					self.sa_session.add(album)

		if len(dirs) > 1:
			artist = self.find_artist(dirs[-2])
			if artist != None:
				if track.artist == None:
					track.artist = artist
					track.album_artist = artist
					self.sa_session.add(artist)

		self.log.info(u'Added track %s to the current session.' % track)

		#commit the transaction
		self.sa_session.commit()


	def find_artist(self, name=None, name_sort=None, musicbrainz_id=None):
		"""Searches the database for an existing artist that matches the specified criteria.
		If no existing artist can be found, a new artist is created with the criteria.
		When a new artist is created, it is not added to the database. This is the responsibility
		of the calling function.
		"""
		artist = None
		if musicbrainz_id != None:
			# we trust musicbrainz_artistid the most because it infers that
			# some other tagger has already verified the metadata.
			artist = self.sa_session.query(Artist).filter(Artist.musicbrainz_artistid == musicbrainz_id).first()
			if artist != None:
				# found an existing artist in our db - compare its metadata
				# to the new info. Always prefer existing metadata over new.
				self.log.info(u'Artist name musicbrainz_artistid search found existing artist %s in database' % artist)
				if name != None:
					if artist.name == None:
						artist.name = name
					elif artist.name != name:
						# TODO: conflict -> schedule musicbrainz task!
						self.log.warning(u'Artist name conflict for musicbrainz_artistid %s: %s != %s' % (artist.musicbrainz_artistid, artist.name, name))
				if name_sort != None:
					if artist.name_sort == None:
						artist.name_sort = name_sort
					elif artist.name_sort != name_sort:
						# TODO: conflict -> schedule musicbrainz task!
						self.log.warning(u'Artist sort name conflict for musicbrainz_artistid %s: %s != %s' % (artist.musicbrainz_artistid, artist.name_sort, name_sort))

		if artist == None and name != None:
			# if we don't have musicbrainz_artistid or there is no matching
			# artist in our db, try to find an existing artist by name
			artist = self.sa_session.query(Artist).filter(Artist.name == name).first()
			if artist != None:
				self.log.info(u'Artist name search found existing artist %s in database' % artist)
				# found an existing artist in our db - compare its metadata
				# to the new info. Always prefer existing metadata over new.
				if name_sort != None:
					if artist.name_sort == None:
						artist.name_sort = name_sort
					elif artist.name_sort != name_sort:
						self.log.warning(u'Artist sort name conflict for artist %s: %s != %s' % (artist.name, artist.name_sort, name_sort))
			else:
				# an existing artist could not be found in our db. Make a new one
				artist = Artist(name)
				if name_sort != None:
					artist.name_sort = name_sort
				if musicbrainz_id != None:
					artist.musicbrainz_artistid = musicbrainz_id
				# add the artist object to the DB
				self.log.info(u'Artist not found in database. Created new artist %s' % artist)

		# return the artist that we found and/or created
		return artist


	# TODO: Need support for album artist?
	def find_album(self, title=None, title_sort=None, musicbrainz_id=None, artist=None, metadata=None):
		"""Searches the database for an existing album that matches the specified criteria.
		If no existing album can be found, a new album is created with the criteria.
		When a new album is created, it is not added to the database. This is the responsibility of
		the calling function.
		"""
		album = None
		if musicbrainz_id != None:
			# we trust musicbrainz_albumid the most because it infers that
			# some other tagger has already verified the metadata.
			album = self.sa_session.query(Album).filter(Album.musicbrainz_albumid == musicbrainz_id).first()
			if album != None:
				# found an existing album in our db - compare its metadata
				# to the new info. Always prefer existing metadata over new.
				self.log.info(u'Album musicbrainz_albumid search found existing album %s in database' % album)
				if title != None:
					if album.title == None:
						album.title = title
					elif album.title != title:
						# TODO: conflict -> schedule musicbrainz task!
						self.log.warning(u'Album title conflict for musicbrainz_albumid %s: %s != %s' % (album.musicbrainz_albumid, album.title, title))
				if title_sort != None:
					if album.title_sort == None:
						album.title_sort = title_sort
					elif album.title_sort != title_sort:
						# TODO: conflict -> schedule musicbrainz task!
						self.log.warning(u'Album sort title conflict for musicbrainz_albumid %s: %s != %s' % (album.musicbrainz_albumid, album.title_sort, title_sort))
				if artist != None:
					if album.artist == None:
						album.artist = artist
					elif album.artist_id != artist.id:
						# TODO: conflict -> schedule musicbrainz task!
						self.log.warning(u'Album artist conflict for musicbrainz_albumid %s: %s != %s' % (album.musicbrainz_albumid, album.artist, artist))

		if album == None and title != None and artist != None:
			# if we don't have musicbrainz_albumid or there is no matching
			# album in our db, try to find an existing album by title and artist
			album = self.sa_session.query(Album).filter(Album.title == title, Album.artist_id == artist.id).first()
			if album != None:
				# found an existing album in our db - compare its metadata
				# to the new info. Always prefer existing metadata over new.
				self.log.info(u'Album title/artist search found existing album %s in database' % album)
				if title_sort != None:
					if album.title_sort == None:
						album.title_sort = title_sort
					elif album.title_sort != title_sort:
						self.log.warning(u'Album sort title conflict for album %s: %s != %s' % (album.title, album.title_sort, title_sort))
			else:
				# an existing album could not be found in our db. Make a new one
				album = Album(title)
				if title_sort != None:
					album.title_sort = title_sort
				if musicbrainz_id != None:
					album.musicbrainz_albumid = musicbrainz_id
				if artist != None:
					album.artist = artist
				self.log.info(u'Album not found in database. Created new album %s' % album)

		# we either found or created the album. now verify its metadata
		if album != None and metadata != None:
			if metadata['asin'] != None:
				if album.asin == None:
					album.asin = metadata['asin']
				elif album.asin != metadata['asin']:
					# TODO: conflict -> schedule musicbrainz task!
					self.log.warning(u'Album ASIN conflict for album %s: %s != %s' % (album, album.asin, metadata['asin']))
			if metadata['barcode'] != None:
				if album.barcode == None:
					album.barcode = metadata['barcode']
				elif album.barcode != metadata['barcode']:
					# TODO: conflict -> schedule musicbrainz task!
					self.log.warning(u'Album barcode conflict for album %s: %s != %s' % (album, album.barcode, metadata['barcode']))
			if metadata['compilation'] != None:
				if album.compilation == None:
					album.compilation = metadata['compilation']
				elif album.compilation != metadata['compilation']:
					# TODO: conflict -> schedule musicbrainz task!
					self.log.warning(u'Album compilation conflict for album %s: %s != %s' % (album, album.compilation, metadata['compilation']))
			if metadata['media'] != None:
				if album.media_type == None:
					album.media_type = metadata['media']
				if album.media_type != metadata['media']:
					# TODO: conflict -> schedule musicbrainz task!
					self.log.warning(u'Album media type conflict for album %s: %s != %s' % (album, album.media_type, metadata['media']))
			if metadata['musicbrainz_albumstatus'] != None:
				if album.musicbrainz_albumstatus == None:
					album.musicbrainz_albumstatus = metadata['musicbrainz_albumstatus']
				elif album.musicbrainz_albumstatus != metadata['musicbrainz_albumstatus']:
					# TODO: conflict -> schedule musicbrainz task!
					self.log.warning(u'Album musicbrainz_albumstatus conflict for album %s: %s != %s' % (album, album.musicbrainz_albumstatus, metadata['musicbrainz_albumstatus']))
			if metadata['musicbrainz_albumtype'] != None:
				if album.musicbrainz_albumtype == None:
					album.musicbrainz_albumtype = metadata['musicbrainz_albumtype']
				elif album.musicbrainz_albumtype != metadata['musicbrainz_albumtype']:
					# TODO: conflict -> schedule musicbrainz task!
					self.log.warning(u'Album musicbrainz_albumtype conflict for album %s: %s != %s' % (album, album.musicbrainz_albumtype, metadata['musicbrainz_albumtype']))
			if metadata['organization'] != None:
				if album.organization == None:
					album.organization = metadata['organization']
				elif album.organization != metadata['organization']:
					# TODO: conflict -> schedule musicbrainz task!
					self.log.warning(u'Album organization conflict for album %s: %s != %s' % (album, album.organization, metadata['organization']))
			if metadata['releasecountry'] != None:
				if album.releasecountry == None:
					album.releasecountry = metadata['releasecountry']
				elif album.releasecountry != metadata['releasecountry']:
					# TODO: conflict -> schedule musicbrainz task!
					self.log.warning(u'Album release country conflict for album %s: %s != %s' % (album, album.releasecountry, metadata['releasecountry']))

		return album


	def find_disc(self, album=None, discnumber=None, discsubtitle=None, musicbrainz_id=None):
		"""Tries to find an existing disc that matches the specified criteria.
		If an existing disc cannot be found, creates a new disc with the specified criteria.
		"""
		# first see if there's a disc that's already linked to the album that
		# has either the specified musicbrainz_discid or discnumber.
		disc = None
		if album != None:
			for d in album.discs:
				if musicbrainz_id != None:
					if d.musicbrainz_id == musicbrainz_id:
						disc = d
				if discnumber != None:
					if d.discnumber == discnumber:
						disc = d

		# if we found a disc in the existing album's collection that matches
		# the specified criteria, update any missing metadata
		if disc != None:
			self.log.info(u'Disc musicbrainz_discid/discnumber search found existing disc %s in database' % disc)
			if discnumber != None:
				if d.discnumber == None:
					d.discnumber = discnumber
				elif d.discnumber != discnumber:
					# TODO: conflict!
					self.log.warning(u'Disc number conflict for disc %s: %s != %s' % (disc, disc.discnumber, discnumber))
			if discsubtitle != None:
				if d.subtitle == None:
					d.subtitle = discsubtitle
				elif d.subtitle != discsubtitle:
					# TODO: Conflict!
					self.log.warning(u'Disc subtitle conflict for disc %s: %s != %s' % (disc, disc.subtitle, discsubtitle))
			if musicbrainz_id != None:
				if d.musicbrainz_discid == None:
					d.musicbrainz_discid = musicbrainz_id
				elif d.musicbrainz_discid != musicbrainz_id:
					# TODO: conflict!
					self.log.warning(u'Disc musicbrainz_discid conflict for disc %s: %s != %s' % (disc, disc.musicbrainz_discid, musicbrainz_id))

		if disc == None and musicbrainz_id != None:
			# search for an existing unlinked disc in the database.
			# we trust musicbrainz_discid the most because it infers that
			# some other tagger has already verified the metadata.
			disc = self.sa_session.query(Disc).filter(Disc.musicbrainz_discid == musicbrainz_id).first()
			if disc != None:
				self.log.info(u'Disc musicbrainz_discid search found existing disc %s in database' % disc)
				if album != None:
					if disc.album == None:
						disc.album = album
					elif disc.album.id != album.id:
						# TODO: conflict -> schedule musicbrainz task!
						self.log.warning(u'Disc album conflict for disc %s: %s != %s' % (disc, disc.album, album))
				if discnumber != None:
					if disc.discnumber == None:
						disc.discnumber = discnumber
					elif disc.discnumber != discnumber:
						# TODO: conflict -> schedule musicbrainz task!
						self.log.warning(u'Disc number conflict for disc %s: %s != %s' % (disc, disc.discnumber, discnumber))
				if discsubtitle != None:
					if disc.discsubtitle == None:
						disc.discsubtitle = discsubtitle
					elif disc.discsubtitle != discsubtitle:
						# TODO: conflict -> schedule musicbrainz task!
						self.log.warning(u'Disc subtitle conflict for disc %s: %s != %s' % (disc, disc.discsubtitle, discsubtitle))

		if disc == None and album != None and discnumber != None:
			# musicbrainz_discid wasn't supplied or didn't yield an existing album.
			# try to search with album id and disc number instead.
			disc = self.sa_session.query(Disc).filter(Disc.album_id == album.id, Disc.discnumber == discnumber).first()
			if disc != None:
				self.log.info(u'Disc album/number search found existing disc %s in database' % disc)
				if discsubtitle != None:
					if disc.discsubtitle == None:
						disc.discsubtitle = discsubtitle
					elif disc.discsubtitle != discsubtitle:
						# TODO: conflict -> schedule musicbrainz task!
						self.log.warning(u'Disc subtitle conflict for disc %s: %s != %s' % (disc, disc.discsubtitle, discsubtitle))
				if musicbrainz_id != None:
					if disc.musicbrainz_discid == None:
						disc.musicbrainz_discid = musicbrainz_id
					elif disc.musicbrainz_discid != musicbrainz_id:
						# TODO: conflict -> schedule musicbrainz task!
						self.log.warning(u'Disc musicbrainz_discid conflict for disc %s: %s != %s' % (disc, disc.musicbrainz_discid, musicbrainz_id))
			else:
				# could not find the disc in question. Create a new one instead
				disc = Disc(discnumber)
				if album != None:
					disc.album = album
				if discsubtitle != None:
					disc.discsubtitle = discsubtitle
				if musicbrainz_id != None:
					disc.musicbrainz_discid = musicbrainz_id
				self.log.info(u'Could not find disc in database. Created new disc %s' % disc)
				self.sa_session.add(disc)

		return disc


	def stop(self):
		"""Cleans up the thread"""
		self.log.info(u'%s.stop has been called' % self.getName())
		self.running = False
