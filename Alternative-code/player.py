# This script plays videos alternating between TV shows and commercials.
# It uses VLC media player to play the videos in fullscreen mode.
# Randomly selects one commercial, then one TV show, then one commercial, etc.
import os
import time
import sys
import random
from subprocess import Popen

# player.py
base_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'videos')
tv_directory = os.path.join(base_directory, 'tv')
commercials_directory = os.path.join(base_directory, 'commercials')

# Store video lists
tv_videos = []
commercial_videos = []

# Get all videos from a specific directory
def getVideosFromDirectory(directory):
    videos = []
    try:
        if not os.path.exists(directory):
            print(f"Warning: Directory {directory} not found")
            return videos
            
        for file in os.listdir(directory):
            if file.lower().endswith('.mp4'):
                videos.append(os.path.join(directory, file))
        
        # Sort for consistent behavior (though we'll randomize selection)
        videos.sort()
        
    except Exception as e:
        print(f"Error reading directory {directory}: {e}")
    
    return videos

# Load videos from both directories
def loadAllVideos():
    global tv_videos, commercial_videos
    
    tv_videos = getVideosFromDirectory(tv_directory)
    commercial_videos = getVideosFromDirectory(commercials_directory)
    
    print(f"Found {len(tv_videos)} TV show(s)")
    print(f"Found {len(commercial_videos)} commercial(s)")
    
    if len(tv_videos) == 0:
        print(f"Error: No TV shows found in {tv_directory}")
        return False
    
    if len(commercial_videos) == 0:
        print(f"Error: No commercials found in {commercials_directory}")
        return False
    
    return True

# Play a single video
def playVideo(video_path):
    try:
        print(f"Playing: {os.path.basename(video_path)}")
        playProcess = Popen(['cvlc', '--fullscreen', '--no-osd', '--play-and-exit', video_path])
        playProcess.wait()
        return True
    except Exception as e:
        print(f"Error playing {os.path.basename(video_path)}: {e}")
        return False

# Main playback loop - alternates between commercials and TV shows
def playAlternatingVideos():
    global tv_videos, commercial_videos
    
    # Refresh video lists in case files were added/removed
    if not loadAllVideos():
        return False
    
    # Always start with a commercial
    while True:
        # Play a random commercial
        if commercial_videos:
            commercial = random.choice(commercial_videos)
            print("--- COMMERCIAL ---")
            if not playVideo(commercial):
                time.sleep(1)  # Brief pause if there was an error
        
        # Play a random TV show
        if tv_videos:
            tv_show = random.choice(tv_videos)
            print("--- TV SHOW ---")
            if not playVideo(tv_show):
                time.sleep(1)  # Brief pause if there was an error
        
        # Small delay between cycles to prevent overwhelming the system
        time.sleep(0.5)

# Create directories if they don't exist
def createDirectories():
    directories = [base_directory, tv_directory, commercials_directory]
    
    for directory in directories:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                print(f"Created directory: {directory}")
            except Exception as e:
                print(f"Error creating directory {directory}: {e}")
                return False
    
    return True

# Main execution
def main():
    print("TinyTV Player - Alternating TV Shows and Commercials")
    print("=" * 50)
    
    # Create directories if needed
    if not createDirectories():
        print("Failed to create required directories")
        sys.exit(1)
    
    # Initial video load
    if not loadAllVideos():
        print("\nPlease add video files to:")
        print(f"  TV Shows: {tv_directory}")
        print(f"  Commercials: {commercials_directory}")
        print("\nThen restart the script.")
        sys.exit(1)
    
    print(f"\nDirectories:")
    print(f"  TV Shows: {tv_directory}")
    print(f"  Commercials: {commercials_directory}")
    print("\nPress Ctrl+C to stop playback")
    print("-" * 50)
    
    try:
        playAlternatingVideos()
    except KeyboardInterrupt:
        print("\nStopping video playback (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

# Load videos on startup
if not createDirectories():
    print("Failed to create directories")
    sys.exit(1)

if __name__ == "__main__":
    main()
else:
    # If imported, still run the main logic
    try:
        while True:
            playAlternatingVideos()
    except KeyboardInterrupt:
        print("Stopping video playback (Ctrl+C)")
        sys.exit(0)