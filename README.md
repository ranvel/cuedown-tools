# cuedown-tools

Small utilities for working with [CueDown](https://cuedown.org) (`.cd`) files.

These tools are conveniences, not part of the format. The CueDown spec and its fixture corpus are the authority; if a tool here disagrees with them, the tool is wrong. Please file tool bugs in this repo, not the spec repo.

## Tools

| Tool | What it does |
| --- | --- |
| [`cue2cd.py`](#cue2cdpy) | Converts a classic `.cue` sheet into a `.cd` file |

## cue2cd.py

Turns a cue sheet into a CueDown file, one canonical line per track.

Requires Python 3. Standard library only, nothing to install.

```
python3 cue2cd.py mix.cue              # writes mix.cd next to the input
python3 cue2cd.py mix.cue -o out.cd    # explicit output path
python3 cue2cd.py mix.cue -o -         # write to stdout
python3 cue2cd.py mix.cue --ms         # keep sub-second precision
```

### Example

Input:

```
PERFORMER "DJ Dawn"
TITLE "October 2001"
FILE "DJ Dawn - October 2001.mp3" MP3
  TRACK 01 AUDIO
    TITLE "Dumonde vs. Lange / Memory (Megara vs. DJ Lee Dub Mix)"
    PERFORMER "DJ Dawn"
    INDEX 01 00:00:00
  TRACK 02 AUDIO
    TITLE "Kai Tracid / Live Is Too Short (Energy Mix)"
    PERFORMER "DJ Dawn"
    INDEX 01 04:20:43
```

Output:

```
0:00 - Dumonde vs. Lange / Memory (Megara vs. DJ Lee Dub Mix)
4:20 - Kai Tracid / Live Is Too Short (Energy Mix)
```

### What it does with your cue sheet

These are this tool's conversion choices, not CueDown rules.

- **Timecodes.** Cue sheets count 75 frames per second. By default the frames are dropped and the timecode is floored to the whole second (`04:20:43` becomes `4:20`). With `--ms` the frames are converted to milliseconds instead (`4:20.573`).
- **Long mixes.** Cue minutes run past 59; the output rolls them into hours (`61:53:33` becomes `1:01:53`).
- **Track start.** `INDEX 01` is used as the track start. `INDEX 00` (the pregap) is ignored.
- **Track text.** The track `TITLE` is written as-is. The track `PERFORMER` is prepended (`Performer – Title`) only when it differs from the sheet-level `PERFORMER`, since DJ-mix sheets usually just repeat the DJ's name on every track.
- **What gets dropped.** The sheet-level `PERFORMER`, `TITLE` and `FILE`, plus `REM`, `FLAGS`, `ISRC`, `PREGAP` and `CATALOG`. CueDown has nowhere to put them.
- **Encoding.** Input is read as UTF-8, falling back to Windows-1252 for older sheets. Output is always UTF-8.

### When it refuses

The tool stops with an error rather than write a broken file when:

- a track has no title and no usable performer (an empty track string);
- two tracks would get the same or a descending timecode. This can happen when frames are dropped and two tracks start within the same second; `--ms` usually fixes it;
- the sheet has more than one `FILE`. Timecodes restart per file, so the sheet can't become a single `.cd`;
- a timecode is malformed, or an `INDEX` appears before any `TRACK`.

## License

TODO