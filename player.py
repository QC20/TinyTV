# This script plays videos from a specified directory in a loop.
# It uses VLC media player to play the videos in fullscreen mode.
# Resumes from the next video after the last played, even after power loss.
import os
import time
import sys
from subprocess import Popen

# player.py
directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'videos')
last_video_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'last_video.txt')

# Ensure the videos directory exists
videos = []

# Get all videos in the videos directory
def getVideos():
    global videos
    videos = []
    try:
        for file in sorted(os.listdir(directory)):  # Sort for consistent order
            if file.lower().endswith('.mp4'):
                videos.append(os.path.join(directory, file))
    except FileNotFoundError:
        print(f"Error: Videos directory {directory} not found")
        sys.exit(1)

# Save the current video to a file for resuming after power loss
def save_last_video(video):
    try:
        with open(last_video_file, 'w') as f:
            f.write(os.path.basename(video))
            f.flush()  # Ensure data is written to disk
            os.fsync(f.fileno())  # Force write to disk
    except Exception as e:
        print(f"Error saving last video: {e}")


# Load the last played video and return its index in the videos list
def load_last_video():
    try:
        with open(last_video_file, 'r') as f:
            last_video = f.read().strip()
            # Find the index of the last video in the current videos list
            for i, video in enumerate(videos):
                if os.path.basename(video) == last_video:
                    return i
    except FileNotFoundError:
        pass  # No file exists yet, start from first video
    except Exception as e:
        print(f"Error loading last video: {e}")
    return -1  # Return -1 if not found or error

# Play videos in order, starting from the next video after the last played
def playVideos():
    global videos
    if len(videos) == 0:
        getVideos()
        if len(videos) == 0:
            print("No videos found in directory")
            time.sleep(5)
            return
    # Get starting index (next video after last played)
    last_video_index = load_last_video()
    start_index = 0 if last_video_index == -1 else (last_video_index + 1) % len(videos)
    for i in range(start_index, len(videos)):
        video = videos[i]
        save_last_video(video)  # Save the video before playing
        playProcess = Popen(['cvlc', '--fullscreen', '--no-osd', '--play-and-exit', video])
        playProcess.wait()
    # After reaching the end, start from the beginning
    for i in range(len(videos)):
        video = videos[i]
        save_last_video(video)  # Save the video before playing
        playProcess = Popen(['cvlc', '--fullscreen', '--no-osd', '--play-and-exit', video])
        playProcess.wait()


# Load and prepare videos
getVideos()
if len(videos) == 0:
    print("No videos found in directory")
    sys.exit(1)

try:
    while True:
        playVideos()
except KeyboardInterrupt:
    print("Stopping video playback (Ctrl+C)")
    sys.exit(0)
