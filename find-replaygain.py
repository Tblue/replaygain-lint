#!/usr/bin/env python2

from argparse import ArgumentParser
from collections import namedtuple
import mutagen
from mutagen.apev2 import APEv2, APENoHeaderError
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
            "-a",
            "--ape-warning",
            help="Print a warning if a file has ReplayGain information in obsolete APEv2 tags.",
            action="store_true"
        )
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


def has_ape_gains(filename):
    try:
        ape_tags = APEv2()
        ape_tags.load(filename)
    except APENoHeaderError:
        return False

    return \
        "REPLAYGAIN_TRACK_GAIN" in ape_tags or \
        "REPLAYGAIN_ALBUM_GAIN" in ape_tags



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
    if gains.track is None:
        msg += " No TRACK gain."
    if gains.album is None:
        msg += " No ALBUM gain."

    ape_gains_found = args.ape_warning and has_ape_gains(mediapath)
    if ape_gains_found:
        msg += " Has obsolete APEv2 ReplayGain tag(s)."

    # Do we have something to display?
    if not len(msg):
        continue

    # If the user only wants to get a list of files which have no ReplayGain tags at all,
    # then also check if all ReplayGain gain tags are missing and only say something if
    # that is the case.
    if ape_gains_found or not args.empty_only or gains.track is None and gains.album is None:
        print "%s:%s" % (mediapath, msg)
