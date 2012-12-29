import logging
import os
import string
import time

from musik import config
from musik.db import DatabaseWrapper, LogEntry

"""A logging class that loosely wraps python's built-in logging class in order
to ensure that log files are always put in the configured directory and named
appropriately."""
class Log:
	log = None

	def __init__(self, module_name, session=None):
		"""Creates a logging instance that will write messages to a log file with the specified module_name, as
		well as to the console. If the messages are of log level WARNING, ERROR, or CRITICAL, they will also be
		written to the log_entries database table.
		If the application is backed by SQLite, it's a good idea to specify a database session when the object
		is created by a thread that might log error messages while writing to the database, because SQLite locks
		the entire file on writes, which can block attempts to log to the database if the thread that is calling
		the log object is using a separate database transaction.
		Note that if a session is specified, it is the responsibility of the calling class to clean it up.
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

		# create a handler that logs to the database. By default, it logs anything WARNING, ERROR, and CRITICAL
		sqa = SqlAlchemyLogger(module_name, session)
		self.log.addHandler(sqa)


	def info(self, msg):
		"""Writes an information-level message to the log"""
		self.log.info(msg)

	def warning(self, msg):
		"""Writes a warning-level message to the log"""
		self.log.warning(msg)

	def error(self, msg):
		"""Writes an error-level message to the log"""
		self.log.error(msg)


class SqlAlchemyLogger(logging.Handler):
	"""A custom log handler that writes messages to log_entries table in the database. If the application is backed
	by SQLite, this can fail when another thread has a transaction open for writing, because SQLite locks the entire
	file for each write. As such, it's a best-try sort of thing."""
	module_name = None
	session = None
	records = []

	def __init__(self, module_name, session=None):
		logging.Handler.__init__(self)
		self.level = logging.WARNING
		self.module_name = module_name
		self.session = session


	def emit(self, record):
		responsible_for_session = False
		if self.session is None:
			# if a session wasn't specified by the calling object, create one and set a flag that ensures that
			# we will clean up after ourselves.
			db = DatabaseWrapper()
			self.session = db.get_session()
			responsible_for_session = True

		try:
			logEntry = LogEntry(record.levelname, self.module_name, self.format(record), record.exc_text)
			self.session.add(logEntry)

			if responsible_for_session:
				self.session.commit()
		except:
			print (u'WARNING: Database is locked, failed to write message to log_entries: %s' % self.format(record))
			if responsible_for_session and self.session is not None:
				self.session.rollback()
		finally:
			if responsible_for_session and self.session is not None:
				self.session.close()
				self.session = None
