from musik.web.api import library
from musik.web.api import streaming
from musik.web.api import importmedia
from musik.web.api import users


class API():
    albums = library.Albums()
    artists = library.Artists()
    discs = library.Discs()
    tracks = library.Tracks()
    stream = streaming.Track()
    importer = importmedia.Importer()
    currentuser = users.CurrentUser()
    users = users.UserAccounts()  # WARNING: all methods under /users are wide open to the public
