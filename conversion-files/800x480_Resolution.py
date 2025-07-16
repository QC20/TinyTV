import os
import subprocess
import time
import json
import multiprocessing

# Configuration
DESKTOP = os.path.expanduser('~/Desktop')
INPUT_DIR = os.path.join(DESKTOP, 'input1')
OUTPUT_DIR = os.path.join(DESKTOP, 'output')
ROTATE = True                        # Rotate 90 degrees or not
ROTATE_DIR = 'counterclockwise'     # 'clockwise' or 'counterclockwise'
target_w = 800
target_h = 480
MAX_STRETCH = 1.05  # Maximum vertical stretch factor (5%)

# CPU Control Configuration
MAX_CPU_THREADS = multiprocessing.cpu_count() // 1  # Use half of available CPU cores
# You can also set this to a specific number like: MAX_CPU_THREADS = 4

def is_video_file(path):
    return path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv', '.webm', 'mpeg'))

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

def calculate_scaling_strategy(orig_w, orig_h, target_w, target_h, rotate=False):
    """Calculate optimal scaling strategy with minimal stretching"""
    
    # If rotating, swap dimensions
    if rotate:
        orig_w, orig_h = orig_h, orig_w
    
    # Calculate aspect ratios
    orig_aspect = orig_w / orig_h
    target_aspect = target_w / target_h
    
    # Calculate what dimensions we'd get with simple scaling
    if orig_aspect > target_aspect:
        # Video is wider than target - scale by width
        scale_w = target_w
        scale_h = int(target_w / orig_aspect)
    else:
        # Video is taller than target - scale by height
        scale_h = target_h
        scale_w = int(target_h * orig_aspect)
    
    # Check if we need stretching to fit exactly
    stretch_factor = 1.0
    use_stretch = False
    
    if scale_w != target_w or scale_h != target_h:
        # Calculate potential stretch factors
        w_stretch = target_w / scale_w if scale_w != target_w else 1.0
        h_stretch = target_h / scale_h if scale_h != target_h else 1.0
        
        # Use the smaller stretch factor (less distortion)
        stretch_factor = min(w_stretch, h_stretch)
        
        # Only apply stretch if it's within our maximum and beneficial
        if 1.0 < stretch_factor <= MAX_STRETCH:
            use_stretch = True
            if abs(w_stretch - 1.0) < abs(h_stretch - 1.0):
                # Stretch width
                final_w = target_w
                final_h = int(scale_h * stretch_factor)
            else:
                # Stretch height
                final_w = int(scale_w * stretch_factor)
                final_h = target_h
        else:
            # No stretching - use cropping instead
            final_w = scale_w
            final_h = scale_h
    else:
        final_w = scale_w
        final_h = scale_h
    
    return {
        'scale_w': scale_w,
        'scale_h': scale_h,
        'final_w': final_w,
        'final_h': final_h,
        'stretch_factor': stretch_factor if use_stretch else 1.0,
        'use_stretch': use_stretch,
        'needs_crop': final_w != target_w or final_h != target_h
    }

def build_filter(video_path):
    """Build filter string based on video dimensions"""
    orig_w, orig_h = get_video_dimensions(video_path)
    
    if orig_w is None or orig_h is None:
        print(f"Warning: Could not determine video dimensions for {video_path}")
        # Fallback to simple scaling
        filters = [f"scale={target_w}:{target_h}"]
    else:
        strategy = calculate_scaling_strategy(orig_w, orig_h, target_w, target_h, ROTATE)
        
        filters = []
        
        # Apply initial scaling
        if strategy['use_stretch']:
            filters.append(f"scale={strategy['final_w']}:{strategy['final_h']}")
            print(f"  Applying {strategy['stretch_factor']:.3f}x stretch factor")
        else:
            filters.append(f"scale={strategy['scale_w']}:{strategy['scale_h']}")
        
        # Apply cropping if needed
        if strategy['needs_crop']:
            crop_w = min(strategy['final_w'], target_w)
            crop_h = min(strategy['final_h'], target_h)
            crop_x = (strategy['final_w'] - crop_w) // 2
            crop_y = (strategy['final_h'] - crop_h) // 2
            filters.append(f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}")
            print(f"  Cropping to {crop_w}x{crop_h}")
        
        # Final scale to exact target if needed
        if strategy['final_w'] != target_w or strategy['final_h'] != target_h:
            filters.append(f"scale={target_w}:{target_h}")
    
    # Apply rotation if specified
    if ROTATE:
        trans = 'transpose=1' if ROTATE_DIR == 'clockwise' else 'transpose=2'
        filters.append(trans)
    
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
    if orig_w and orig_h:
        print(f"  Original dimensions: {orig_w}x{orig_h}")
    
    vf = build_filter(input_path)
    cmd = [
        'ffmpeg', '-i', input_path,
        '-vf', vf,
        '-c:v', 'libx264', '-profile:v', 'main', '-level', '3.0',
        '-preset', 'veryslow', '-crf', '26',
        '-threads', str(MAX_CPU_THREADS),  # Limit CPU threads
        '-c:a', 'aac', '-b:a', '128k',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        out_path
    ]
    
    print(f"Encoding '{base}' with filters: {vf}")
    start = time.time()
    try:
        subprocess.run(cmd, check=True)
        dur = time.time() - start
        size = os.path.getsize(out_path) // 1024
        print(f" -> Done in {dur:.1f}s, size={size} KB")
        return True, dur
    except subprocess.CalledProcessError as e:
        print(f"Error encoding '{base}': {e}")
        return False, 0

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    vids = find_videos(INPUT_DIR)
    total = len(vids)
    done = 0
    skip = 0
    total_conversion_time = 0
    
    print(f"Found {total} videos. Target: {target_w}x{target_h}")
    print(f"Maximum stretch factor: {MAX_STRETCH:.1%}")
    print(f"Using {MAX_CPU_THREADS} CPU threads (out of {multiprocessing.cpu_count()} available)")
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