# Experiments

Things that were tried and parked. Not wired into the build.

**`player_WITH-CIRCULATION.py`** implements the rotation described in
[../../docs/playback-design.md](../../docs/playback-design.md): a session picks
randomly from what hasn't played yet, state is saved after every file so a power
cut doesn't lose it, and files added or removed from the directories are picked
up on the next loop. Functionally it is what the player should do.

It plays through `--hwdec=auto` and calls `mpv` under `sudo`, and on a Pi 3B that
stutters badly on anything that isn't H.264. Merging its rotation logic into
`player.py`'s per-codec decoder selection is the obvious next step; nobody has
done it.
