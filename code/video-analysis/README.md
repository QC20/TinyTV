# Video analysis

Scripts for looking at a video library, not for playing it.

**`analyze.py`** walks `tv/`, `films/` and `commercials/` in the current
directory and reports file counts, total runtime and size per category, plus how
long the whole library would take to watch. Durations come from `ffprobe`, then
`mediainfo`, and if neither is available it estimates from file size and a
per-category bitrate guess — the output says which source it used, so you know
when the numbers are soft.

**`list_files.py`** writes every `.mp4` under the script's directory to
`list_files.txt`, grouped by folder.

**`encode.py`** is an older, much simpler batch encoder: scale everything to 800
tall, H.264 baseline, CRF 23. Superseded by
[../encoding](../encoding), which handles cropping, rotation and subtitles.

Run `analyze.py` and `list_files.py` from inside the video library.
