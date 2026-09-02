# Playback rotation — design notes

What the video counter system was meant to do. This is the spec, not a
description of what ships; see [Known gaps](../README.md#known-gaps) for where
the two diverge.

## Session-based cycle

A *session* is one pass in which every video file plays exactly once. When
everything has played, a new session starts. Sessions repeat indefinitely.

## Random, but constrained

Pick randomly, but only from the videos that haven't played yet this session.
Straight random selection means an unlucky file can go months without coming up;
drawing without replacement spreads playtime evenly while keeping the order
unpredictable.

## State survives restarts

If the player stops, it resumes where it left off. Videos already played this
session stay marked as played, and the rest stay in the pool.

## History is kept

Track total plays per file across all sessions, not just the current one. A new
session resets the "played this session" flag but not the running count, so
"this one has been on 47 times" stays true.

## New files are picked up on their own

Anything dropped into the video directories is detected and joins the current
session as unplayed. Nothing to register by hand.

## The tracking file is readable

`playback_state.txt` is plain text so anyone can open it and see what has played,
what hasn't, and how often — no database, no JSON.

---

In short: fair rotation that remembers where it was, keeps its history, and
stays legible to someone who doesn't write code.
