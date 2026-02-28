#!/usr/bin/env python3

import os
import sys
import random
import subprocess
from subprocess import Popen
from datetime import datetime

base_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'videos')
tv_directory = os.path.join(base_directory, 'tv')
commercials_directory = os.path.join(base_directory, 'commercials')
state_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'playback_state.txt')

playback_state = {
    'session': 1,
    'tv': {},
    'commercials': {}
}

def loadPlaybackState():
    global playback_state
    if not os.path.exists(state_file):
        return
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        current_category = None
        for line in lines:
            line = line.strip()
            if line.startswith('Current Session:'):
                playback_state['session'] = int(line.split(':')[1].strip())
            elif line == '--- TV SHOWS ---':
                current_category = 'tv'
            elif line == '--- COMMERCIALS ---':
                current_category = 'commercials'
            elif current_category and line.startswith('['):
                parts = line.split(' - ')
                if len(parts) >= 2:
                    played_this_session = '^|^s' in parts[0]
                    filename = parts[0].split(']')[-1].strip()
                    total_plays = int(parts[1].split(':')[1].strip()) if len(parts) > 1 else 0
                    last_played = parts[2].split(': ', 1)[1].strip() if len(parts) > 2 else 'never'
                    playback_state[current_category][filename] = {
                        'played_this_session': played_this_session,
                        'total_plays': total_plays,
                        'last_played': last_played
                    }
        print(f"Loaded playback state from session {playback_state['session']}")
    except Exception as e:
        print(f"Error loading playback state: {e}")

def savePlaybackState():
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            f.write("=== TinyTV Playback Tracker ===\n")
            f.write(f"Current Session: {playback_state['session']}\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("--- TV SHOWS ---\n")
            for filename, data in sorted(playback_state['tv'].items()):
                flag = "^|^s" if data.get('played_this_session') else " "
                f.write(f"[ {flag} ] {filename} - Total plays: {data.get('total_plays', 0)} - Last: {data.get('last_played', 'never')}\n")
            f.write("\n--- COMMERCIALS ---\n")
            for filename, data in sorted(playback_state['commercials'].items()):
                flag = "^|^s" if data.get('played_this_session') else " "
                f.write(f"[ {flag} ] {filename} - Total plays: {data.get('total_plays', 0)} - Last: {data.get('last_played', 'never')}\n")
    except Exception as e:
        print(f"Error saving playback state: {e}")

def get_video_codec(filepath):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
             '-show_entries', 'stream=codec_name',
             '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip().lower()
    except Exception:
        return 'unknown'

def play_video(filepath):
    print(f"Playing: {filepath}")
    codec = get_video_codec(filepath)
    print(f"  Codec: {codec}")

    base_args = ['mpv', '--vo=drm', '--drm-connector=HDMI-A-1', '--no-osd-bar', '--really-quiet']

    if codec in ('hevc', 'h265', 'vp9', 'av1'):
        extra = ['--hwdec=no', '--vd-lavc-threads=4', '--cache=yes', '--demuxer-max-bytes=20M', '--video-sync=audio']
    elif codec in ('h264', 'avc'):
        extra = ['--hwdec=auto', '--cache=yes', '--demuxer-max-bytes=20M', '--video-sync=audio']
    else:
        extra = ['--hwdec=auto', '--cache=yes', '--demuxer-max-bytes=20M', '--video-sync=audio']

    process = Popen(base_args + extra + [filepath])
    process.wait()

def get_video_files(folder):
    return [f for f in os.listdir(folder) if f.lower().endswith((".mp4", ".mkv", ".avi", ".mov"))]

def mark_played(category, filename):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    entry = playback_state[category].get(filename, {
        'played_this_session': False,
        'total_plays': 0,
        'last_played': 'never'
    })
    entry['played_this_session'] = True
    entry['total_plays'] += 1
    entry['last_played'] = now
    playback_state[category][filename] = entry

def playAlternatingVideos():
    tv_files = get_video_files(tv_directory)
    comm_files = get_video_files(commercials_directory)
    random.shuffle(tv_files)
    random.shuffle(comm_files)
    comm_index = 0
    for tv in tv_files:
        tv_path = os.path.join(tv_directory, tv)
        play_video(tv_path)
        mark_played('tv', tv)
        if comm_files:
            comm = comm_files[comm_index % len(comm_files)]
            comm_index += 1
            comm_path = os.path.join(commercials_directory, comm)
            play_video(comm_path)
            mark_played('commercials', comm)

def createDirectories():
    try:
        os.makedirs(tv_directory, exist_ok=True)
        os.makedirs(commercials_directory, exist_ok=True)
        return True
    except Exception as e:
        print(f"Directory creation failed: {e}")
        return False

def main():
    loadPlaybackState()
    tv_unplayed = sum(1 for d in playback_state['tv'].values() if not d.get('played_this_session', False))
    comm_unplayed = sum(1 for d in playback_state['commercials'].values() if not d.get('played_this_session', False))
    print(f"Remaining: {tv_unplayed} TV, {comm_unplayed} commercials")
    print("Press Ctrl+C to stop")
    try:
        playAlternatingVideos()
    except KeyboardInterrupt:
        print("Stopping TinyTV")
        savePlaybackState()
        sys.exit(0)

if __name__ == "__main__":
    if not createDirectories():
        sys.exit(1)
    main()
