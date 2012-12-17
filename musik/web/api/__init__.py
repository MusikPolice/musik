from musik.web.api import library
from musik.web.api import streaming
from musik.web.api import importmedia

class API():
	albums = library.Albums()
	artists = library.Artists()
	discs = library.Discs()
	tracks = library.Tracks()
	stream = streaming.Track()
	importer = importmedia.Importer()