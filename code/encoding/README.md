# Encoding videos for the screen

The Pi is not fast enough to scale and decode arbitrary video in real time, so
everything gets converted once on a desktop machine and copied over ready to
play. These are the ffmpeg wrappers that do it.

`480x800-screen.py` is the one to use. The others are kept in `deprecated/`
because earlier builds used different panels.

## What it does

Per file, in this order:

1. **Crops black bars.** Samples the frame at 10%, 50% and 90% through the video
   and crops letterboxing when it exceeds 2% of the frame. Sampling at three
   points avoids being fooled by a dark opening shot.
2. **Picks target dimensions.** Height is fixed at 480. Width is allowed to land
   anywhere between 770 and 800, preferring 780 — the case covers a few pixels
   at the edges, so filling the panel exactly wastes them. It searches for the
   width that needs the least stretching, staying inside a 12% stretch / 20%
   squeeze limit.
3. **Burns in subtitles** if a `.srt` with the same base name sits next to the
   source. 18px Arial with a 2px outline, which is about the smallest that stays
   readable on a 4″ panel.
4. **Rotates 90°** if `ROTATE` is on, subtitles along with it.
5. **Encodes** to H.264 Main / Level 3.0, CRF 23, `veryslow`, AAC audio at
   256 kbps, `yuv420p`, faststart.

Existing outputs are skipped, and sources are never modified.

## Requirements

ffmpeg on PATH, and Python 3.

```bash
sudo apt install ffmpeg    # Debian/Raspberry Pi OS
brew install ffmpeg        # macOS
```

## Use

Put your videos in an `input/` folder beside the script; `output/` is created
for you.

```text
code/encoding/
├── 480x800-screen.py
├── input/     <- source videos (and matching .srt files, if any)
└── output/    <- converted files land here
```

```bash
python3 480x800-screen.py
```

Progress looks like this:

```text
(1/10)
Analyzing 'sample_video'...
  Original dimensions: 1920x1080
  Duration: 00:05:23
  Found subtitle file: sample_video.srt
  Detecting black bars (sampling 10s)...
  Black bars detected! Original: 1920x1080, After crop: 1920x800
  Optimal target dimensions: 780x480
  Applying rotation: counterclockwise
Encoding 'sample_video' with filters: crop=1920:800:0:140,scale=780:480,...
  Progress: [====================] 100.00% (00:05:23 / 00:05:23)
 -> Done in 142.3s, size=8472 KB
```

Roughly 6–8 minutes per 30-minute episode on a modern laptop, scaling with how
many threads you give it.

## Settings

All near the top of the script:

```python
TARGET_HEIGHT = 480
TARGET_WIDTH_PREFERRED = 780
TARGET_WIDTH_MIN = 770
TARGET_WIDTH_MAX = 800

ROTATE = True
ROTATE_DIR = 'counterclockwise'

MAX_STRETCH = 1.12          # how much distortion to tolerate
MIN_SQUEEZE = 0.80

SUBTITLE_FONT_SIZE = 18
SUBTITLE_FONT_NAME = 'Arial'
SUBTITLE_OUTLINE = 2

MAX_CPU_THREADS = multiprocessing.cpu_count() // 2
```

Worth knowing:

- **Video looks stretched** — tighten `MAX_STRETCH` and `MIN_SQUEEZE` towards 1.0.
- **Too slow** — raise `MAX_CPU_THREADS`, or change the preset from `veryslow`
  to `medium`. `veryslow` buys maybe 5% file size for several times the wait.
- **Rotated the wrong way** — flip `ROTATE_DIR`.
- **Quality** — CRF 18 is close to lossless and much larger, 23 is the default,
  26 is noticeably softer but small. On a 4″ screen 26 is more defensible than
  it sounds.

## The deprecated scripts

| Script | Target |
| --- | --- |
| `TinyTV_Converter.py` | Same as `480x800-screen.py`, but reads from `~/Desktop/c_input` instead of a folder beside the script |
| `video-converter_800x480.py` | Aspect-preserving 480p for a normal monitor |
| `video-converter_480x320.py` | Fixed 480×320 with letterboxing, for 2.8″–3.5″ panels |
| `800x480_Resolution.py` | Earlier pass at the 800×480 conversion |
