import logging
import os

from musik import config

"""A logging class that loosely wraps python's built-in logging class in order
to ensure that log files are always put in the configured directory and named
appropriately."""
class Log:
	log = None

	def __init__(self, module_name):
		"""Creates a log file in the appropriate directory with module_name as
		a file name. Also logs to the console.
		"""
		# set up logging
		self.log = logging.getLogger(module_name)
		self.log.setLevel(logging.DEBUG)

		# dictate log message formatting
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

		# only log to the console if configured to do so
		if config.get("Logging", "log_to_console") == "true":
			# create a handler that dumps log messages to the console
			ch = logging.StreamHandler()
			ch.setLevel(logging.DEBUG)

			ch.setFormatter(formatter)
			self.log.addHandler(ch)

		# only log to file if configured to do so
		if config.get("Logging", "log_to_files") == "true":
			# confirm that logging directory exists
			log_dir = config.get("Logging", "log_directory_path")
			if not os.path.isdir(log_dir):
				print u"Creating log directory %s" % log_dir
				os.mkdir(log_dir)

			# create a handler that dumps log messages to an appropriately named file
			log_path = os.path.abspath(os.path.join(log_dir, module_name + '.log'))

			fs = logging.FileHandler(log_path)
			fs.setLevel(logging.DEBUG)

			fs.setFormatter(formatter)
			self.log.addHandler(fs)


	def info(self, msg):
		"""Writes an information-level message to the log"""
		self.log.info(msg)

	def error(self, msg):
		"""Writes an error-level message to the log"""
		self.log.error(msg)

	def warning(self, msg):
		"""Writes a warning-level message to the log"""
		self.log.warning(msg)