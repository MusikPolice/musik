import datetime
import hashlib
import os
import os.path
import uuid

from musik import config

from sqlalchemy import Column, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import String, Integer, DateTime, Boolean, BigInteger, Enum
from sqlalchemy.orm import backref, relationship, sessionmaker


# Helper to map and register a Python class a db table
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    passhash = Column(String, nullable=False)
    created = Column(DateTime, nullable=False)
    token = Column(String)
    token_expires = Column(DateTime)

    def __init__(self, username, password):
        """Creates a new user with the specified username and password"""
        self.username = username
        self.passhash = self.password_hash(username, password)
        self.created = datetime.datetime.utcnow()

    def password_hash(self, username, password):
        """Hashes the specified username and password and returns the result. The resulting
        hash can be stored in or compared to the passhash column of the User table."""
        hash = hashlib.sha512()
        hash.update(username)
        hash.update(password)
        hash.update(config.get("General", "salt"))
        return hash.hexdigest()

    def generate_token(self):
        """Generates a unique token for the user and sets its expiry date to one hour from now."""
        self.token = uuid.uuid4().hex
        self.update_token_expiry()
        return self.token

    def update_token_expiry(self):
        """Sets the token expiry date ahead by one hour from now."""
        self.token_expires = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

    def as_dict(self):
        """Returns a representation of the user as a dictionary that does not contain the
        passhash field."""
        u = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        del u['passhash']
        return u

    def as_dict_safe(self):
        """Returns a representation of the user as a dictionary that does not contain the
        passhash, token, or token_expires fields."""
        u = self.as_dict()
        del u['token']
        del u['token_expires']
        return u


class LogEntry(Base):
    """Error and warning messages are written to the database and to log files."""
    __tablename__ = 'log_entries'

    id = Column(Integer, primary_key=True)
    created = Column(DateTime, nullable=False)
    severity = Column(Enum('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', name='severity'), nullable=False)
    classpath = Column(String)
    message = Column(String)
    stack_trace = Column(String, nullable=True)

    def __init__(self, severity, classpath, message, stack_trace=None):
        Base.__init__(self)
        self.created = datetime.datetime.utcnow()
        self.severity = severity
        self.classpath = classpath
        self.message = message
        if stack_trace is not None:
            self.stack_trace = stack_trace

    def __unicode__(self):
        return u'<LogEntry(created=%s, severity=%s, classpath=%s, message=%s>' % (str(created), str(severity), classpath, message)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def as_dict(self):
        """Returns a representation of the log entry as a dictionary"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


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
        self.created = datetime.datetime.utcnow()

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
    id = Column(Integer, primary_key=True)  # unique id
    name = Column(String)                   # artist name
    name_sort = Column(String)              # sortable artist name
    musicbrainz_artistid = Column(String)   # unique 36-digit musicbrainz hex string

    # TODO: make musicbrainz_artistid unique!

    def __init__(self, name):
        Base.__init__(self)
        self.name = name
        self.name_sort = name

    # calculates the number of tracks linked to this artist by expanding its albums link
    def numTracks(self):
        numTracks = 0;
        if self.albums is None:
            return 0;

        for album in self.albums:
            numTracks += album.numTracks();
        return numTracks;

    # calculates the number of albums linked to this artist by expanding its albums link
    def numAlbums(self):
        if self.albums is None:
            return 0;
        return len(self.albums);

    def __unicode__(self):
        return u'<Artist(name=%s)>' % self.name

    def __str__(self):
        return unicode(self).encode('utf-8')

    def as_dict(self, ignored=[]):
        """Returns a representation of the artist as a dictionary.
        Columns specified in the ignored list will not be included in the dictionary."""
        artist_dict = {}

        # add table columns to the dict
        for column in self.__table__.columns:
            if (column.name not in ignored):
                artist_dict[column.name] = getattr(self, column.name)

        # add computed columns to the dict
        if self.albums is not None and 'albums' not in ignored:
            # when adding this artist's albums, we have to ignore their artist field because including
            # it causes infinite recursion and a stack overflow
            artist_dict['albums'] = sorted([album.as_dict(ignored=['artist', 'discs', 'tracks']) for album in self.albums], key=lambda album: album['title_sort'])

        if 'numTracks' not in ignored:
            artist_dict['numTracks'] = self.numTracks();

        if 'numAlbums' not in ignored:
            artist_dict['numAlbums'] = self.numAlbums();

        return artist_dict


class Album(Base):
    """An album is a platonic ideal of a collection of released songs.
    Back in the day, the only way to get songs was on some physical medium.
    Modern listeners may not identify with albums in the classical sense, so
    this class is not intended to represent a physical item, but rather a
    collection of related songs that may or may not have a physical representation.
    """
    __tablename__ = 'albums'
    id = Column(Integer, primary_key=True)                  # unique id
    albumstatus = Column(String)                            # musicbrainz album status
    albumtype = Column(String)                              # musicbrainz album type
    artist_id = Column(Integer, ForeignKey('artists.id'))   # the artist that recorded this album
    asin = Column(String)                                   # amazon standard identification number - only if physical
    catalognum = Column(String)                             # a quasi-unique identifier assigned to the album by the label
    compilation = Column(Boolean)                           # whether or not this album is a compilation
    country = Column(String)                                # the country that this album was released in
    label = Column(String)                                  # the record label that released this album
    mb_albumid = Column(String)                             # unique 36-digit musicbrainz hex string
    mb_releasegroupid = Column(String)                      # unique identifer of label that released the album
    media_type = Column(String)                             # the type of media (CD, etc)
    title = Column(String)                                  # the title of the album
    title_sort = Column(String)                             # sortable title of the album
    year = Column(Integer)                                  # the year in which the album was released

    # computed columns that link to other objects
    artist = relationship('Artist', backref=backref('albums', order_by=id))

    def __init__(self, title):
        Base.__init__(self)
        self.title = title
        self.title_sort = title

    # returns the number of tracks linked to this album
    def numTracks(self):
        if self.tracks is None:
            return 0;
        return len(self.tracks);

    def __unicode__(self):
        return u'<Album(title=%s)>' % self.title

    def __str__(self):
        return unicode(self).encode('utf-8')

    def as_dict(self, ignored=[]):
        """Returns a representation of the album as a dictionary.
        Columns specified in the ignored list will not be included in the dictionary."""
        album_dict = {}

        # add table columns to dict
        for column in self.__table__.columns:
            if column.name not in ignored:
                album_dict[column.name] = getattr(self, column.name)

        # add computed columns to dict
        if self.artist is not None and 'artist' not in ignored:
            album_dict['artist'] = self.artist.as_dict(ignored=['albums'])

        if self.discs is not None and 'discs' not in ignored:
            # all discs have the same album as a parent, so ignore this attribute on child discs or
            # else risk a stack overflow thanks to unbounded recursion
            album_dict['discs'] = sorted([disc.as_dict(ignored=['album', 'tracks']) for disc in self.discs], key=lambda disc: (0 if disc['discnumber'] is None else int(disc['discnumber'])))

        if self.tracks is not None and 'tracks' not in ignored:
            # no need to include all of the computed columns for every track - that would be a waste
            album_dict['tracks'] = sorted([track.as_dict(ignored=['album', 'album_artist', 'artist', 'disc']) for track in self.tracks], key=lambda track: (0 if track['tracknumber'] is None else int(track['tracknumber'])))

        if 'numTracks' not in ignored:
            album_dict['numTracks'] = self.numTracks();

        return album_dict


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
    id = Column(Integer, primary_key=True)               # unique id
    album_id = Column(Integer, ForeignKey('albums.id'))  # the album that this disc belongs to
    discnumber = Column(String)                          # the play order of this disc in the collection
    disc_subtitle = Column(String)                       # the subtitle (if applicable) of this disc
    num_tracks = Column(Integer)                         # total tracks on the disc

    # relationships
    album = relationship('Album', backref=backref('discs', order_by=discnumber, lazy='dynamic'))

    def __init__(self, discnumber):
        Base.__init__(self)
        self.discnumber = discnumber

    def __unicode__(self):
        return u'<Disc(album=%s, discnumber=%s)>' % (self.album, self.discnumber)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def as_dict(self, ignored=[]):
        """Returns a representation of the disc as a dictionary.
        Columns specified in the ignored list will not be included in the dictionary."""
        disc_dict = {}

        # add table columns to dict
        for column in self.__table__.columns:
            if column.name not in ignored:
                disc_dict[column.name] = getattr(self, column.name)

        # add computed columns to dict
        if 'album' not in ignored:
            disc_dict['album'] = self.album.as_dict()

        if 'tracks' not in ignored:
            disc_dict['tracks'] = sorted([track.as_dict() for track in self.trackcks], key=lambda track: int(track['tracknumber']))

        return disc_dict


class Track(Base):
    """A track is a single audio file, which usually corresponds to a distinct
    song, comedy routine, or book chapter. Tracks can be grouped into Albums,
    and are usually created by one or more Artists.
    """
    __tablename__ = 'tracks'

    # fields from metadata
    id = Column(Integer, primary_key=True)                      # unique id
    uri = Column(String)                                        # physical location of the track file
    album_id = Column(Integer, ForeignKey('albums.id'))         # the album that contains the track
    albumartist_id = Column(Integer, ForeignKey('artists.id'))  # the artist that recorded the album
    artist_id = Column(Integer, ForeignKey('artists.id'))       # the artist that recorded the track
    bitdepth = Column(Integer)                                  # Number of bits per sample
    bitrate = Column(Integer)                                   # Number of bits per second
    bpm = Column(Integer)                                       # beats per minute
    channels = Column(Integer)                                  # The number of channels in the audio
    comments = Column(String)                                   # Comments
    composer_id = Column(Integer, ForeignKey('artists.id'))     # the artist that composed the track
    date = Column(DateTime)                                     # date that the track was released
    disc_id = Column(Integer, ForeignKey('discs.id'))           # disc of the album that the track appeared on
    encoder = Column(String)                                    # encoder that created the digital file
    format = Column(String)                                     # the file format/codec
    genre = Column(String)                                      # genre of track contents
    language = Column(String)                                   # language code
    length = Column(BigInteger)                                 # length of the track in seconds
    lyrics = Column(String)                                     # the lyrics to the song
    mb_trackid = Column(String)                                 # unique 36-digit musicbrainz hex string
    samplerate = Column(Integer)                                # sample rate
    title = Column(String)                                      # title of the track
    tracknumber = Column(Integer)                               # order of the track on the disc

    # custom fields
    playcount = Column(Integer)                                 # number of times the track was played
    rating = Column(Integer)                                    # rating of the track (0-255)
    mimetype = Column(String)                                   # IANA mimetype of the file

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

    def as_dict(self, ignored=[]):
        """Returns a representation of the track as a dictionary.
        Columns specified in the ignored list will not be included in the dictionary."""
        track_dict = {}

        # add table columns to dict
        for column in self.__table__.columns:
            if column.name not in ignored:
                track_dict[column.name] = getattr(self, column.name)

        # add computed columns to dict
        if self.album is not None and 'album' not in ignored:
            track_dict['album'] = self.album.as_dict(ignored=['artist'])

        if self.album_artist is not None and 'album_artist' not in ignored:
            track_dict['album_artist'] = self.album_artist.as_dict(ignored=['albums'])

        if self.artist is not None and 'artist' not in ignored:
            track_dict['artist'] = self.artist.as_dict(ignored=['albums'])

        if self.disc is not None and 'disc' not in ignored:
            track_dict['disc'] = self.disc.as_dict(ignored=['tracks'])

        return track_dict


class UserAction(Base):
    """An action that was performed by some user at some time. Used to report statistics and track activity that
    informs shuffle play, song recommendations, etc."""

    __tablename__ = 'user_actions'

    id = Column(Integer, primary_key=True)
    created = Column(DateTime, nullable=False)
    userId = Column(Integer, ForeignKey('users.id'), nullable=False)
    actionType = Column(Enum('LOG_IN', 'START_TRACK', 'COMPLETE_TRACK', 'SKIP_TRACK', name='action_type'), nullable=False)
    artistId = Column(Integer, ForeignKey('artists.id'))
    albumId = Column(Integer, ForeignKey('albums.id'))
    trackId = Column(Integer, ForeignKey('tracks.id'))

    def __init__(self, userId, actionType, artistId, albumId, trackId):
        self.created = datetime.datetime.utcnow()
        self.userId = userId
        self.actionType = actionType
        self.artistId = artistId
        self.albumId = albumId
        self.trackId = trackId


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
