from datetime import datetime
import os, os.path

from musik import config

from sqlalchemy import Column, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import String, Integer, DateTime, Boolean, BigInteger
from sqlalchemy.orm import backref, relationship, sessionmaker


# Helper to map and register a Python class a db table
Base = declarative_base()

# Represents an import task
class ImportTask(Base):
	"""An import task is any operation that results in the import of a media
	file into the library from some uri.
	At this time, only local directories and files are supported, but in the
	future we may support YouTube videos, SoundCloud files, or files hosted
	on HTTP, FTP, and SSH servers.
	"""
	__tablename__ = 'import_tasks'
	id = Column(Integer, primary_key=True)
	uri = Column(String)
	created = Column(DateTime)
	started = Column(DateTime)
	completed = Column(DateTime)

	def __init__(self, uri):
		Base.__init__(self)
		self.uri = uri
		self.created = datetime.utcnow()

	def __unicode__(self):
		if self.completed != None:
			return u'<ImportTask(uri=%s, created=%s, started=%s, completed=%s)>' % (self.uri, self.created, self.started, self.completed)
		elif self.started != None:
			return u'<ImportTask(uri=%s, created=%s, started=%s)>' % (self.uri, self.created, self.started)
		else:
			return u'<ImportTask(uri=%s, created=%s)>' % (self.uri, self.created)

	def __str__(self):
		return unicode(self).encode('utf-8')

	def as_dict(self):
		"""Returns a representation of the task as a dictionary"""
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Artist(Base):
	"""An artist is the person or persons responsible for creating some
	aspect of a Track.
	Tracks have artists, composers, conductors, lyricists, etc.
	Internally, all are treated as artists and foreign key to this table.
	"""
	__tablename__ = 'artists'
	id = Column(Integer, primary_key=True)	# unique id
	name = Column(String)					# artist name
	name_sort = Column(String)				# sortable artist name
	musicbrainz_artistid = Column(String)	# unique 36-digit musicbrainz hex string

	# TODO: make musicbrainz_artistid unique!

	def __init__(self, name):
		Base.__init__(self)
		self.name = name
		self.name_sort = name

	def __unicode__(self):
		return u'<Artist(name=%s)>' % self.name

	def __str__(self):
		return unicode(self).encode('utf-8')

	def as_dict(self):
		"""Returns a representation of the artist as a dictionary"""
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Album(Base):
	"""An album is a platonic ideal of a collection of released songs.
	Back in the day, the only way to get songs was on some physical medium.
	Modern listeners may not identify with albums in the classical sense, so
	this class is not intended to represent a physical item, but rather a
	collection of related songs that may or may not have a physical representation.
	"""
	__tablename__ = 'albums'
	id = Column(Integer, primary_key=True)					# unique id
	albumstatus = Column(String)							# musicbrainz album status
	albumtype = Column(String)								# musicbrainz album type
	artist_id = Column(Integer, ForeignKey('artists.id'))	# the artist that recorded this album
	asin = Column(String)									# amazon standard identification number - only if physical
	catalognum = Column(String)								# a quasi-unique identifier assigned to the album by the label
	compilation = Column(Boolean)							# whether or not this album is a compilation
	country = Column(String)								# the country that this album was released in
	label = Column(String)									# the record label that released this album
	mb_albumid = Column(String)								# unique 36-digit musicbrainz hex string
	mb_releasegroupid = Column(String)						# unique identifer of label that released the album
	media_type = Column(String)								# the type of media (CD, etc)
	title = Column(String)									# the title of the album
	title_sort = Column(String)								# sortable title of the album
	year = Column(Integer)									# the year in which the album was released

	artist = relationship('Artist', backref=backref('albums', order_by=id))

	def __init__(self, title):
		Base.__init__(self)
		self.title = title
		self.title_sort = title

	def __unicode__(self):
		return u'<Album(title=%s)>' % self.title

	def __str__(self):
		return unicode(self).encode('utf-8')

	def as_dict(self):
		"""Returns a representation of the album as a dictionary"""
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Disc(Base):
	"""A disc is a physical platter that comprises a part of the physical
	manifestation of an Album. Physical albums must have at least one disc,
	while digital releases will not have any.
	CD - Pink Floyd's The Wall was released on two distinct discs
	LP - Pink Floyd's The Wall was released on two platters, each with two
		 sides. We represent this with four discs, one for each side.
	Cassette - Pink Floyd's The Wall was released on two cassette tapes,
			   each with two sides. We represent this with four discs, one
			   for each side.
	"""
	__tablename__ = 'discs'

	# columns
	id = Column(Integer, primary_key=True)				# unique id
	album_id = Column(Integer, ForeignKey('albums.id'))	# the album that this disc belongs to
	discnumber = Column(String)							# the play order of this disc in the collection
	disc_subtitle = Column(String)						# the subtitle (if applicable) of this disc
	num_tracks = Column(Integer)						# total tracks on the disc

	# relationships
	album = relationship('Album', backref=backref('discs', order_by=discnumber, lazy='dynamic'))

	def __init__(self, discnumber):
		Base.__init__(self)
		self.discnumber = discnumber

	def __unicode__(self):
		return u'<Disc(album=%s, discnumber=%s)>' % (self.album, self.discnumber)

	def __str__(self):
		return unicode(self).encode('utf-8')

	def as_dict(self):
		"""Returns a representation of the disc as a dictionary"""
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Track(Base):
	"""A track is a single audio file, which usually corresponds to a distinct
	song, comedy routine, or book chapter. Tracks can be grouped into Albums,
	and are usually created by one or more Artists.
	"""
	__tablename__ = 'tracks'

	# fields from metadata
	id = Column(Integer, primary_key=True)						# unique id
	uri = Column(String)										# physical location of the track file
	album_id = Column(Integer, ForeignKey('albums.id'))			# the album that contains the track
	albumartist_id = Column(Integer, ForeignKey('artists.id'))  # the artist that recorded the album
	artist_id = Column(Integer, ForeignKey('artists.id'))		# the artist that recorded the track
	bitdepth = Column(Integer)									# Number of bits per sample
	bitrate = Column(Integer)									# Number of bits per second
	bpm = Column(Integer)										# beats per minute
	channels = Column(Integer)									# The number of channels in the audio
	comments = Column(String)									# Comments
	composer_id = Column(Integer, ForeignKey('artists.id'))		# the artist that composed the track
	date = Column(DateTime)										# date that the track was released
	disc_id = Column(Integer, ForeignKey('discs.id'))			# disc of the album that the track appeared on
	encoder = Column(String)									# encoder that created the digital file
	format = Column(String)										# the file format/codec
	genre = Column(String)										# genre of track contents
	language = Column(String)									# language code
	length = Column(BigInteger)									# length of the track in milliseconds
	lyrics = Column(String)										# the lyrics to the song
	mb_trackid = Column(String)									# unique 36-digit musicbrainz hex string
	samplerate = Column(Integer)								# sample rate
	title = Column(String)										# title of the track
	tracknumber = Column(Integer)								# order of the track on the disc

	# custom fields
	playcount = Column(Integer)									# number of times the track was played
	rating = Column(Integer)									# rating of the track (0-255)

	# relationships
	album = relationship('Album', backref=backref('tracks', order_by=tracknumber))
	album_artist = relationship('Artist', primaryjoin='Artist.id == Track.albumartist_id')
	artist = relationship('Artist', primaryjoin='Artist.id == Track.artist_id')
	composer = relationship('Artist', primaryjoin='Artist.id == Track.composer_id')
	disc = relationship('Disc', backref=backref('tracks', order_by=tracknumber))

	def __init__(self, uri):
		Base.__init__(self)
		self.uri = uri

	def __unicode__(self):
		return u'<Track(title=%s, uri=%s)>' % (self.title, self.uri)

	def __str__(self):
		return unicode(self).encode('utf-8')

	def as_dict(self):
		"""Returns a representation of the track as a dictionary"""
		fields = {c.name: getattr(self, c.name) for c in self.__table__.columns}
		fields['stream_uri'] = '%s/api/stream/%s' % (config.get_site_root(), str(fields['id']))
		return fields


# Loosely wraps the SQLAlchemy database types and access methods.
# The goal here isn't to encapsulate SQLAlchemy. Rather, we want dictate
# to the process of connecting to and disconnecting from the db,
# as well as the data types that the application uses once connected.
# TODO: refactor the class and function names to follow python spec
class DatabaseWrapper:

	db_path = None
	sa_engine = None
	sa_sessionmaker = None

	def __init__(self):
		"""Creates a new instance of the DatabaseWrapper.
		This function starts a new database engine and ensures that the
		database has been initialized.
		"""
		self.db_path = config.get("General", "database_path")
		self.init_database()

	def get_engine(self):
		"""Initializes and returns an instance of sqlalchemy.engine.base.Engine
		"""
		if self.sa_engine == None:
			self.sa_engine = create_engine('sqlite:///%s' % self.db_path, echo=False)
		return self.sa_engine

	def init_database(self):
		"""Initializes the database schema
		This method is not thread-safe; users must take steps to ensure that it is
		only called from one thread at a time.
		If get_engine has not yet been called, this method will call it implicitly.
		"""
		if self.sa_engine == None:
			self.get_engine()
		Base.metadata.create_all(self.sa_engine)

	def get_session(self):
		"""Initializes and returns an instance of sqlalchemy.engine.base.Engine
		If get_engine has not yet been called, this method will call it implicitly.
		"""
		if self.sa_engine == None:
			self.get_engine()

		if self.sa_sessionmaker == None:
			self.sa_sessionmaker = sessionmaker(bind=self.sa_engine)
		return self.sa_sessionmaker()