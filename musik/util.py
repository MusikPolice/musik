import datetime
import json

class EasygoingDictionary(dict):
	"""A dictionary that returns None if you try to access a non-existent key.
	"""
	def __getitem__(self, key):
		if not key in self:
			return None
		return super(EasygoingDictionary, self).__getitem__(key)


class DateTimeEncoder(json.JSONEncoder):
	"""A custom JSONEncoder that converts datetime objects into their ISO
	representation. If the specified object is not of type datetime, python's
	default JSONEncoder is used."""
	def default(self, obj):
		if isinstance(obj, datetime.datetime):
			return obj.isoformat()
		elif isinstance(obj, datetime.date):
			return obj.isoformat()
		elif isinstance(obj, datetime.timedelta):
			return (datetime.datetime.min + obj).time().isoformat()
		else:
			return json.JSONEncoder.default(self, obj)