# This script plays videos from a specified directory in a loop.
# It uses VLC media player to play the videos in fullscreen mode.
import os
import random
import time
from subprocess import Popen

# player.py
directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'videos')


# Ensure the videos directory exists
videos = []

# Get all videos in the videos directory
def getVideos():
    global videos
    videos = []
    for file in os.listdir(directory):
        if file.lower().endswith('.mp4'):
            videos.append(os.path.join(directory, file))

# If the videos directory is empty, create a placeholder video
def playVideos():
    global videos
    if len(videos) == 0:
        getVideos()
        time.sleep(5)
        return
    random.shuffle(videos)
    for video in videos:
        # Uncomment for full screen
        #playProcess = Popen(['cvlc', '--play-and-exit', '--fullscreen', video])
        playProcess = Popen(['cvlc', '--fullscreen', '--no-osd', '--loop', '--play-and-exit', video])
        playProcess.wait()

# runs endlessly, playing videos in a loop
while (True):
    playVideos()