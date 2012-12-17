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
	title = Column(String)									# the title of the album
	title_sort = Column(String)								# sortable title of the album
	artist_id = Column(Integer, ForeignKey('artists.id'))	# the artist that recorded this album
	asin = Column(String)									# amazon standard identification number - only if physical
	barcode = Column(String)								# physical album barcode
	compilation = Column(Boolean)							# whether or not this album is a compilation
	media_type = Column(String)								# the type of media (CD, etc)
	musicbrainz_albumid = Column(String)					# unique 36-digit musicbrainz hex string
	musicbrainz_albumstatus = Column(String)				# unique 36-digit musicbrainz hex string
	musicbrainz_albumtype = Column(String)					# unique 36-digit musicbrainz hex string
	organization = Column(String)							# organization that released the album (usually a record company)
	releasecountry = Column(String)							# the country that this album was released in

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
	musicbrainz_discid = Column(String)					# unique 36-digit musicbrainz hex string

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

	# columns
	id = Column(Integer, primary_key=True)						# unique id
	uri = Column(String)										# physical location of the track file
	artist_id = Column(Integer, ForeignKey('artists.id'))		# the artist that recorded the track
	album_id = Column(Integer, ForeignKey('albums.id'))			# the album that contains the track
	album_artist_id = Column(Integer, ForeignKey('artists.id'))	# the artist that released the album
	arranger_id = Column(Integer, ForeignKey('artists.id'))		# the artist that arranged the track
	author_id = Column(Integer, ForeignKey('artists.id'))		# the author that wrote the track
	bpm = Column(Integer)										# beats per minute
	composer_id = Column(Integer, ForeignKey('artists.id'))		# the artist that composed the track
	conductor_id = Column(Integer, ForeignKey('artists.id'))	# the artist that conducted the track
	copyright = Column(String)									# copyright information
	date = Column(String)										# date that the track was released
	disc_id = Column(Integer, ForeignKey('discs.id'))			# disc of the album that the track appeared on
	encodedby = Column(String)									# encoder that created the digital file
	genre = Column(String)										# genre of track contents
	isrc = Column(String) 										# ISO 3901 12-character International Standard Recording Code
	length = Column(BigInteger)									# length of the track in milliseconds
	lyricist_id = Column(Integer, ForeignKey('artists.id'))		# the artist that wrote the lyrics of the track
	mood = Column(String)										# description of the mood of the track
	musicbrainz_trackid = Column(String)						# unique 36-digit musicbrainz hex string
	musicbrainz_trmid = Column(String)							# semi-unique trm fingerprint
	musicip_fingerprint = Column(String)						# unique musicip (gracenote) fingerprint
	musicip_puid = Column(String)								# unique musicip (gracenote) id
	performer_id = Column(Integer, ForeignKey('artists.id'))	# artist that performed the track
	title = Column(String)										# title of the track
	title_sort = Column(String)									# sortable title of the track
	tracknumber = Column(Integer)								# order of the track on the disc
	subtitle = Column(String)									# sub title of the track
	website = Column(String)									# a website for the track
	playcount = Column(Integer)									# number of times the track was played
	rating = Column(Integer)									# rating of the track (0-255)

	# relationships
	artist = relationship('Artist', primaryjoin='Artist.id == Track.artist_id')
	album_artist = relationship('Artist', primaryjoin='Artist.id == Track.album_artist_id')
	arranger = relationship('Artist', primaryjoin='Artist.id == Track.arranger_id')
	composer = relationship('Artist', primaryjoin='Artist.id == Track.composer_id')
	conductor = relationship('Artist', primaryjoin='Artist.id == Track.conductor_id')
	lyricist = relationship('Artist', primaryjoin='Artist.id == Track.lyricist_id')
	performer = relationship('Artist', primaryjoin='Artist.id == Track.performer_id')
	author = relationship('Artist', primaryjoin='Artist.id == Track.author_id')
	album = relationship('Album', backref=backref('tracks', order_by=tracknumber))
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