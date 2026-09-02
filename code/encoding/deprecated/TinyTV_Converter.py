"""
Commercial Video Processor for 4-inch Screen (800x480)
Converts videos to optimal format with black bar removal, subtitle burning, and smart scaling
Author: Jonas
Date: November 2025
Features: Flexible width targeting (770-800px, prefer 780px), rotation support, 
          progress tracking, CPU thread control, and intelligent distortion minimization
"""

import os
import subprocess
import time
import json
import multiprocessing
import re
import threading
import sys

# Configuration
DESKTOP = os.path.expanduser('~/Desktop')
INPUT_DIR = os.path.join(DESKTOP, 'c_input')
OUTPUT_DIR = os.path.join(DESKTOP, 'output')
ROTATE = True                        # Rotate 90 degrees or not
ROTATE_DIR = 'counterclockwise'     # 'clockwise' or 'counterclockwise'

# Target dimensions with flexible width
TARGET_HEIGHT = 480                 # Strict height requirement
TARGET_WIDTH_MAX = 800              # Maximum acceptable width (full screen)
TARGET_WIDTH_MIN = 770              # Minimum acceptable width
TARGET_WIDTH_PREFERRED = 780        # Preferred target width (accounts for case coverage)

# Scaling limits - more conservative to minimize distortion
MAX_STRETCH = 1.15   # Maximum stretch factor (15% larger)
MIN_SQUEEZE = 0.85   # Minimum squeeze factor (15% smaller)
PREFERRED_MAX_DISTORTION = 1.10     # Prefer to stay under 10% distortion

# Preference strength - how strongly to prefer TARGET_WIDTH_PREFERRED
# Higher value = stronger preference for 780 (will choose 780 unless significant quality benefit elsewhere)
# Lower value = weaker preference (will more readily choose 770 or 800 if it reduces distortion)
WIDTH_PREFERENCE_STRENGTH = 5

# Subtitle Configuration (optimized for 4-inch screen)
SUBTITLE_FONT_SIZE = 18             # Font size in pixels
SUBTITLE_FONT_NAME = 'Arial'        # Clear, readable font
SUBTITLE_OUTLINE = 2                # Outline width for better readability
SUBTITLE_MARGIN_V = 15              # Bottom margin in pixels

# CPU Control Configuration
MAX_CPU_THREADS = multiprocessing.cpu_count() // 1.0 # Use half of available CPU cores
# You can also set this to a specific number like: MAX_CPU_THREADS = 4

def is_video_file(path):
    return path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv', '.webm', 'mpeg'))

def find_subtitle_file(video_path):
    """
    Find matching .srt subtitle file for a video.
    Looks for a file with the same base name but .srt extension.
    """
    base_path = os.path.splitext(video_path)[0]
    srt_path = base_path + '.srt'
    
    if os.path.exists(srt_path):
        return srt_path
    return None

def find_videos(directory):
    videos = []
    for root, _, files in os.walk(directory):
        for f in files:
            if is_video_file(f):
                videos.append(os.path.join(root, f))
    return sorted(videos, key=lambda p: os.path.basename(p).lower())

def get_video_dimensions(video_path):
    """Get video dimensions using ffprobe"""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams',
        video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        for stream in data['streams']:
            if stream['codec_type'] == 'video':
                width = int(stream['width'])
                height = int(stream['height'])
                return width, height
        return None, None
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
        return None, None

def detect_black_bars(video_path, sample_duration=10):
    """
    Detect black bars/letterboxing in video using ffmpeg's cropdetect filter.
    Samples the video at multiple points to find consistent crop values.
    Returns the crop parameters as a dict: {width, height, x, y}
    """
    print(f"  Detecting black bars (sampling {sample_duration}s)...")
    
    # Get video duration first
    duration = get_video_duration(video_path)
    if not duration or duration < 2:
        print("  Could not determine duration, skipping black bar detection")
        return None
    
    # Sample from multiple points in the video
    sample_points = [
        duration * 0.1,   # 10% into video
        duration * 0.5,   # Middle
        duration * 0.9    # 90% into video
    ]
    
    crop_values = []
    
    for start_time in sample_points:
        cmd = [
            'ffmpeg', '-ss', str(start_time), '-i', video_path,
            '-t', str(min(3, sample_duration)),  # Sample 3 seconds at each point
            '-vf', 'cropdetect=24:16:0',  # Detect with threshold 24, rounds to 16
            '-f', 'null', '-'
        ]
        
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Find all crop values in output
            crop_matches = re.findall(r'crop=(\d+):(\d+):(\d+):(\d+)', result.stdout)
            if crop_matches:
                # Use the most common crop value from this sample
                crop_values.extend(crop_matches)
        except subprocess.CalledProcessError:
            continue
    
    if not crop_values:
        print("  No black bars detected")
        return None
    
    # Find the most common crop value (mode)
    from collections import Counter
    most_common_crop = Counter(crop_values).most_common(1)[0][0]
    
    crop_w, crop_h, crop_x, crop_y = map(int, most_common_crop)
    
    # Get original dimensions to compare
    orig_w, orig_h = get_video_dimensions(video_path)
    
    if orig_w and orig_h:
        # Only use crop if it actually removes something significant (more than 2% on any side)
        width_diff = orig_w - crop_w
        height_diff = orig_h - crop_h
        
        if width_diff > orig_w * 0.02 or height_diff > orig_h * 0.02:
            print(f"  Black bars detected! Original: {orig_w}x{orig_h}, After crop: {crop_w}x{crop_h}")
            return {
                'width': crop_w,
                'height': crop_h,
                'x': crop_x,
                'y': crop_y
            }
        else:
            print(f"  Minimal black bars detected (< 2%), keeping original dimensions")
            return None
    
    return None

def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe"""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format',
        video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        duration = float(data['format']['duration'])
        return duration
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, ValueError):
        return None

def draw_progress_bar(percentage, width=50):
    """Draw a text-based progress bar"""
    filled = int(width * percentage / 100)
    bar = '=' * filled + '-' * (width - filled)
    return f"[{bar}] {percentage:6.2f}%"

class ProgressTracker:
    def __init__(self, video_name, duration=None):
        self.video_name = video_name
        self.duration = duration
        self.current_time = 0
        self.percentage = 0
        self.last_update = 0
        
    def update_progress(self, current_time):
        self.current_time = current_time
        if self.duration and self.duration > 0:
            self.percentage = min((current_time / self.duration) * 100, 100)
        else:
            self.percentage = 0
            
        # Only update display every 0.5 seconds to avoid flickering
        now = time.time()
        if now - self.last_update > 0.5:
            self.display_progress()
            self.last_update = now
    
    def display_progress(self):
        progress_bar = draw_progress_bar(self.percentage)
        time_info = ""
        if self.duration:
            time_info = f" ({format_time(self.current_time)} / {format_time(self.duration)})"
        
        # Use \r to overwrite the line
        print(f"\r  Progress: {progress_bar}{time_info}", end='', flush=True)

def parse_ffmpeg_progress(line, tracker):
    """Parse ffmpeg progress output"""
    if 'out_time_ms=' in line:
        # Extract microseconds
        match = re.search(r'out_time_ms=(\d+)', line)
        if match:
            microseconds = int(match.group(1))
            seconds = microseconds / 1_000_000
            tracker.update_progress(seconds)
    elif 'out_time=' in line:
        # Extract time in HH:MM:SS.MS format
        match = re.search(r'out_time=(\d+):(\d+):(\d+\.\d+)', line)
        if match:
            hours, minutes, seconds = match.groups()
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            tracker.update_progress(total_seconds)

def calculate_optimal_dimensions(width, height, will_rotate):
    """
    Calculate optimal target dimensions based on source aspect ratio.
    Accounts for rotation if specified.
    Returns dict with target_w, target_h, and analysis info.
    """
    # If rotating, we need to account for dimension swap
    if will_rotate:
        # After rotation, width becomes height and vice versa
        effective_width = height
        effective_height = width
    else:
        effective_width = width
        effective_height = height
    
    # Calculate source aspect ratio (what it will be after rotation if applicable)
    source_aspect = effective_width / effective_height
    
    # Our target range is 770-800 width, 480 height
    # So aspect ratios range from 770/480 = 1.604 to 800/480 = 1.667
    min_target_aspect = TARGET_WIDTH_MIN / TARGET_HEIGHT  # 1.604
    max_target_aspect = TARGET_WIDTH_MAX / TARGET_HEIGHT  # 1.667
    preferred_target_aspect = TARGET_WIDTH_PREFERRED / TARGET_HEIGHT  # 1.625
    
    # Determine best target width based on source aspect ratio
    if source_aspect <= min_target_aspect:
        # Source is narrower than our minimum, use minimum width
        target_w = TARGET_WIDTH_MIN
    elif source_aspect >= max_target_aspect:
        # Source is wider than our maximum, use maximum width
        target_w = TARGET_WIDTH_MAX
    else:
        # Source is within our range
        # Calculate what width would give us the source aspect ratio
        natural_width = int(source_aspect * TARGET_HEIGHT)
        
        # Apply preference for 780px
        # Calculate distance from preferred width (780)
        distance_from_preferred = abs(natural_width - TARGET_WIDTH_PREFERRED)
        
        # If natural width is very close to preferred (within preference strength pixels)
        if distance_from_preferred <= WIDTH_PREFERENCE_STRENGTH:
            target_w = TARGET_WIDTH_PREFERRED
        else:
            target_w = natural_width
    
    # Ensure we're within bounds
    target_w = max(TARGET_WIDTH_MIN, min(TARGET_WIDTH_MAX, target_w))
    target_h = TARGET_HEIGHT
    
    return {
        'target_w': target_w,
        'target_h': target_h,
        'source_aspect': source_aspect,
        'target_aspect': target_w / target_h
    }

def calculate_scaling_strategy(width, height, target_w, target_h, will_rotate):
    """
    Determine the best scaling strategy to reach target dimensions.
    Minimizes distortion while staying within acceptable limits.
    
    Returns dict with:
    - use_scaling: whether to use aspect-ratio-changing scaling
    - scale_factor: the scaling factor to apply
    - scaling_type: 'stretch', 'squeeze', or 'none'
    - final_w, final_h: dimensions after scaling
    - needs_crop: whether final crop is needed
    - scale_w, scale_h: intermediate scaling dimensions (if not using distortion)
    """
    aspect = width / height
    target_aspect = target_w / target_h
    
    # Calculate what scale factor we'd need to match target aspect ratio
    if aspect < target_aspect:
        # Need to stretch width (or squeeze height)
        needed_factor = target_aspect / aspect
        scaling_type = "stretch"
    elif aspect > target_aspect:
        # Need to squeeze width (or stretch height) 
        needed_factor = aspect / target_aspect
        scaling_type = "squeeze"
    else:
        # Aspects already match
        needed_factor = 1.0
        scaling_type = "none"
    
    # Check if needed factor is within acceptable limits
    use_distortion = False
    if scaling_type == "stretch" and needed_factor <= MAX_STRETCH:
        use_distortion = True
    elif scaling_type == "squeeze" and needed_factor <= (1 / MIN_SQUEEZE):
        use_distortion = True
    elif scaling_type == "none":
        use_distortion = True  # No distortion needed
    
    # Determine strategy
    if use_distortion and needed_factor <= PREFERRED_MAX_DISTORTION:
        # Use distortion - it's within preferred limits
        if scaling_type == "stretch":
            final_w = int(width * needed_factor)
            final_h = height
        elif scaling_type == "squeeze":
            final_w = width
            final_h = int(height * needed_factor)
        else:
            final_w = width
            final_h = height
        
        return {
            'use_scaling': True,
            'scale_factor': needed_factor,
            'scaling_type': scaling_type,
            'final_w': final_w,
            'final_h': final_h,
            'needs_crop': False,
            'scale_w': final_w,
            'scale_h': final_h
        }
    else:
        # Use traditional scale + crop approach
        # Scale to target height, then crop width (or vice versa)
        if aspect < target_aspect:
            # Scale based on width, crop height
            scale_w = target_w
            scale_h = int(target_w / aspect)
        else:
            # Scale based on height, crop width
            scale_h = target_h
            scale_w = int(target_h * aspect)
        
        return {
            'use_scaling': False,
            'scale_factor': 1.0,
            'scaling_type': 'none',
            'final_w': scale_w,
            'final_h': scale_h,
            'needs_crop': True,
            'scale_w': scale_w,
            'scale_h': scale_h
        }

def build_subtitle_filter(subtitle_path):
    """
    Build subtitle filter with proper escaping for file paths.
    Optimized for small 4-inch screen readability.
    """
    # Escape the path for ffmpeg filter
    escaped_path = subtitle_path.replace('\\', '\\\\').replace(':', '\\:')
    
    subtitle_filter = (
        f"subtitles='{escaped_path}':"
        f"force_style='"
        f"FontName={SUBTITLE_FONT_NAME},"
        f"FontSize={SUBTITLE_FONT_SIZE},"
        f"OutlineColour=&H80000000,"
        f"Outline={SUBTITLE_OUTLINE},"
        f"MarginV={SUBTITLE_MARGIN_V}"
        f"'"
    )
    return subtitle_filter

def build_filter(video_path, crop_info=None, subtitle_path=None):
    """
    Build filter string based on video dimensions.
    Now includes black bar cropping and subtitle burning if available.
    IMPORTANT: Subtitles are applied BEFORE rotation so they rotate correctly with the video.
    """
    orig_w, orig_h = get_video_dimensions(video_path)
    
    if orig_w is None or orig_h is None:
        print(f"Warning: Could not determine video dimensions for {video_path}")
        # Fallback to simple scaling
        filters = [f"scale={TARGET_WIDTH_PREFERRED}:{TARGET_HEIGHT}"]
    else:
        # Start with original dimensions
        current_w, current_h = orig_w, orig_h
        
        filters = []
        
        # Step 1: Crop black bars if detected
        if crop_info:
            crop_filter = f"crop={crop_info['width']}:{crop_info['height']}:{crop_info['x']}:{crop_info['y']}"
            filters.append(crop_filter)
            current_w = crop_info['width']
            current_h = crop_info['height']
            print(f"  Applying black bar crop: {current_w}x{current_h}")
        
        # Step 2: Calculate optimal target dimensions
        optimal_dims = calculate_optimal_dimensions(current_w, current_h, ROTATE)
        target_w = optimal_dims['target_w']
        target_h = optimal_dims['target_h']
        
        print(f"  Optimal target dimensions: {target_w}x{target_h}")
        
        # Step 3: Calculate scaling strategy
        strategy = calculate_scaling_strategy(current_w, current_h, target_w, target_h, ROTATE)
        
        # Apply initial scaling
        if strategy['use_scaling']:
            filters.append(f"scale={strategy['final_w']}:{strategy['final_h']}")
            if strategy['scaling_type'] == "stretch":
                distortion_pct = (strategy['scale_factor'] - 1.0) * 100
                print(f"  Applying {strategy['scale_factor']:.3f}x stretch ({distortion_pct:.1f}% distortion)")
            elif strategy['scaling_type'] == "squeeze":
                distortion_pct = (1.0 - strategy['scale_factor']) * 100
                print(f"  Applying {strategy['scale_factor']:.3f}x squeeze ({distortion_pct:.1f}% distortion)")
        else:
            filters.append(f"scale={strategy['scale_w']}:{strategy['scale_h']}")
        
        # Apply cropping if needed to reach exact target
        if strategy['needs_crop']:
            crop_w = min(strategy['final_w'], target_w)
            crop_h = min(strategy['final_h'], target_h)
            crop_x = (strategy['final_w'] - crop_w) // 2
            crop_y = (strategy['final_h'] - crop_h) // 2
            filters.append(f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}")
            print(f"  Cropping to {crop_w}x{crop_h}")
        
        # Final scale to exact target if still needed
        if strategy['final_w'] != target_w or strategy['final_h'] != target_h:
            filters.append(f"scale={target_w}:{target_h}")
    
    # Add subtitles BEFORE rotation (so they rotate with the video content)
    if subtitle_path:
        subtitle_filter = build_subtitle_filter(subtitle_path)
        filters.append(subtitle_filter)
        print(f"  Burning in subtitles: {os.path.basename(subtitle_path)}")
        print(f"    Font: {SUBTITLE_FONT_NAME}, Size: {SUBTITLE_FONT_SIZE}px")
    
    # Apply rotation AFTER subtitles (so subtitles rotate with the content)
    if ROTATE:
        trans = 'transpose=1' if ROTATE_DIR == 'clockwise' else 'transpose=2'
        filters.append(trans)
        print(f"  Applying rotation: {ROTATE_DIR}")
    
    return ','.join(filters)

def format_time(seconds):
    """Format seconds into HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def process_video(input_path, current_num, total_num):
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_path = os.path.join(OUTPUT_DIR, f"{base}.mp4")
    
    print(f"({current_num}/{total_num})")
    
    if os.path.exists(out_path):
        print(f"Skipping '{base}', output exists.")
        return False, 0
    
    print(f"Analyzing '{base}'...")
    orig_w, orig_h = get_video_dimensions(input_path)
    duration = get_video_duration(input_path)
    
    if orig_w and orig_h:
        print(f"  Original dimensions: {orig_w}x{orig_h}")
    if duration:
        print(f"  Duration: {format_time(duration)}")
    
    # Check for subtitle file
    subtitle_path = find_subtitle_file(input_path)
    if subtitle_path:
        print(f"  Found subtitle file: {os.path.basename(subtitle_path)}")
    
    # Detect and remove black bars
    crop_info = detect_black_bars(input_path)
    
    # Build filter chain (includes subtitles if available)
    vf = build_filter(input_path, crop_info, subtitle_path)
    
    cmd = [
        'ffmpeg', '-i', input_path,
        '-vf', vf,
        '-c:v', 'libx264', '-profile:v', 'main', '-level', '3.0',
        '-preset', 'veryslow', '-crf', '23',
        '-threads', str(MAX_CPU_THREADS),
        '-c:a', 'aac', '-b:a', '256k',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        '-progress', 'pipe:1',
        out_path
    ]
    
    print(f"Encoding '{base}' with filters: {vf}")
    
    # Create progress tracker
    tracker = ProgressTracker(base, duration)
    
    start = time.time()
    try:
        # Run ffmpeg with progress monitoring
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor progress in real time
        for line in process.stdout:
            if 'time=' in line:
                parse_ffmpeg_progress(line, tracker)
        
        process.wait()
        
        if process.returncode != 0:
            print(f"\nError: ffmpeg returned code {process.returncode}")
            return False, 0
        
        # Ensure we show 100% completion
        if duration:
            tracker.update_progress(duration)
        
        dur = time.time() - start
        size = os.path.getsize(out_path) // 1024
        print(f"\n -> Done in {dur:.1f}s, size={size} KB")
        return True, dur
        
    except subprocess.CalledProcessError as e:
        print(f"\nError encoding '{base}': {e}")
        return False, 0
    except Exception as e:
        print(f"\nUnexpected error encoding '{base}': {e}")
        return False, 0

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    vids = find_videos(INPUT_DIR)
    total = len(vids)
    done = 0
    skip = 0
    total_conversion_time = 0
    videos_with_subs = 0
    
    # Count videos with subtitles
    for v in vids:
        if find_subtitle_file(v):
            videos_with_subs += 1
    
    print(f"Found {total} videos.")
    print(f"Videos with subtitles: {videos_with_subs}")
    print(f"Target: {TARGET_HEIGHT}h × {TARGET_WIDTH_MIN}-{TARGET_WIDTH_MAX}w (prefer {TARGET_WIDTH_PREFERRED}w)")
    print(f"Scaling limits: {MIN_SQUEEZE:.1%} squeeze to {MAX_STRETCH:.1%} stretch")
    print(f"Using {MAX_CPU_THREADS} CPU threads (out of {multiprocessing.cpu_count()} available)")
    print(f"Black bar detection: ENABLED")
    print(f"Subtitle settings: Font={SUBTITLE_FONT_NAME}, Size={SUBTITLE_FONT_SIZE}px, Outline={SUBTITLE_OUTLINE}px")
    print()
    
    overall_start = time.time()
    
    for i, v in enumerate(vids, 1):
        success, conversion_time = process_video(v, i, total)
        if success:
            done += 1
            total_conversion_time += conversion_time
        else:
            skip += 1
        print()  # Add spacing between videos
    
    overall_end = time.time()
    overall_duration = overall_end - overall_start
    
    print(f"Finished: {done} processed, {skip} skipped/failed.")
    print(f"Total conversion time: {format_time(total_conversion_time)} (total time in minutes:seconds: {int(total_conversion_time//60)}:{int(total_conversion_time%60):02d})")
    print(f"Overall script runtime: {format_time(overall_duration)}")

if __name__ == '__main__':
    main()