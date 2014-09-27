#!/usr/bin/env python2

from collections import namedtuple
import mutagen
from mutagen.id3 import ID3, TXXX
from mutagen.oggvorbis import OggVorbis
import sys


GainTuple = namedtuple("GainTuple", "track album")


def get_gains(mediafile):
    if mediafile.tags is None:
        return GainTuple(None, None)

    track_gain = None
    album_gain = None

    if isinstance(mediafile, OggVorbis):
        try:
            track_gain = float(mediafile.tags["REPLAYGAIN_TRACK_GAIN"][0].split()[0])
            album_gain = float(mediafile.tags["REPLAYGAIN_ALBUM_GAIN"][0].split()[0])
        except (KeyError, IndexError):
            pass
    elif isinstance(mediafile.tags, ID3):
        try:
            track_gain = mediafile.tags.getall("RVA2:track")[0].gain
            album_gain = mediafile.tags.getall("RVA2:album")[0].gain
        except IndexError:
            pass
    else:
        # Unhandled tag type.
        return None

    return GainTuple(track_gain, album_gain)



if len(sys.argv) < 2:
    print >> sys.stderr, "Usage:"
    print >> sys.stderr, " %s file..." % sys.argv[0]
    sys.exit(1)

for mediapath in sys.argv[1:]:
    mediafile = mutagen.File(mediapath)
    if mediafile is None:
        print "%s: Don't know how to parse this file type." % mediapath
        continue

    gains = get_gains(mediafile)
    if gains is None:
        print "%s: Don't know how to get ReplayGain information." % mediapath
        continue

    msg = ""
    if not gains.track:
        msg += " No TRACK gain."
    if not gains.album:
        msg += " No ALBUM gain."

    if len(msg):
        print "%s:%s" % (mediapath, msg)
