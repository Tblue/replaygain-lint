#!/usr/bin/env python2

from argparse import ArgumentParser
from collections import namedtuple
import mutagen
from mutagen.apev2 import APEv2, APENoHeaderError
from mutagen.id3 import ID3, TXXX
from mutagen.mp4 import MP4Tags
from mutagen.oggvorbis import OggVorbis
import sys


GainTuple = namedtuple("GainTuple", "track album has_undo")


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
    arg_parser.add_argument(
            "-u",
            "--missing-undo",
            help="Print a warning if a MP3 file has no MP3Gain undo tags, i. e. if "
                "it has NOT been modified directly for compatibility with old players "
                "which are not aware of ReplayGain tags.",
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
    def try_shift(xs, callback):
        if len(xs):
            return callback(xs[0])

        return None


    if mediafile.tags is None:
        return GainTuple(None, None, False)

    track_gain = None
    album_gain = None
    has_undo   = False

    if isinstance(mediafile, OggVorbis):
        track_gain = try_shift(
                mediafile.tags["REPLAYGAIN_TRACK_GAIN"],
                lambda val: float(val.split(maxsplit=1)[0])
            )
        album_gain = try_shift(
                mediafile.tags["REPLAYGAIN_ALBUM_GAIN"],
                lambda val: float(val.split(maxsplit=1)[0])
            )
    elif isinstance(mediafile.tags, ID3):
        has_undo   = len(mediafile.tags.getall("TXXX:MP3GAIN_UNDO")) > 0
        track_gain = try_shift(
                mediafile.tags.getall("RVA2:track"),
                lambda val: val.gain
            )
        album_gain = try_shift(
                mediafile.tags.getall("RVA2:album"),
                lambda val: val.gain
            )
    elif isinstance(mediafile.tags, MP4Tags):
        track_gain = try_shift(
                mediafile.tags["----:com.apple.iTunes:replaygain_track_gain"],
                lambda val: float(val)
            )
        album_gain = try_shift(
                mediafile.tags["----:com.apple.iTunes:replaygain_album_gain"],
                lambda val: float(val)
            )
    else:
        # Unhandled tag type.
        return None

    return GainTuple(track_gain, album_gain, has_undo)


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

    missing_undo = args.missing_undo and not gains.has_undo
    if missing_undo:
        msg += " NO UNDO INFORMATION FOUND (frames probably not modified by MP3Gain)."

    ape_gains_found = args.ape_warning and has_ape_gains(mediapath)
    if ape_gains_found:
        msg += " Has obsolete APEv2 ReplayGain tag(s)."

    # Do we have something to display?
    if not len(msg):
        continue

    # If the user only wants to get a list of files which have no ReplayGain tags at all,
    # then also check if all ReplayGain gain tags are missing and only say something if
    # that is the case.
    if ape_gains_found or missing_undo or \
            not args.empty_only or gains.track is None and gains.album is None:
        print "%s:%s" % (mediapath, msg)
