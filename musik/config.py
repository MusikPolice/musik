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
