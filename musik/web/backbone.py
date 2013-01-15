import cherrypy
from mako.lookup import TemplateLookup

# Template looker-upper that handles loading and caching of mako templates
templates = TemplateLookup(
    directories=['templates'],
    module_directory='templates/compiled')


class Musik:
    """A backbone.js front-end implementation for the Musik API"""
    @cherrypy.expose
    def index(self):
        """Renders the index.html template."""
        return templates.get_template('backbone.html').render()
