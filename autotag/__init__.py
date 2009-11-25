# This file is part of beets.
# Copyright 2009, Adrian Sampson.
# 
# Beets is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Beets is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with beets.  If not, see <http://www.gnu.org/licenses/>.

"""Facilities for automatically determining files' correct metadata.
"""

import os
from collections import defaultdict
from beets.autotag import mb
import re
from munkres import Munkres
from beets import library, mediafile

# If the MusicBrainz length is more than this many seconds away from the
# track length, an error is reported. 30 seconds may seem like overkill,
# but tracks do seem to vary a lot in the wild and this is the
# threshold used by Picard before it even applies a penalty.
LENGTH_TOLERANCE = 30

class AutotagError(Exception): pass
class InsufficientMetadataError(AutotagError): pass
class UnknownAlbumError(AutotagError): pass
class UnorderedTracksError(AutotagError): pass

def albums_in_dir(path, lib=None):
    """Recursively searches the given directory and returns an iterable
    of lists of items where each list is probably an album.
    Specifically, any folder containing any media files is an album.
    """
    for root, dirs, files in os.walk(path):
        # Get a list of items in the directory.
        items = []
        for filename in files:
            try:
                i = library.Item.from_path(os.path.join(root, filename), lib)
            except mediafile.FileTypeError:
                pass
            else:
                items.append(i)
        
        # If it's nonempty, yield it.
        if items:
            yield items

def _ie_dist(str1, str2):
    """Gives an "intuitive" edit distance between two strings. This is
    an edit distance, normalized by the string length, ignoring case
    and nonalphanumeric characters.
    """
    str1 = re.sub(r'[^a-z0-9]', '', str1.lower())
    str2 = re.sub(r'[^a-z0-9]', '', str2.lower())
    
    # Here's a nice DP edit distance implementation from Wikibooks:
    # http://en.wikibooks.org/wiki/Algorithm_implementation/Strings/
    # Levenshtein_distance#Python
    # This should probably be written in a C module.
    def levenshtein(s1, s2):
        if len(s1) < len(s2):
            return levenshtein(s2, s1)
        if not s1:
            return len(s2)
     
        previous_row = xrange(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
     
        return previous_row[-1]
    
    return levenshtein(str1, str2)

def current_metadata(items):
    """Returns the most likely artist and album for a set of Items.
    Each is determined by tag reflected by the plurality of the Items.
    """
    # The tags we'll try to determine.
    keys = 'artist', 'album'

    # Make dictionaries in which to count the freqencies of different
    # artist and album tags. We'll use this to find the most likely
    # artist and album. Defaultdicts let the frequency default to zero.
    freqs = {}
    for key in keys:
        freqs[key] = defaultdict(int)

    # Count the frequencies.
    for item in items:
        for key in keys:
            value = getattr(item, key)
            if value: # Don't count empty tags.
                freqs[key][value] += 1

    # Find max-frequency tags.
    likelies = {}
    for key in keys:
        max_freq = 0
        likelies[key] = None
        for tag, freq in freqs[key].items():
            if freq > max_freq:
                max_freq = freq
                likelies[key] = tag
    
    return (likelies['artist'], likelies['album'])

def _order_items_meta(items):
    """Orders the items based on their existing metadata. Returns
    False on failure.
    """
    ordered_items = [None]*len(items)
    available_indices = set(range(len(items)))
    
    for item in items:
        if item.track:
            index = item.track - 1
            
            # Make sure the index is valid.
            if index in available_indices:
                available_indices.remove(index)
            else:
                # Same index used twice.
                return None
                
            # Apply index.
            ordered_items[index] = item
            
        else:
            # If we have any item without an index, give up.
            return None
    
    if available_indices:
        # Not all indices were used.
        return None
    
    return ordered_items

def _order_items_match(items, trackinfo):
    """Orders the items based on how they match some canonical track
    information. This always produces a result if the numbers of tracks
    match. However, it is compuationally expensive: the core algorithm
    (for min-cost bipartite matching) is somewhere between O(n^2) and
    O(n^3); also, the cost matrix has to calculate edit distances n^2
    times. So this should be used as a fallback.
    """
    # Construct the cost matrix.
    costs = []
    for cur_item in items:
        row = []
        for canon_item in trackinfo:
            row.append(_ie_dist(cur_item.title, canon_item['title']))
        costs.append(row)
    
    # Find a minimum-cost bipartite matching.
    matching = Munkres().compute(costs)
    
    # Order items based on the matching.
    ordered_items = [None]*len(items)
    for cur_idx, canon_idx in matching:
        ordered_items[canon_idx] = items[cur_idx]
    return ordered_items

def order_items(items, trackinfo):
    """Given a list of items, put them in album order.
    """
    # Try using metadata, using matching as a fallback.
    ordered = _order_items_meta(items)
    if ordered: return ordered
    return _order_items_match(items, trackinfo)

def distance(items, info):
    """Determines how "significant" an album metadata change would be.
    Returns a float in [0.0,1.0]. The list of items must be ordered.
    """
    cur_artist, cur_album = current_metadata(items)
    
    # These accumulate the possible distance components. The final
    # distance will be dist/dist_max.
    dist = 0.0
    dist_max = 0.0
    
    # If either tag is missing, change should be confirmed.
    if len(cur_artist) == 0 or len(cur_album) == 0:
        return 1.0
    
    # Check whether the new values differ from the old ones.
    #fixme edit distance instead of 1/0
    #fixme filter non-alphanum
    if cur_artist.lower() != info['artist'].lower() or \
       cur_album.lower()  != info['album'].lower():
        dist += 1.0
        dist_max += 1.0
    
    # Find track distances.
    for item, track_data in zip(items, info['tracks']):
        # Check track length.
        if 'length' not in track_data:
            # If there's no length to check, assume the worst.
            return 1.0
        elif abs(item.length - track_data['length']) > LENGTH_TOLERANCE:
            # Abort with maximum. (fixme, something softer?)
            return 1.0
        #fixme track name
    
    # Normalize distance, avoiding divide-by-zero.
    if dist_max == 0.0:
        return 0.0
    else:
        return dist/dist_max

def apply_metadata(items, info):
    """Set the items' metadata to match the data given in info. The
    list of items must be ordered.
    """
    for index, (item, track_data) in enumerate(zip(items,  info['tracks'])):
        item.artist = info['artist']
        item.album = info['album']
        item.tracktotal = len(items)
        
        if 'year' in info:
            item.year = info['year']
        if 'month' in info:
            item.month = info['month']
        if 'day' in info:
            item.day = info['day']
        
        item.title = track_data['title']
        item.track = index + 1
        
        #fixme Set MusicBrainz IDs

def tag_album(items):
    """Bundles together the functionality used to infer tags for a
    set of items comprised by an album. Returns everything relevant
    and a little bit more:
        - The list of items, possibly reordered.
        - The current metadata: an (artist, album) tuple.
        - The inferred metadata dictionary.
        - The distance between the current and new metadata.
    May raise an AutotagError if existing metadata is insufficient.
    """
    # Get current and candidate metadata.
    cur_artist, cur_album = current_metadata(items)
    if not cur_artist or not cur_album:
        raise InsufficientMetadataError()
    info = mb.match_album(cur_artist, cur_album, len(items))
    
    # Make sure the album has the correct number of tracks.
    if len(items) != len(info['tracks']):
        raise UnknownAlbumError()
    
    # Put items in order.
    #fixme need to try ordering tracks for every candidate album
    items = order_items(items, info['tracks'])
    if not items:
        raise UnorderedTracksError()
    
    # Get the change distance.
    dist = distance(items, info)
    
    return items, (cur_artist, cur_album), info, dist

