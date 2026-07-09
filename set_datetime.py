#!/usr/bin/env python3
"""Rewrite photo EXIF date/time from the folder structure.

The phone clock was wrong when these photos were taken, so real capture times
are unreliable. Instead we treat the **folder path** as the source of truth:

    Social_Internship/
    ├── 2026-06-24/            <- date  (YYYY-MM-DD)
    │   ├── Morning_0900/      <- time  (any label + _HHMM, 24-hour)
    │   │   ├── IMG....jpg
    │   │   └── IMG....jpg
    │   └── Evening_1630/
    └── 2026-06-25/
        └── ...

For each activity folder, photos are sorted by filename (chronological) and
stamped starting at the folder's HH:MM, with each subsequent photo ~5 minutes
after the previous (jittered 3-7 min so the schedule doesn't look mechanical).

Times are written LOSSLESSLY into EXIF (piexif.insert — no image recompression):
  DateTimeOriginal, DateTimeDigitized, DateTime, OffsetTime* (+05:30),
  and the UTC GPSDateStamp / GPSTimeStamp so metadata stays self-consistent.

The jitter is seeded from the folder path, so re-running produces identical
times (idempotent / safe to repeat).

Usage:
    python3 set_datetime.py --dry-run              # preview, write nothing
    python3 set_datetime.py                        # process ./Social_Internship
    python3 set_datetime.py path/to/root           # process a different root
"""
import argparse
import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone

import piexif

ROOT_DEFAULT = "Social_Internship"
TZ = timezone(timedelta(hours=5, minutes=30))   # IST, matches the banner label
JITTER_MIN_S = 180                               # 3 min
JITTER_MAX_S = 420                               # 7 min

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")     # 2026-06-24
TIME_RE = re.compile(r"(\d{4})$")                # trailing HHMM of activity dir


def parse_activity(date_name, activity_name):
    """Return the base datetime for an activity folder, or None if it can't
    be parsed."""
    if not DATE_RE.match(date_name):
        return None
    m = TIME_RE.search(activity_name)
    if not m:
        return None
    hhmm = m.group(1)
    hh, mm = int(hhmm[:2]), int(hhmm[2:])
    if hh > 23 or mm > 59:
        return None
    try:
        d = datetime.strptime(date_name, "%Y-%m-%d")
    except ValueError:
        return None
    return d.replace(hour=hh, minute=mm, second=0, tzinfo=TZ)


def assign_times(base, n, seed):
    """Return a list of n datetimes starting at `base`, each +3..7 min."""
    rng = random.Random(seed)
    out, cur = [], base
    for i in range(n):
        if i:
            cur = cur + timedelta(seconds=rng.randint(JITTER_MIN_S, JITTER_MAX_S))
        out.append(cur)
    return out


def _safe_dump(exif):
    """piexif.dump, but drop any tag piexif refuses to re-encode.

    Some phones store UNDEFINED-type tags (e.g. SceneType) in a form piexif can
    load but not dump. Those tags are cosmetic; we drop only the offending ones
    (location / date / make / model are untouched) and retry until it succeeds.
    """
    while True:
        try:
            return piexif.dump(exif)
        except ValueError as e:
            m = re.search(r"(\d+) in (\w+) IFD", str(e))
            if not m:
                raise
            ifd, tag = m.group(2), int(m.group(1))
            if ifd in exif and tag in exif[ifd]:
                del exif[ifd][tag]
            else:
                raise


def write_exif(path, dt):
    """Write local datetime `dt` (tz-aware, IST) into the file's EXIF, lossless."""
    try:
        exif = piexif.load(path)
    except Exception:
        exif = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "Interop": {}}

    local = dt.strftime("%Y:%m:%d %H:%M:%S").encode()
    offset = "+05:30".encode()
    exif["0th"][piexif.ImageIFD.DateTime] = local
    exif["Exif"][piexif.ExifIFD.DateTimeOriginal] = local
    exif["Exif"][piexif.ExifIFD.DateTimeDigitized] = local
    exif["Exif"][piexif.ExifIFD.OffsetTime] = offset
    exif["Exif"][piexif.ExifIFD.OffsetTimeOriginal] = offset
    exif["Exif"][piexif.ExifIFD.OffsetTimeDigitized] = offset

    # GPS timestamps are in UTC
    utc = dt.astimezone(timezone.utc)
    exif["GPS"][piexif.GPSIFD.GPSDateStamp] = utc.strftime("%Y:%m:%d").encode()
    exif["GPS"][piexif.GPSIFD.GPSTimeStamp] = (
        (utc.hour, 1), (utc.minute, 1), (utc.second, 1)
    )

    piexif.insert(_safe_dump(exif), path)


def main():
    ap = argparse.ArgumentParser(description="Rewrite EXIF date/time from folder structure.")
    ap.add_argument("root", nargs="?", default=ROOT_DEFAULT,
                    help=f"root folder to process (default: {ROOT_DEFAULT})")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the schedule without modifying any files")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        sys.exit(f"error: folder not found: {args.root}\n"
                 f"Create it as  <root>/YYYY-MM-DD/Label_HHMM/  and put photos inside.")

    activities = 0
    photos = 0
    skipped = []
    failed = []

    # Walk date folders, then activity folders inside them.
    for date_name in sorted(os.listdir(args.root)):
        date_path = os.path.join(args.root, date_name)
        if not os.path.isdir(date_path):
            continue
        for activity_name in sorted(os.listdir(date_path)):
            act_path = os.path.join(date_path, activity_name)
            if not os.path.isdir(act_path):
                continue
            base = parse_activity(date_name, activity_name)
            if base is None:
                skipped.append(os.path.join(date_name, activity_name))
                continue
            jpgs = sorted(f for f in os.listdir(act_path)
                          if f.lower().endswith((".jpg", ".jpeg")))
            if not jpgs:
                continue
            times = assign_times(base, len(jpgs), seed=os.path.join(date_name, activity_name))
            print(f"[{date_name}/{activity_name}]  base {base:%a %d/%m/%Y %I:%M %p}  ({len(jpgs)} photos)")
            for fname, dt in zip(jpgs, times):
                print(f"    {fname}  ->  {dt:%a %d/%m/%Y %I:%M %p}")
                if not args.dry_run:
                    try:
                        write_exif(os.path.join(act_path, fname), dt)
                    except Exception as e:
                        print(f"      ! failed: {e}")
                        failed.append(os.path.join(date_name, activity_name, fname))
                        continue
                photos += 1
            activities += 1

    mode = "DRY-RUN (nothing written)" if args.dry_run else "written"
    print(f"\n{mode}: {photos} photos across {activities} activities.")
    if skipped:
        print("Skipped (couldn't parse date/HHMM):")
        for s in skipped:
            print(f"  - {s}")
    if failed:
        print(f"Failed to write ({len(failed)}):")
        for s in failed:
            print(f"  - {s}")


if __name__ == "__main__":
    main()
