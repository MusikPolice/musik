# This file is part of audioread.
# Copyright 2011, Adrian Sampson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Decode audio files."""

class DecodeError(Exception):
    """The file could not be decoded by any backend. Either no backends
are available or each available backedn failed to decode the file.
"""

def _gst_available():
    """Determines whether pygstreamer is installed."""
    try:
        import gst
    except ImportError:
        return False
    else:
        return True


def audio_open(path):
    """Open an audio file using a library that is available on this
system.
"""
    # GStreamer.
    if _gst_available():
        from . import gstreamer
        try:
            return gstreamer.GstAudioFile(path)
        except gstreamer.GStreamerError:
            pass

    # All backends failed!
    raise DecodeError()