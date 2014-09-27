#!/usr/bin/env python2

from argparse import ArgumentParser
from collections import namedtuple
import mutagen
from mutagen.id3 import ID3, TXXX
from mutagen.mp4 import MP4Tags
from mutagen.oggvorbis import OggVorbis
import sys


GainTuple = namedtuple("GainTuple", "track album")


def setup_arg_parser():
    arg_parser = ArgumentParser(
            description="Find files with missing ReplayGain tags."
        )

    # Options
    arg_parser.add_argument(
            "-e",
            "--empty-only",
            help="Only print those files which have no ReplayGain tags at all.",
            action="store_true"
        )

    # Arguments
    arg_parser.add_argument(
            "file",
            help="File to process.",
            nargs="+",
        )

    return arg_parser


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
    elif isinstance(mediafile.tags, MP4Tags):
        try:
            track_gain = float(mediafile.tags["----:com.apple.iTunes:replaygain_track_gain"][0])
            album_gain = float(mediafile.tags["----:com.apple.iTunes:replaygain_album_gain"][0])
        except (KeyError, IndexError):
            pass
    else:
        # Unhandled tag type.
        return None

    return GainTuple(track_gain, album_gain)



args = setup_arg_parser().parse_args()
for mediapath in args.file:
    mediafile = mutagen.File(mediapath)
    if mediafile is None:
        print >> sys.stderr, "%s: Don't know how to parse this file type." % mediapath
        continue

    gains = get_gains(mediafile)
    if gains is None:
        print >> sys.stderr, "========= WARNING ==========="
        print >> sys.stderr, "%s: Don't know how to get ReplayGain information." % mediapath
        print >> sys.stderr, "CLASS NAME: %s" % mediafile.__class__.__name__
        print >> sys.stderr, "TAG DUMP:"
        print >> sys.stderr, mediafile.tags.pprint()
        print >> sys.stderr, "============================="

        continue

    msg = ""
    if not gains.track:
        msg += " No TRACK gain."
    if not gains.album:
        msg += " No ALBUM gain."

    if len(msg) and (not args.empty_only or not gains.track and not gains.album):
        print "%s:%s" % (mediapath, msg)
