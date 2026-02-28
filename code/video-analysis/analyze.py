#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import subprocess
import json
import time

def check_ffprobe():
    """Check if ffprobe is available"""
    try:
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def get_video_info_ffprobe(file_path):
    """Get video duration and file size using ffprobe"""
    try:
        cmd = [
            'ffprobe', 
            '-v', 'quiet', 
            '-print_format', 'json', 
            '-show_format', 
            str(file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if 'format' in data and 'duration' in data['format']:
                duration = float(data['format']['duration'])
                size = int(data['format']['size'])
                return duration, size, None
        
        return None, file_path.stat().st_size, f"ffprobe failed: {result.stderr[:100]}"
    except subprocess.TimeoutExpired:
        return None, file_path.stat().st_size, "ffprobe timeout"
    except Exception as e:
        return None, file_path.stat().st_size, f"ffprobe error: {str(e)[:100]}"

def get_video_info_mediainfo(file_path):
    """Fallback: try mediainfo if available"""
    try:
        cmd = ['mediainfo', '--Output=JSON', str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if 'media' in data and 'track' in data['media']:
                for track in data['media']['track']:
                    if track.get('@type') == 'General' and 'Duration' in track:
                        duration = float(track['Duration'])
                        size = file_path.stat().st_size
                        return duration, size, None
        
        return None, file_path.stat().st_size, "mediainfo failed"
    except:
        return None, file_path.stat().st_size, "mediainfo not available"

def estimate_duration_from_size(file_size, folder_type):
    """Rough duration estimate based on file size and content type"""
    # More realistic bitrate estimates for Pi-optimized videos
    if folder_type == 'tv':
        # TV episodes: ~0.3-0.5 Mbps (compressed for small screen)
        estimated_seconds = file_size / (0.4 * 1024 * 1024 / 8)  # 0.4 Mbps
    elif folder_type == 'films':
        # Films: ~0.5-0.8 Mbps (higher quality but still compressed)
        estimated_seconds = file_size / (0.6 * 1024 * 1024 / 8)  # 0.6 Mbps
    elif folder_type == 'commercials':
        # Commercials: ~0.6-1.0 Mbps (short, decent quality)
        estimated_seconds = file_size / (0.8 * 1024 * 1024 / 8)  # 0.8 Mbps
    else:
        # Default: ~0.5 Mbps
        estimated_seconds = file_size / (0.5 * 1024 * 1024 / 8)
    
    return max(10, estimated_seconds)  # Minimum 10 seconds

def get_video_info(file_path, folder_type):
    """Get video info with multiple fallback methods"""
    # Try ffprobe first
    duration, size, error1 = get_video_info_ffprobe(file_path)
    if duration is not None:
        return duration, size, "ffprobe"
    
    # Try mediainfo as fallback
    duration, size, error2 = get_video_info_mediainfo(file_path)
    if duration is not None:
        return duration, size, "mediainfo"
    
    # Final fallback: estimate from file size
    size = file_path.stat().st_size
    estimated_duration = estimate_duration_from_size(size, folder_type)
    return estimated_duration, size, "estimated"

def format_duration(seconds):
    """Convert seconds to hours:minutes format"""
    if seconds is None:
        return "Unknown"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"

def format_size(bytes_size):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}TB"

def draw_progress_bar(current, total, bar_length=30):
    """Draw a progress bar"""
    progress = current / total
    filled_length = int(bar_length * progress)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    percent = progress * 100
    return f"{bar} {percent:.0f}% ({current}/{total})"

def analyze_folder(folder_path, folder_name):
    """Analyze a single folder and return stats"""
    mp4_files = list(folder_path.glob("*.mp4"))
    
    if not mp4_files:
        return None
    
    total_files = len(mp4_files)
    total_duration = 0
    total_size = 0
    durations = []
    file_sizes = []
    method_counts = {"ffprobe": 0, "mediainfo": 0, "estimated": 0}
    
    print(f"Scanning {folder_name}... ", end='', flush=True)
    
    # Process each file
    for i, file_path in enumerate(mp4_files, 1):
        if i % max(1, total_files // 10) == 0 or i == total_files:
            progress = draw_progress_bar(i, total_files, 20)
            print(f"\rScanning {folder_name}... {progress}", end='', flush=True)
        
        duration, size, method = get_video_info(file_path, folder_name.lower())
        
        total_duration += duration
        durations.append(duration)
        method_counts[method] += 1
        
        total_size += size
        file_sizes.append(size)
        
        time.sleep(0.002)  # Small delay
    
    print()  # New line after progress
    
    return {
        'folder_name': folder_name,
        'total_files': total_files,
        'total_duration': total_duration,
        'total_size': total_size,
        'durations': durations,
        'file_sizes': file_sizes,
        'method_counts': method_counts
    }

def print_folder_stats(stats):
    """Print stats for a single folder"""
    if not stats or not stats['durations']:
        print(f"{stats['folder_name'].upper()}: No valid video files found")
        return
    
    folder_name = stats['folder_name']
    total_files = stats['total_files']
    total_duration = stats['total_duration']
    total_size = stats['total_size']
    durations = stats['durations']
    file_sizes = stats['file_sizes']
    method_counts = stats['method_counts']
    
    # Calculate statistics
    avg_duration = sum(durations) / len(durations)
    min_duration = min(durations)
    max_duration = max(durations)
    
    # Calculate viewing time scenarios
    total_hours = total_duration / 3600
    days_straight = total_hours / 24
    months_1hr = total_hours / 30.44
    months_2hr = (total_hours / 2) / 30.44
    
    # File size statistics
    min_size = min(file_sizes)
    max_size = max(file_sizes)
    avg_size = sum(file_sizes) / len(file_sizes)
    
    print(f"\n{folder_name.upper()} COLLECTION:")
    print(f"Files: {total_files:,} | Duration: {format_duration(total_duration)} | Size: {format_size(total_size)}")
    print(f"Watch time: {days_straight:.1f} days | 1hr daily: {months_1hr:.1f} months | 2hr daily: {months_2hr:.1f} months")
    print(f"File sizes: {format_size(min_size)} - {format_size(max_size)} | Average: {format_size(avg_size)}")
    
    # Show data source reliability
    if method_counts['estimated'] > 0:
        estimated_pct = (method_counts['estimated'] / total_files) * 100
        print(f"Duration source: {method_counts['ffprobe']} exact, {method_counts['estimated']} estimated ({estimated_pct:.0f}%)")
    
    # Category-specific insights
    if folder_name.lower() == 'tv':
        avg_episode_length = format_duration(avg_duration)
        episodes_per_hour = 3600 / avg_duration if avg_duration > 0 else 0
        print(f"Average episode: {avg_episode_length} | ~{episodes_per_hour:.1f} episodes per hour")
        
    elif folder_name.lower() == 'films':
        short_films = sum(1 for d in durations if d < 3600)
        feature_films = sum(1 for d in durations if 3600 <= d < 7200)
        long_films = sum(1 for d in durations if d >= 7200)
        longest_film = format_duration(max_duration)
        print(f"Short(<1h): {short_films} | Feature(1-2h): {feature_films} | Long(2h+): {long_films} | Longest: {longest_film}")
        
    elif folder_name.lower() == 'commercials':
        avg_commercial = format_duration(avg_duration)
        commercials_per_hour = 3600 / avg_duration if avg_duration > 0 else 0
        shortest = format_duration(min_duration)
        print(f"Average ad: {avg_commercial} | Shortest: {shortest} | ~{commercials_per_hour:.0f} ads per hour")

def main():
    print("MP4 Video Library Statistics")
    print("=" * 50)
    
    # Check for ffprobe
    if not check_ffprobe():
        print("Warning: ffprobe not found. Using file size estimates for duration.")
        print("Install with: sudo apt install ffmpeg")
        print()
    
    # Get current directory
    current_dir = Path.cwd()
    
    # Define the three folders
    folders = ['tv', 'films', 'commercials']
    all_stats = []
    
    # Analyze each folder
    for folder_name in folders:
        folder_path = current_dir / folder_name
        if folder_path.exists() and folder_path.is_dir():
            stats = analyze_folder(folder_path, folder_name)
            if stats:
                all_stats.append(stats)
                print_folder_stats(stats)
        else:
            print(f"\n{folder_name.upper()}: Folder not found")
    
    # Overall summary
    if all_stats:
        print("\n" + "=" * 50)
        print("OVERALL LIBRARY SUMMARY:")
        
        total_files = sum(s['total_files'] for s in all_stats)
        total_duration = sum(s['total_duration'] for s in all_stats)
        total_size = sum(s['total_size'] for s in all_stats)
        
        total_hours = total_duration / 3600
        days_straight = total_hours / 24
        months_1hr = total_hours / 30.44
        months_2hr = (total_hours / 2) / 30.44
        
        print(f"Total files: {total_files:,} | Duration: {format_duration(total_duration)} | Size: {format_size(total_size)}")
        print(f"Complete marathon: {days_straight:.1f} days | 1hr daily: {months_1hr:.1f} months | 2hr daily: {months_2hr:.1f} months")
        
        # Content breakdown
        tv_files = next((s['total_files'] for s in all_stats if s['folder_name'] == 'tv'), 0)
        film_files = next((s['total_files'] for s in all_stats if s['folder_name'] == 'films'), 0)
        commercial_files = next((s['total_files'] for s in all_stats if s['folder_name'] == 'commercials'), 0)
        
        print(f"Content mix: TV({tv_files}) Films({film_files}) Commercials({commercial_files})")
        
        # Storage per category percentages
        if total_size > 0:
            tv_size = next((s['total_size'] for s in all_stats if s['folder_name'] == 'tv'), 0)
            film_size = next((s['total_size'] for s in all_stats if s['folder_name'] == 'films'), 0)
            commercial_size = next((s['total_size'] for s in all_stats if s['folder_name'] == 'commercials'), 0)
            
            tv_pct = (tv_size / total_size) * 100
            film_pct = (film_size / total_size) * 100
            commercial_pct = (commercial_size / total_size) * 100
            print(f"Storage: TV({tv_pct:.1f}%) Films({film_pct:.1f}%) Commercials({commercial_pct:.1f}%)")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)