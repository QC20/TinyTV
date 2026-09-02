# Player

What runs on the Pi.

**`player.py`** shuffles `videos/tv` and `videos/commercials` (both relative to
this file) and alternates between them: an episode, then a commercial, then the
next episode. Playback goes through `mpv --vo=drm` straight to HDMI, so no
desktop is needed.

Decoder flags are chosen per file after probing the codec with `ffprobe`. H.264
uses the Pi's hardware decoder; H.265, VP9 and AV1 fall back to four software
threads with the loop filter disabled, which is the difference between watchable
and a slideshow on a 3B. Encode to H.264 and none of this matters.

Play counts go to `playback_state.txt` next to the script, written on Ctrl+C.

```bash
mkdir -p videos/tv videos/commercials
# copy encoded files in, then
python3 player.py
```

**`buttons.py`** polls a toggle switch on GPIO 26 every 300 ms. On, it drives
GPIO 18 high for the backlight and puts GPIO 19 into ALT5 — its PWM audio
function — via `raspi-gpio`. Off, it reverses both, so screen and sound come up
and go down together.

If yours works backwards, invert the read; there's a comment in the loop marking
the line.

Needs `mpv`, `ffmpeg` and `RPi.GPIO`.
