"""
Commercial Video Processor for 4-inch Screen (800x480)
Converts videos to optimal format with black bar removal, subtitle burning, and smart scaling
Author: [Your Name/GitHub Handle]
Date: November 2025

Setup:
1. Place this script in a folder.
2. Create an 'input' folder in the same directory and place your videos there.
3. The script will automatically create an 'output' folder for the processed files.
"""

import os
import subprocess
import time
import json
import multiprocessing
import re
import threading
import sys

# --- ANONYMISED PATH CONFIGURATION ---
# Sets paths relative to where the script is saved
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

# Fallback: If you prefer using a generic Home directory path (e.g., ~/VideoProjects)
# BASE_DIR = os.path.expanduser('~/video_processing_workspace')
# -------------------------------------

ROTATE = True                        # Rotate 90 degrees or not
ROTATE_DIR = 'counterclockwise'      # 'clockwise' or 'counterclockwise'

# Target dimensions with flexible width
TARGET_HEIGHT = 480                 # Strict height requirement
TARGET_WIDTH_MAX = 800              # Maximum acceptable width (full screen)
TARGET_WIDTH_MIN = 770              # Minimum acceptable width
TARGET_WIDTH_PREFERRED = 780        # Preferred target width (accounts for case coverage)

# Scaling limits - more conservative to minimize distortion
MAX_STRETCH = 1.12   # Maximum stretch factor (12% larger)
MIN_SQUEEZE = 0.80   # Minimum squeeze factor (20% smaller)
PREFERRED_MAX_DISTORTION = 1.40     # Prefer to stay under 10% distortion

# Preference strength - how strongly to prefer TARGET_WIDTH_PREFERRED
WIDTH_PREFERENCE_STRENGTH = 9

# Subtitle Configuration (optimized for 4-inch screen)
SUBTITLE_FONT_SIZE = 18             
SUBTITLE_FONT_NAME = 'Arial'        
SUBTITLE_OUTLINE = 2                
SUBTITLE_MARGIN_V = 15              

# CPU Control Configuration
# Automatically use half of the available cores if not specified
MAX_CPU_THREADS = multiprocessing.cpu_count() // 2

def is_video_file(path):
    return path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv', '.webm', 'mpeg'))

def find_subtitle_file(video_path):
    """Find matching .srt subtitle file for a video."""
    base_path = os.path.splitext(video_path)[0]
    srt_path = base_path + '.srt'
    return srt_path if os.path.exists(srt_path) else None

def find_videos(directory):
    videos = []
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created input directory: {directory}")
        return videos

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
                return int(stream['width']), int(stream['height'])
        return None, None
    except:
        return None, None

def detect_black_bars(video_path, sample_duration=10):
    """Detect black bars using ffmpeg's cropdetect filter."""
    duration = get_video_duration(video_path)
    if not duration or duration < 2:
        return None
    
    sample_points = [duration * 0.1, duration * 0.5, duration * 0.9]
    crop_values = []
    
    for start_time in sample_points:
        cmd = [
            'ffmpeg', '-ss', str(start_time), '-i', video_path,
            '-t', '3', '-vf', 'cropdetect=24:16:0', '-f', 'null', '-'
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            crop_matches = re.findall(r'crop=(\d+):(\d+):(\d+):(\d+)', result.stdout)
            if crop_matches:
                crop_values.extend(crop_matches)
        except:
            continue
    
    if not crop_values:
        return None
    
    from collections import Counter
    most_common_crop = Counter(crop_values).most_common(1)[0][0]
    crop_w, crop_h, crop_x, crop_y = map(int, most_common_crop)
    
    orig_w, orig_h = get_video_dimensions(video_path)
    if orig_w and orig_h:
        if (orig_w - crop_w) > orig_w * 0.02 or (orig_h - crop_h) > orig_h * 0.02:
            return {'width': crop_w, 'height': crop_h, 'x': crop_x, 'y': crop_y}
    return None

def get_video_duration(video_path):
    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', video_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(json.loads(result.stdout)['format']['duration'])
    except:
        return None

def draw_progress_bar(percentage, width=40):
    filled = int(width * percentage / 100)
    return f"[{'=' * filled}{'-' * (width - filled)}] {percentage:6.2f}%"

class ProgressTracker:
    def __init__(self, video_name, duration=None):
        self.video_name = video_name
        self.duration = duration
        self.current_time = 0
        self.last_update = 0
        
    def update_progress(self, current_time):
        self.current_time = current_time
        percentage = min((current_time / self.duration) * 100, 100) if self.duration else 0
        now = time.time()
        if now - self.last_update > 0.5:
            print(f"\r  Encoding: {draw_progress_bar(percentage)} {format_time(current_time)}/{format_time(self.duration if self.duration else 0)}", end='', flush=True)
            self.last_update = now

def parse_ffmpeg_progress(line, tracker):
    time_match = re.search(r'time=(\d+):(\d+):(\d+\.?\d*)', line)
    if time_match:
        current_time = int(time_match.group(1)) * 3600 + int(time_match.group(2)) * 60 + float(time_match.group(3))
        tracker.update_progress(current_time)

def calculate_optimal_dimensions(video_w, video_h, rotate=False):
    if rotate: video_w, video_h = video_h, video_w
    video_aspect = video_w / video_h
    best_config, best_score = None, float('inf')
    
    for target_w in range(TARGET_WIDTH_MAX, TARGET_WIDTH_MIN - 1, -2):
        target_h = TARGET_HEIGHT
        target_aspect = target_w / target_h
        
        if video_aspect > target_aspect:
            scale_h = int(target_w / video_aspect)
            stretch = target_h / scale_h
            score = (abs(stretch - 1.0) * 100) if MIN_SQUEEZE <= stretch <= MAX_STRETCH else 2000
        else:
            scale_w = int(target_h * video_aspect)
            stretch = target_w / scale_w
            score = (abs(stretch - 1.0) * 100) if MIN_SQUEEZE <= stretch <= MAX_STRETCH else 2000
        
        score += abs(target_w - TARGET_WIDTH_PREFERRED) * WIDTH_PREFERENCE_STRENGTH
        if best_config is None or score < best_score:
            best_score, best_config = score, {'target_w': target_w, 'target_h': target_h}
    return best_config

def calculate_scaling_strategy(video_w, video_h, target_w, target_h, rotate=False):
    if rotate: video_w, video_h = video_h, video_w
    video_aspect = video_w / video_h
    target_aspect = target_w / target_h
    
    if video_aspect > target_aspect:
        scale_w, scale_h = target_w, int(target_w / video_aspect)
    else:
        scale_w, scale_h = int(target_h * video_aspect), target_h
    
    w_scale = target_w / scale_w if scale_w != target_w else 1.0
    h_scale = target_h / scale_h if scale_h != target_h else 1.0
    scale_factor = min(w_scale, h_scale)
    
    if MIN_SQUEEZE <= scale_factor <= MAX_STRETCH:
        if abs(w_scale - 1.0) < abs(h_scale - 1.0):
            final_w, final_h = target_w, int(scale_h * scale_factor)
        else:
            final_w, final_h = int(scale_w * scale_factor), target_h
        return {'scale_w': scale_w, 'scale_h': scale_h, 'final_w': final_w, 'final_h': final_h, 'use_scaling': True, 'needs_crop': final_w != target_w or final_h != target_h}
    
    return {'scale_w': scale_w, 'scale_h': scale_h, 'final_w': scale_w, 'final_h': scale_h, 'use_scaling': False, 'needs_crop': True}

def escape_filter_path(path):
    path = path.replace('\\', '/').replace(':', r'\:').replace("'", r"'\\\''")
    return path

def build_subtitle_filter(srt_path):
    escaped_path = escape_filter_path(srt_path)
    style = f"FontName={SUBTITLE_FONT_NAME},FontSize={SUBTITLE_FONT_SIZE},PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline={SUBTITLE_OUTLINE},MarginV={SUBTITLE_MARGIN_V},Alignment=2,Bold=0"
    return f"subtitles='{escaped_path}':force_style='{style}'"

def build_filter(video_path, crop_info=None, subtitle_path=None):
    orig_w, orig_h = get_video_dimensions(video_path)
    if not orig_w: return f"scale={TARGET_WIDTH_PREFERRED}:{TARGET_HEIGHT}"
    
    cur_w, cur_h, filters = orig_w, orig_h, []
    if crop_info:
        filters.append(f"crop={crop_info['width']}:{crop_info['height']}:{crop_info['x']}:{crop_info['y']}")
        cur_w, cur_h = crop_info['width'], crop_info['height']
    
    opt = calculate_optimal_dimensions(cur_w, cur_h, ROTATE)
    strat = calculate_scaling_strategy(cur_w, cur_h, opt['target_w'], opt['target_h'], ROTATE)
    
    filters.append(f"scale={strat['final_w']}:{strat['final_h']}" if strat['use_scaling'] else f"scale={strat['scale_w']}:{strat['scale_h']}")
    
    if strat['needs_crop']:
        cw, ch = min(strat['final_w'], opt['target_w']), min(strat['final_h'], opt['target_h'])
        filters.append(f"crop={cw}:{ch}:{(strat['final_w']-cw)//2}:{(strat['final_h']-ch)//2}")
    
    if ROTATE: filters.append('transpose=1' if ROTATE_DIR == 'clockwise' else 'transpose=2')
    if subtitle_path: filters.append(build_subtitle_filter(subtitle_path))
    
    return ','.join(filters)

def format_time(seconds):
    return f"{int(seconds // 3600):02d}:{int((seconds % 3600) // 60):02d}:{int(seconds % 60):02d}"

def process_video(input_path, current_num, total_num):
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_path = os.path.join(OUTPUT_DIR, f"{base}.mp4")
    if os.path.exists(out_path): return False, 0
    
    duration = get_video_duration(input_path)
    sub_path = find_subtitle_file(input_path)
    crop = detect_black_bars(input_path)
    vf = build_filter(input_path, crop, sub_path)
    
    cmd = ['ffmpeg', '-i', input_path, '-vf', vf, '-c:v', 'libx264', '-profile:v', 'main', '-level', '3.0', '-preset', 'veryslow', '-crf', '34', '-threads', str(MAX_CPU_THREADS), '-c:a', 'aac', '-b:a', '256k', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-progress', 'pipe:1', out_path]
    
    tracker = ProgressTracker(base, duration)
    start = time.time()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1)
        for line in proc.stdout:
            if 'time=' in line: parse_ffmpeg_progress(line, tracker)
        proc.wait()
        return (True, time.time() - start) if proc.returncode == 0 else (False, 0)
    except:
        return False, 0

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    vids = find_videos(INPUT_DIR)
    if not vids:
        print(f"No videos found in {INPUT_DIR}. Add some videos and try again.")
        return

    print(f"Processing {len(vids)} videos...")
    for i, v in enumerate(vids, 1):
        process_video(v, i, len(vids))
        print()

if __name__ == '__main__':
    main()