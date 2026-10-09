#!/usr/bin/env python3
"""cue2cd: convert a classic .cue sheet into a CueDown (.cd) file.

Usage:
	cue2cd.py mix.cue                # writes mix.cd next to the input
	cue2cd.py mix.cue -o out.cd      # explicit output path
	cue2cd.py mix.cue -o -           # write to stdout
	cue2cd.py mix.cue --ms           # keep sub-second precision (frames -> .mmm)

Every cue is written as a canonical CueDown line:

	TIMECODE - TRACK STRING
"""

import argparse
import re
import sys
from pathlib import Path

FRAMES_PER_SECOND = 75

FILE_RE = re.compile(r"^FILE\s+", re.IGNORECASE)
TRACK_RE = re.compile(r"^TRACK\s+(\d+)", re.IGNORECASE)
FIELD_RE = re.compile(r"^(TITLE|PERFORMER)\s+(.*)$", re.IGNORECASE)
INDEX_RE = re.compile(r"^INDEX\s+(\d+)\s+(\d+):(\d{1,2}):(\d{1,2})$", re.IGNORECASE)


class CueError(Exception):
	pass


def read_text(path):
	"""Old cue sheets are rarely UTF-8, so fall back to Windows-1252."""
	raw = path.read_bytes()
	for encoding in ("utf-8-sig", "cp1252"):
		try:
			return raw.decode(encoding)
		except UnicodeDecodeError:
			continue
	return raw.decode("latin-1")


def unquote(value):
	value = value.strip()
	if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
		value = value[1:-1]
	# A track string is always a single line with single spaces.
	return " ".join(value.split())


def parse_cue(text):
	"""Return (album, tracks). Album and each track are plain dicts."""
	album = {"title": "", "performer": ""}
	tracks = []
	current = None
	files_seen = 0

	for line_number, raw_line in enumerate(text.splitlines(), start=1):
		line = raw_line.strip()
		if not line:
			continue

		if FILE_RE.match(line):
			files_seen += 1
			if files_seen > 1 and tracks:
				raise CueError(
					f"line {line_number}: multiple FILE entries; timecodes restart "
					"per file, so this sheet can't become one .cd"
				)
			continue

		match = TRACK_RE.match(line)
		if match:
			current = {
				"number": int(match.group(1)),
				"title": "",
				"performer": "",
				"indexes": {},
			}
			tracks.append(current)
			continue

		match = FIELD_RE.match(line)
		if match:
			target = current if current is not None else album
			target[match.group(1).lower()] = unquote(match.group(2))
			continue

		match = INDEX_RE.match(line)
		if match:
			if current is None:
				raise CueError(f"line {line_number}: INDEX before any TRACK")
			index, minutes, seconds, frames = (int(g) for g in match.groups())
			if seconds > 59 or frames >= FRAMES_PER_SECOND:
				raise CueError(f"line {line_number}: malformed timecode in '{line}'")
			total_ms = (minutes * 60 + seconds) * 1000 + frames * 1000 // FRAMES_PER_SECOND
			current["indexes"][index] = total_ms
			continue

		# REM, FLAGS, ISRC, PREGAP, CATALOG, ... have no CueDown equivalent.

	return album, tracks


def track_start_ms(track):
	"""INDEX 01 is where the track starts; INDEX 00 is only the pregap."""
	indexes = track["indexes"]
	if 1 in indexes:
		return indexes[1]
	if indexes:
		return indexes[min(indexes)]
	raise CueError(f"track {track['number']:02d}: no INDEX")


def track_string(track, album):
	title = track["title"]
	performer = track["performer"]
	# In DJ-mix sheets the track PERFORMER is usually just the DJ again;
	# only use it when it actually says something the title doesn't.
	if performer and performer != album["performer"]:
		text = f"{performer} \u2013 {title}" if title else performer
	else:
		text = title
	if not text:
		raise CueError(f"track {track['number']:02d}: empty track string")
	return text


def format_timecode(total_ms, keep_ms):
	total_seconds, ms = divmod(total_ms, 1000)
	minutes, seconds = divmod(total_seconds, 60)
	hours, minutes = divmod(minutes, 60)
	if hours:
		timecode = f"{hours}:{minutes:02d}:{seconds:02d}"
	else:
		timecode = f"{minutes}:{seconds:02d}"
	if keep_ms:
		timecode += f".{ms:03d}"
	return timecode


def convert(text, keep_ms=False):
	album, tracks = parse_cue(text)
	if not tracks:
		raise CueError("no TRACK entries found")

	lines = []
	previous = None
	for track in tracks:
		start_ms = track_start_ms(track)
		# Compare at the precision actually written: CueDown timecodes
		# must be strictly ascending.
		written = start_ms if keep_ms else start_ms // 1000
		if previous is not None and written <= previous:
			hint = "" if keep_ms else " (try --ms)"
			raise CueError(
				f"track {track['number']:02d}: timecode is not strictly "
				f"ascending{hint}"
			)
		previous = written
		lines.append(f"{format_timecode(start_ms, keep_ms)} - {track_string(track, album)}")

	return "\n".join(lines) + "\n"


def main(argv=None):
	parser = argparse.ArgumentParser(description="Convert a .cue sheet to CueDown (.cd).")
	parser.add_argument("cue", type=Path, help="input .cue file")
	parser.add_argument("-o", "--output", help="output path ('-' for stdout); default: input name with .cd")
	parser.add_argument("--ms", action="store_true", help="keep sub-second precision as .mmm")
	args = parser.parse_args(argv)

	try:
		output = convert(read_text(args.cue), keep_ms=args.ms)
	except (CueError, OSError) as error:
		print(f"cue2cd: {error}", file=sys.stderr)
		return 1

	if args.output == "-":
		sys.stdout.write(output)
	else:
		destination = Path(args.output) if args.output else args.cue.with_suffix(".cd")
		destination.write_text(output, encoding="utf-8")
	return 0


if __name__ == "__main__":
	sys.exit(main())
