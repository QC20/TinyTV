import os
import time
import sys
import random
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
    """Load playback state from human-readable file"""
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
                # Parse line like: [✓] episode1.mp4 - Total plays: 5 - Last: 2024-12-21 14:30
                parts = line.split(' - ')
                if len(parts) >= 2:
                    played_this_session = line[1] == '✓'
                    filename = parts[0][4:].strip()  # Remove [✓] or [ ]
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
    """Save playback state to human-readable file"""
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            f.write("=== TinyTV Playback Tracker ===\n")
            f.write(f"Current Session: {playback_state['session']}\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d')}\n\n")
            
            f.write("--- TV SHOWS ---\n")
            for filename, data in sorted(playback_state['tv'].items()):
                check = '✓' if data['played_this_session'] else ' '
                f.write(f"[{check}] {filename} - Total plays: {data['total_plays']} - Last: {data['last_played']}\n")
            
            f.write("\n--- COMMERCIALS ---\n")
            for filename, data in sorted(playback_state['commercials'].items()):
                check = '✓' if data['played_this_session'] else ' '
                f.write(f"[{check}] {filename} - Total plays: {data['total_plays']} - Last: {data['last_played']}\n")
        
        print(f"Saved playback state (Session {playback_state['session']})")
    except Exception as e:
        print(f"Error saving playback state: {e}")

def getVideosFromDirectory(directory):
    """Get all MP4 files from directory"""
    videos = []
    try:
        if not os.path.exists(directory):
            print(f"Warning: Directory {directory} not found")
            return videos
        for file in os.listdir(directory):
            if file.lower().endswith('.mp4'):
                videos.append(file)
        videos.sort()
    except Exception as e:
        print(f"Error reading directory {directory}: {e}")
    return videos

def updatePlaybackState():
    """Update state with current videos, add new ones, start new session if needed"""
    tv_videos = getVideosFromDirectory(tv_directory)
    commercial_videos = getVideosFromDirectory(commercials_directory)
    
    # Check if we need to start a new session (all videos played)
    tv_all_played = all(playback_state['tv'].get(v, {}).get('played_this_session', False) for v in tv_videos) if tv_videos else False
    comm_all_played = all(playback_state['commercials'].get(v, {}).get('played_this_session', False) for v in commercial_videos) if commercial_videos else False
    
    if tv_all_played and comm_all_played and (tv_videos or commercial_videos):
        print(f"\n🎉 Session {playback_state['session']} complete! All videos played.")
        print("Starting new session...\n")
        playback_state['session'] += 1
        # Reset 'played_this_session' for all videos
        for category in ['tv', 'commercials']:
            for filename in playback_state[category]:
                playback_state[category][filename]['played_this_session'] = False
    
    # Add new TV videos
    for filename in tv_videos:
        if filename not in playback_state['tv']:
            print(f"New TV show found: {filename}")
            playback_state['tv'][filename] = {
                'played_this_session': False,
                'total_plays': 0,
                'last_played': 'never'
            }
    
    # Add new commercials
    for filename in commercial_videos:
        if filename not in playback_state['commercials']:
            print(f"New commercial found: {filename}")
            playback_state['commercials'][filename] = {
                'played_this_session': False,
                'total_plays': 0,
                'last_played': 'never'
            }
    
    # Remove videos that no longer exist
    for category, directory in [('tv', tv_directory), ('commercials', commercials_directory)]:
        current_videos = getVideosFromDirectory(directory)
        to_remove = [f for f in playback_state[category] if f not in current_videos]
        for filename in to_remove:
            print(f"Removed deleted file: {filename}")
            del playback_state[category][filename]
    
    return tv_videos, commercial_videos

def getUnplayedVideo(category):
    """Get a random unplayed video from category, or None if all played"""
    unplayed = [
        filename for filename, data in playback_state[category].items()
        if not data['played_this_session']
    ]
    
    if not unplayed:
        return None
    
    return random.choice(unplayed)

def markVideoPlayed(category, filename):
    """Mark video as played and update statistics"""
    if filename in playback_state[category]:
        playback_state[category][filename]['played_this_session'] = True
        playback_state[category][filename]['total_plays'] += 1
        playback_state[category][filename]['last_played'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        savePlaybackState()

def playVideo(video_path):
    """Play video using mpv"""
    try:
        print(f"Playing: {os.path.basename(video_path)}")
        playProcess = Popen([
            'sudo', 'mpv',
            '--vo=drm',
            '--drm-connector=HDMI-A-1',
            '--hwdec=auto',
            '--really-quiet',
            '--ao=pulse,alsa,',
            video_path
        ])
        playProcess.wait()
        return True
    except Exception as e:
        print(f"Error playing {os.path.basename(video_path)}: {e}")
        return False

def playAlternatingVideos():
    """Main playback loop"""
    while True:
        # Update state (checks for new videos, new session, etc.)
        tv_videos, commercial_videos = updatePlaybackState()
        
        if not tv_videos and not commercial_videos:
            print("No videos found!")
            return False
        
        # Play commercial
        if commercial_videos:
            commercial = getUnplayedVideo('commercials')
            if commercial:
                print("--- COMMERCIAL ---")
                commercial_path = os.path.join(commercials_directory, commercial)
                if playVideo(commercial_path):
                    markVideoPlayed('commercials', commercial)
                else:
                    time.sleep(1)
        
        # Play TV show
        if tv_videos:
            tv_show = getUnplayedVideo('tv')
            if tv_show:
                print("--- TV SHOW ---")
                tv_show_path = os.path.join(tv_directory, tv_show)
                if playVideo(tv_show_path):
                    markVideoPlayed('tv', tv_show)
                else:
                    time.sleep(1)
        
        time.sleep(0.5)

def createDirectories():
    """Create necessary directories"""
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

def main():
    print("TinyTV Player with Session Tracking")
    print("=" * 50)
    
    if not createDirectories():
        sys.exit(1)
    
    # Load existing playback state
    loadPlaybackState()
    
    # Update state with current videos
    tv_videos, commercial_videos = updatePlaybackState()
    
    if not tv_videos and not commercial_videos:
        print("\nNo videos found. Please add video files:")
        print(f"  TV shows: {tv_directory}")
        print(f"  Commercials: {commercials_directory}")
        sys.exit(1)
    
    # Save initial state
    savePlaybackState()
    
    print(f"\nFound {len(tv_videos)} TV show(s)")
    print(f"Found {len(commercial_videos)} commercial(s)")
    
    # Count unplayed
    tv_unplayed = sum(1 for d in playback_state['tv'].values() if not d['played_this_session'])
    comm_unplayed = sum(1 for d in playback_state['commercials'].values() if not d['played_this_session'])
    print(f"Remaining this session: {tv_unplayed} TV, {comm_unplayed} commercials")
    
    print("\nPress Ctrl+C to stop")
    print("-" * 50)
    
    try:
        playAlternatingVideos()
    except KeyboardInterrupt:
        print("\nStopping TinyTV")
        savePlaybackState()
        sys.exit(0)

if __name__ == "__main__":
    if not createDirectories():
        sys.exit(1)
    main()