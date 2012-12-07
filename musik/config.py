from ConfigParser import ConfigParser
import os

def get(section, option):
	""" A quick and dirty wrapper function that gets the requested option value
	from the specified section of the musik.cfg config file in the root
	directory of the application. If musik.cfg does not exist, it is created
	with a set of sane default values.
	"""
	# finds the parent directory of the directory that this file resides in
	parent_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
	config_path = os.path.abspath(os.path.join(parent_directory, "musik.cfg"))

	# TODO: specify default configuration values here using the set method
	conf = ConfigParser()
	conf.add_section("General")
	conf.set("General", "database_path", os.path.abspath(os.path.join(parent_directory, "musik.db")))
	conf.set("General", "server_domain_name", "localhost")
	conf.set("General", "server_port", "8080")

	conf.add_section("Logging")
	conf.set("Logging", "log_to_console", "true")
	conf.set("Logging", "log_to_files", "true")
	conf.set("Logging", "log_directory_path", os.path.abspath(os.path.join(parent_directory, "logs")))

	if os.path.exists(config_path):
		# if a config file exists, read in values that overwrite the defaults above
		conf.readfp(open(config_path, "r"))
	else:
		# otherwise, write the values above to a file that can be modified by the user
		conf.write(open(config_path, "w"))

	# return the requested value
	return conf.get(section, option)


def get_root_directory():
	"""Returns the root directory that Musik is installed in. This is where
	you'll find the database, config files, and musik.py
	"""
	return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def get_server_port():
	"""Returns the server port configuration setting. This can be overriden
	with the PORT environment variable.
	"""
	return int(os.environ.get('PORT', get('General', 'server_port')))


def get_site_root():
	"""Returns the base URI of the web application. This includes the scheme
	(http://), the domain name, and the port that the application is being
	served from.
	"""
	port = get("General", "server_port")

	if port is None or port == "80":
		return "http://%s" % get("General", "server_domain_name")
	else:
		return "http://%s:%s" % (get("General", "server_domain_name"), str(port))