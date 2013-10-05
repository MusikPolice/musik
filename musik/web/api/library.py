from musik import log

import cherrypy
from musik.db import Album, Artist, Disc, Track
import musik.web.api.library
from musik.util import DateTimeEncoder

import json
import random


def _query(obj, sortby, params):
    """Performs a generic database query and returns the results as a dictionary.
    obj: The musik.db object to query (Track, Artist, Album, etc)
    sortby: The field of obj to sort the results by (Track.title, Artist.name, etc)
    params: A list of key/value pairs to query with, where key is the database obj
            field and value is the value to search for. Strings will be matched with
            a LIKE clause, other values are matched with strict equality.
    """
    #get the set of fields that makes up the type
    fields = {c.name: c for c in obj.__table__.columns}

    #split the query into key:value pairs
    query = []
    for index in range(0, len(params) - 1, 2):
        if params[index] not in fields:
            #invalid key specified
            raise cherrypy.HTTPError(400, "Invalid query string specified. %s does not contain a field named %s." % (str(obj), params[index]))
        query.append(dict([(params[index], params[index + 1])]))

    q = cherrypy.request.db.query(obj)
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
    results = []
    for a in q.order_by(sortby).all():
        results.append(a.as_dict())

    return results


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

        # do the query
        results = _query(Album, Album.title_sort, params)
        return json.dumps(results, cls=DateTimeEncoder)


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

        # do the query
        results = _query(Artist, Artist.name_sort, params)
        return json.dumps(results, cls=DateTimeEncoder)


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

        # do the query
        results = _query(Disc, Disc.id, params)
        return json.dumps(results, cls=DateTimeEncoder)


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

        # catch random track requests
        if len(params) == 1 and params[0] == 'random':
            return self.random_track()

        # do the query
        results = _query(Track, Track.title, params)
        return json.dumps(results, cls=DateTimeEncoder)

    def random_track(self):
        """Returns a random track from the library."""

        cherrypy.response.headers['Content-Type'] = 'application/json'
        self.log.info(u'RandomTracks called.')

        q = cherrypy.request.db.query(Track).all()
        track = q[random.randint(0, len(q) - 1)]

        return json.dumps(track.as_dict(), cls=DateTimeEncoder)
