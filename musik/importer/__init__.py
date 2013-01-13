from datetime import datetime
import mimetypes
import os
import re
import threading
import time

from musik import log
from musik.db import DatabaseWrapper, ImportTask, Track, Album, Artist, Disc
from musik.importer.mediafile import MediaFile, UnreadableFileError


class ImportThread(threading.Thread):

    running = True      # whether or not the thread should continue to run
    sa_session = None   # database session
    log = None          # logging instance

    def __init__(self):
        """Creates a new instance of ImportThread and connects to the database.
        This design pattern is important: since the constructor runs synchonously,
        it ensures that two threads don't attempt to initialize the database at
        the same time.
        """
        super(ImportThread, self).__init__(name=__name__)
        db = DatabaseWrapper()
        self.sa_session = db.get_session()

        # create a log object that uses the same session that we do so that we can write error messages
        # during transactions
        self.log = log.Log(__name__, self.sa_session)

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
                    self.log.info(u'Processing task %s' % task.uri)

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
                    self.log.info(u'finished processing task %s' % task.uri)

                time.sleep(1)
        finally:
            # always clean up - your mom doesn't work here
            if self.sa_session != None:
                self.sa_session.close()
                self.sa_session = None

    def import_directory(self, uri):
        """Adds the specified directory to the library.
        In practice, this implements a recursive breadth-first search over the
        subtree rooted at uri. All files with a mimetype that starts with the
        string 'audio' will be put back into the import queue for additional
        processing. Returns True."""
        search_queue = [uri]
        while len(search_queue) > 0:
            # this is the current working directory
            baseuri = search_queue.pop(0)
            if os.path.isdir(baseuri) == False:
                continue

            # TODO: directory permissions. Make sure that we can read before we try to
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
        return True

    def is_mime_type_supported(self, uri):
        """Takes a guess at the mimetype of the file at the specified uri.
        Returns True if the mimetype could be inferred and file contains audio
        data, false otherwise. Note that this function does not care whether or
        not the file actually exists."""
        (mimetype, encoding) = mimetypes.guess_type(uri)
        return mimetype is not None and mimetype.startswith('audio')

    def import_file(self, uri):
        """Adds the specified file to the library.
        Returns True if the file was successfully added to the database, or
        False if metadata could not be read or the file could not be added."""

        # ensure that the uri isn't already in our library - we don't want duplicates
        track = self.sa_session.query(Track).filter(Track.uri == uri).first()
        if track == None:
            track = Track(uri)
            self.sa_session.add(track)
        else:
            self.log.info(u'The file %s is already in the library. Updating metadata...' % uri)

        try:
            metadata = MediaFile(uri)
        except UnreadableFileError:
            self.log.error(u'Could not extract metadata from %s' % uri)
            return False

        # artist
        artist = self.find_artist(metadata.artist, metadata.artist_sort, metadata.mb_artistid)
        if artist != None:
            if track.artist == None:
                track.artist = artist
                self.sa_session.add(artist)
            elif track.artist.id != artist.id:
                # TODO: conflict!
                self.log.warning(u'Artist conflict for track %s: %s != %s' % (track.uri, track.artist.name, artist.name))

        # album artist - use the artist if metadata isn't set
        album_artist = self.find_artist(metadata.albumartist, metadata.albumartist_sort)
        if album_artist != None:
            if track.album_artist == None:
                track.album_artist = album_artist
                self.sa_session.add(album_artist)
            elif track.album_artist.id != album_artist.id:
                # TODO: conflict!
                self.log.warning(u'Album artist conflict for track %s: %s != %s' % (track.uri, track.album_artist.name, album_artist.name))
        elif artist != None:
            if track.album_artist == None:
                track.album_artist = artist
                self.sa_session.add(artist)
            elif track.album_artist.id != artist.id:
                # TODO: conflict!
                self.log.warning(u'Album artist conflict for track %s: %s != %s' % (track.uri, track.album_artist.name, artist.name))

        # composer
        composer = self.find_artist(metadata.composer, '')
        if composer != None:
            if track.composer == None:
                track.composer = composer
                self.sa_session.add(composer)
            elif track.composer.id != composer.id:
                # TODO: conflict!
                self.log.warning(u'Composer conflict for track %s: %s != %s' % (track.uri, track.composer.name, composer.name))

        # album
        album = self.find_album(metadata.album, metadata.mb_albumid, track.artist, metadata)
        if album != None:
            if track.album == None:
                track.album = album
                self.sa_session.add(album)
            elif track.album.id != album.id:
                # TODO: conflict!
                self.log.warning(u'Album conflict for track %s: %s != %s' % (track.uri, track.album.title, album.title))

        # bitdepth
        if metadata.bitdepth != 0:
            if track.bitdepth == None:
                track.bitdepth = metadata.bitdepth
            elif track.bitdepth != metadata.bitdepth:
                #TODO: conflict!
                self.log.warning(u'Track bitdepth conflict for track %s: %d != %d' % (track.uri, track.bitdepth, metadata.bitdepth))

        # bitrate
        if metadata.bitrate != 0:
            if track.bitrate == None:
                track.bitrate = metadata.bitrate
            elif track.bitrate != metadata.bitrate:
                #TODO: conflict!
                self.log.warning(u'Track bitrate conflict for track %s: %d != %d' % (track.uri, track.bitrate, metadata.bitrate))

        #bpm
        if metadata.bpm != 0:
            if track.bpm == None:
                track.bpm = metadata.bpm
            elif track.bpm != metadata.bpm:
                # TODO: conflict!
                self.log.warning(u'Track bpm conflict for track %s: %d != %d' % (track.uri, track.bpm, metadata.bpm))

        #channels
        if metadata.channels != 0:
            if track.channels == None:
                track.channels = metadata.channels
            elif track.channels != metadata.channels:
                # TODO: conflict!
                self.log.warning(u'Track channels conflict for track %s: %d != %d' % (track.uri, track.channels, metadata.channels))

        # comments
        if metadata.comments != '':
            if track.comments == None:
                track.comments = metadata.comments
            elif track.comments != metadata.comments:
                #TODO: conflict!
                self.log.warning(u'Track comments conflict for track %s: %s != %s' % (track.uri, track.comments, metadata.comments))

        #date
        if metadata.date != None:
            if track.date == None:
                track.date = metadata.date
            elif track.date != metadata.date:
                # TODO: conflict!
                self.log.warning(u'Track date conflict for track %s: %s != %s' % (track.uri, unicode(track.date), unicode(metadata.date)))

        # disc
        if track.album != None:
            disc = self.find_disc(track.album, metadata.disc, metadata.disctitle, metadata.disctotal)
            for d in track.album.discs:
                if d.id == disc.id:
                    # found disc is already linked - don't add it again
                    disc = None
            if disc != None:
                track.album.discs.append(disc)

        #encoder
        if metadata.encoder != '':
            if track.encoder == None:
                track.encoder = metadata.encoder
            elif track.encoder != metadata.encoder:
                # TODO: conflict!
                self.log.warning(u'Track encoder conflict for track %s: %s != %s' % (track.uri, track.encoder, metadata.encoder))

        # format
        if metadata.format != '':
            if track.format == None:
                track.format = metadata.format
            elif track.format != metadata.format:
                #TODO: conflict!
                self.log.warning(u'Track format conflict for track %s: %s != %s' % (track.uri, track.format, metadata.format))

        #genre
        if metadata.genre != '':
            if track.genre == None:
                track.genre = metadata.genre
            elif track.genre != metadata.genre:
                # TODO: conflict!
                self.log.warning(u'Track genre conflict for track %s: %s != %s' % (track.uri, track.genre, metadata.genre))

        # language
        if metadata.language != '':
            if track.language == None:
                track.language = metadata.language
            elif track.language != metadata.language:
                #TODO: conflict!
                self.log.warning(u'Track language conflict for track %s: %s != %s' % (track.uri, track.language, metadata.language))

        #length
        if metadata.length != 0:
            if track.length == None:
                track.length = metadata.length
            elif track.length != metadata.length:
                # TODO: conflict!
                self.log.warning(u'Track length conflict for track %s: %d != %d' % (track.uri, track.length, metadata.length))

        # lyrics
        if metadata.lyrics != '':
            if track.lyrics == None:
                track.lyrics = metadata.lyrics
            elif track.lyrics != metadata.lyrics:
                #TODO: conflict!
                self.log.warning(u'Track lyrics conflict for track %s: %s != %s' % (track.uri, track.lyrics, metadata.lyrics))

        #mb_trackid
        if metadata.mb_trackid != '':
            if track.mb_trackid == None:
                track.mb_trackid = metadata.mb_trackid
            elif track.mb_trackid != metadata.mb_trackid:
                # TODO: conflict!
                self.log.warning(u'Track mb_trackid conflict for track %s: %s != %s' % (track.uri, track.mb_trackid, metadata.mb_trackid))

        #samplerate
        if metadata.samplerate != 0:
            if track.samplerate == None:
                track.samplerate = metadata.samplerate
            elif track.samplerate != metadata.samplerate:
                # TODO: conflict!
                self.log.warning(u'Track samplerate conflict for track %s: %d != %d' % (track.uri, track.samplerate, metadata.samplerate))

        # title
        if metadata.title != '':
            if track.title == None:
                track.title = metadata.title
            elif track.title != metadata.title:
                # TODO: conflict!
                self.log.warning(u'Track title conflict for track %s: %s != %s' % (track.uri, track.title, metadata.title))

        # tracknumber
        if metadata.track != 0:
            if track.tracknumber == None:
                track.tracknumber = metadata.track
            elif track.tracknumber != metadata.track:
                # TODO: conflict!
                self.log.warning(u'Track tracknumber conflict for track %s: %d != %d' % (track.uri, track.tracknumber, metadata.track))

        # if we couldn't determine track, album, artist from metadata, try to snag it from the path
        # track name = file name
        # album title = last directory in path,
        # artist name = second last directory in path.
        (dirName, fileName) = os.path.split(uri)
        (fileBaseName, fileExtension) = os.path.splitext(fileName)
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

        self.log.info(u'Added %s by %s to the current session.' % (track.title, track.artist.name))

        #commit the transaction
        self.sa_session.commit()

    def find_artist(self, name='', name_sort='', musicbrainz_id=''):
        """Searches the database for an existing artist that matches the specified criteria.
        If no existing artist can be found, a new artist is created with the criteria.
        When a new artist is created, it is not added to the database. This is the responsibility
        of the calling function.
        """
        artist = None
        if musicbrainz_id != '':
            # we trust musicbrainz_artistid the most because it infers that
            # some other tagger has already verified the metadata.
            artist = self.sa_session.query(Artist).filter(Artist.musicbrainz_artistid == musicbrainz_id).first()
            if artist != None:
                # found an existing artist in our db - compare its metadata
                # to the new info. Always prefer existing metadata over new.
                self.log.info(u'Artist name musicbrainz_artistid search found existing artist %s in database' % artist.name)
                if name != '':
                    if artist.name == None:
                        artist.name = name
                    elif artist.name != name:
                        # TODO: conflict -> schedule musicbrainz task!
                        self.log.warning(u'Artist name conflict for musicbrainz_artistid %s: %s != %s' % (artist.musicbrainz_artistid, artist.name, name))
                if name_sort != '':
                    if artist.name_sort == None:
                        artist.name_sort = name_sort
                    elif artist.name_sort != name_sort:
                        # TODO: conflict -> schedule musicbrainz task!
                        self.log.warning(u'Artist sort name conflict for musicbrainz_artistid %s: %s != %s' % (artist.musicbrainz_artistid, artist.name_sort, name_sort))

        if artist == None and name != '':
            # if we don't have musicbrainz_artistid or there is no matching
            # artist in our db, try to find an existing artist by name
            artist = self.sa_session.query(Artist).filter(Artist.name == name).first()
            if artist != None:
                self.log.info(u'Artist name search found existing artist %s in database' % artist.name)
                # found an existing artist in our db - compare its metadata
                # to the new info. Always prefer existing metadata over new.
                if name_sort != '':
                    if artist.name_sort == None:
                        artist.name_sort = name_sort
                    elif artist.name_sort != name_sort:
                        self.log.warning(u'Artist sort name conflict for artist %s: %s != %s' % (artist.name, artist.name_sort, name_sort))
            else:
                # an existing artist could not be found in our db. Make a new one
                artist = Artist(name)
                if name_sort != '':
                    artist.name_sort = name_sort
                if musicbrainz_id != '':
                    artist.musicbrainz_artistid = musicbrainz_id
                # add the artist object to the DB
                self.log.info(u'Artist not found in database. Created new artist %s' % artist.name)

        # return the artist that we found and/or created
        return artist

    def find_album(self, title='', musicbrainz_id='', artist=None, metadata=None):
        """Searches the database for an existing album that matches the specified criteria.
        If no existing album can be found, a new album is created with the criteria.
        When a new album is created, it is not added to the database. This is the responsibility of
        the calling function.
        """
        album = None

        # we trust mb_albumid the most because it infers that
        # some other tagger has already verified the metadata.
        if musicbrainz_id != '':
            album = self.sa_session.query(Album).filter(Album.mb_albumid == musicbrainz_id).first()

        # if we don't have mb_albumid or there is no matching
        # album in our db, try to find an existing album by title and artist
        if album == None and title != '' and artist != None:
            album = self.sa_session.query(Album).filter(Album.title == title, Album.artist_id == artist.id).first()

        # an existing album could not be found in our db. Make a new one
        if album == None:
            album = Album(title)
            self.log.info(u'Album not found in database. Created new album %s' % album.title)

        # we either found or created the album. now verify its metadata
        if album != None and metadata != None:
            # albumstatus
            if metadata.albumstatus != '':
                if album.albumstatus == None:
                    album.albumstatus = metadata.albumstatus
                elif album.albumstatus != metadata.albumstatus:
                    #TODO: conflict!
                    self.log.warning(u'Album albumstatus conflict for album %s: %s != %s' % (album.title, album.albumstatus, metadata.albumstatus))

            # albumtype
            if metadata.albumtype != '':
                if album.albumtype == None:
                    album.albumtype = metadata.albumtype
                elif album.albumtype != metadata.albumtype:
                    #TODO: conflict!
                    self.log.warning(u'album albumtype conflict for album %s: %s != %s' % (album.title, album.albumtype, metadata.albumtype))

            # artist
            if artist != None:
                if album.artist == None:
                    album.artist = artist
                elif album.artist_id != artist.id:
                    # TODO: conflict -> schedule musicbrainz task!
                    self.log.warning(u'Album artist conflict for mb_albumid %s: %s != %s' % (album.mb_albumid, album.artist.name, artist.name))

            # asin
            if metadata.asin != '':
                if album.asin == None:
                    album.asin = metadata.asin
                elif album.asin != metadata.asin:
                    #TODO: conflict!
                    self.log.warning(u'Album asin conflict for album %s: %s != %s' % (album.title, album.asin, metadata.asin))

            # catalognum
            if metadata.catalognum != '':
                if album.catalognum == None:
                    album.catalognum = metadata.catalognum
                elif album.catalognum != metadata.catalognum:
                    #TODO: conflict!
                    self.log.warning(u'album catalognum conflict for album %s: %s != %s' % (album.title, album.catalognum, metadata.catalognum))

            # compilation
            if album.compilation == None:
                album.compilation = metadata.comp
            elif album.compilation != metadata.comp:
                # TODO: conflict!
                self.log.warning(u'album comp conflict for album %s: %b != %b' % (album.title, album.compilation, metadata.comp))

            # country
            if metadata.country != '':
                if album.country == None:
                    album.country = metadata.country
                elif album.country != metadata.country:
                    #TODO: conflict!
                    self.log.warning(u'album country conflict for album %s: %s != %s' % (album.title, album.country, metadata.country))

            # label/organization
            if metadata.label != '':
                if album.label == None:
                    album.label = metadata.label
                elif album.label != metadata.label:
                    #TODO: conflict!
                    self.log.warning(u'Album label conflict for album %s: %s != %s' % (album.title, album.label, metadata.label))

            #mb_releasegroupid
            if metadata.mb_releasegroupid != '':
                if album.mb_releasegroupid == None:
                    album.mb_releasegroupid = metadata.mb_releasegroupid
                elif album.mb_releasegroupid != metadata.mb_releasegroupid:
                    # TODO: conflict!
                    self.log.warning(u'album mb_releasegroupid conflict for album %s: %s != %s' % (album.title, album.mb_releasegroupid, metadata.mb_releasegroupid))

            #media type
            if metadata.media != '':
                if album.media_type == None:
                    album.media_type = metadata.media
                elif album.media_type != metadata.media:
                    # TODO: conflict!
                    self.log.warning(u'album media_type conflict for album %s: %s != %s' % (album.title, album.media_type, metadata.media))

            if title != '':
                if album.title == None:
                    album.title = title
                    album.title_sort = title
                elif album.title != title:
                    # TODO: conflict -> schedule musicbrainz task!
                    self.log.warning(u'Album title conflict for mb_albumid %s: %s != %s' % (album.mb_albumid, album.title, title))

            # year
            if metadata.track != 0:
                if album.year == None:
                    album.year = metadata.track
                elif album.year != metadata.track:
                    # TODO: conflict!
                    self.log.warning(u'album.year conflict for track %s: %d != %d' % (metadata.title, album.year, metadata.year))

        return album

    def find_disc(self, album=None, discnumber=0, discsubtitle='', num_tracks=0):
        """Tries to find an existing disc that matches the specified criteria.
        If an existing disc cannot be found, creates a new disc with the specified criteria.
        """
        # first see if there's a disc that's already linked to the album that
        # has either the specified musicbrainz_discid or discnumber.
        disc = None
        if album != None:
            for d in album.discs:
                if discnumber != 0:
                    if d.discnumber == discnumber:
                        disc = d

        # if we found a disc in the existing album's collection that matches
        # the specified criteria, update any missing metadata
        if disc != None:
            self.log.info(u'Disc musicbrainz_discid/discnumber search found existing disc %s in database' % disc)
            if discnumber != 0:
                if d.discnumber == None:
                    d.discnumber = discnumber
                elif d.discnumber != discnumber:
                    # TODO: conflict!
                    self.log.warning(u'Disc number conflict for disc %s: %s != %s' % (disc, disc.discnumber, discnumber))
            if discsubtitle != '':
                if d.subtitle == None:
                    d.subtitle = discsubtitle
                elif d.subtitle != discsubtitle:
                    # TODO: Conflict!
                    self.log.warning(u'Disc subtitle conflict for disc %s: %s != %s' % (disc, disc.subtitle, discsubtitle))
            if num_tracks != 0:
                if d.num_tracks == None:
                    d.num_tracks = num_tracks
                elif d.num_tracks != num_tracks:
                    # TODO: conflict!
                    self.log.warning(u'Disc number of tracks conflict for disc %s: %s != %s' % (disc, disc.num_tracks, num_tracks))

        if disc == None and album != None and discnumber != 0:
            # musicbrainz_discid wasn't supplied or didn't yield an existing album.
            # try to search with album id and disc number instead.
            disc = self.sa_session.query(Disc).filter(Disc.album_id == album.id, Disc.discnumber == discnumber).first()
            if disc != None:
                self.log.info(u'Disc album/number search found existing disc %s in database' % disc)
                if discsubtitle != '':
                    if disc.discsubtitle == None:
                        disc.discsubtitle = discsubtitle
                    elif disc.discsubtitle != discsubtitle:
                        # TODO: conflict -> schedule musicbrainz task!
                        self.log.warning(u'Disc subtitle conflict for disc %s: %s != %s' % (disc, disc.discsubtitle, discsubtitle))
                if num_tracks != 0:
                    if disc.num_tracks == None:
                        disc.num_tracks = num_tracks
                    elif disc.num_tracks != num_tracks:
                        # TODO: conflict!
                        self.log.warning(u'Disc number of tracks conflict for disc %s: %s != %s' % (disc, disc.num_tracks, num_tracks))
            else:
                # could not find the disc in question. Create a new one instead
                disc = Disc(discnumber)
                if album != None:
                    disc.album = album
                if discsubtitle != '':
                    disc.discsubtitle = discsubtitle
                if num_tracks != 0:
                    disc.num_tracks = num_tracks
                self.log.info(u'Could not find disc in database. Created new disc %s' % disc)
                self.sa_session.add(disc)

        return disc

    def stop(self):
        """Cleans up the thread"""
        self.log.info(u'Stop has been called')
        self.running = False
