import os
import subprocess
import time
import json

# Configuration
DESKTOP = os.path.expanduser('~/Desktop')
INPUT_DIR = os.path.join(DESKTOP, 'input')
OUTPUT_DIR = os.path.join(DESKTOP, 'output')
ROTATE = True                        # Rotate 90 degrees or not
ROTATE_DIR = 'counterclockwise'     # 'clockwise' or 'counterclockwise'
target_w = 800
target_h = 480
VERT_DISTORT = 1.05  # vertical stretch factor (~5%)
CROP_TOLERANCE = 0.05  # Allow up to 5% cropping

# Calculate the scaled height after vertical distortion
distorted_h = int(target_h * VERT_DISTORT)

# Calculate how many pixels to crop vertically and horizontally to fit exactly 800x480
crop_v = distorted_h - target_h  # pixels to crop vertically

# Because width is 800 originally, crop a bit of width to balance:
# Calculate equivalent horizontal crop using aspect ratio so crop amount is balanced
crop_h = int(crop_v * (target_w / distorted_h))  # proportional horizontal crop

# Final cropped width and height
crop_w = target_w - crop_h
crop_h_final = target_h

# Offsets for centered cropping
crop_x = crop_h // 2
crop_y = crop_v // 2

def is_video_file(path):
    return path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv', '.webm', 'mpeg'))

def find_videos(directory):
    videos = []
    for root, _, files in os.walk(directory):
        for f in files:
            if is_video_file(f):
                videos.append(os.path.join(root, f))
    return sorted(videos, key=lambda p: os.path.basename(p).lower())

def probe_video(input_path):
    """Probe video to get dimensions and other metadata"""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams',
        input_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # Find the first video stream
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                width = int(stream.get('width', 0))
                height = int(stream.get('height', 0))
                return width, height
        
        print(f"Warning: No video stream found in {input_path}")
        return None, None
        
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        print(f"Error probing {input_path}: {e}")
        return None, None

def calculate_optimal_scaling(input_w, input_h, target_w, target_h):
    """
    Calculate if we need cropping and what the optimal scaling should be.
    Returns: (needs_crop, scale_filter, detailed_report)
    """
    if not input_w or not input_h:
        return True, None, {
            'strategy': 'fallback',
            'scaling': 'unknown',
            'crop_type': 'unknown',
            'crop_percent': 0,
            'description': "Unknown dimensions - using fallback method"
        }
    
    # Calculate aspect ratios
    input_ratio = input_w / input_h
    target_ratio = target_w / target_h
    
    # Calculate scaling options
    # Option 1: Scale to fit width (may need vertical crop)
    scale_by_width_h = int(target_w / input_ratio)
    
    # Option 2: Scale to fit height (may need horizontal crop)  
    scale_by_height_w = int(target_h * input_ratio)
    
    # Determine scaling direction
    scale_factor_width = target_w / input_w
    scale_factor_height = target_h / input_h
    
    # Check if we can fit without cropping more than tolerance
    width_crop_percent = 0
    height_crop_percent = 0
    
    if scale_by_width_h > target_h:
        # Scaling by width results in height overflow
        height_crop_percent = (scale_by_width_h - target_h) / scale_by_width_h
        
    if scale_by_height_w > target_w:
        # Scaling by height results in width overflow
        width_crop_percent = (scale_by_height_w - target_w) / scale_by_height_w
    
    # Determine best approach
    if height_crop_percent <= CROP_TOLERANCE and width_crop_percent <= CROP_TOLERANCE:
        # We can fit with minimal or no cropping
        if height_crop_percent <= width_crop_percent:
            # Scale by width, minimal height crop
            scaling_type = "up" if scale_factor_width > 1 else "down" if scale_factor_width < 1 else "none"
            if height_crop_percent == 0:
                return False, f"scale={target_w}:{scale_by_width_h}", {
                    'strategy': 'perfect_fit',
                    'scaling': f"scaled {scaling_type} by {scale_factor_width:.2f}x",
                    'crop_type': 'none',
                    'crop_percent': 0,
                    'description': f"Perfect fit by width: {input_w}x{input_h} → {target_w}x{scale_by_width_h}"
                }
            else:
                crop_amount = scale_by_width_h - target_h
                crop_offset = crop_amount // 2
                return True, f"scale={target_w}:{scale_by_width_h},crop={target_w}:{target_h}:0:{crop_offset}", {
                    'strategy': 'minimal_crop',
                    'scaling': f"scaled {scaling_type} by {scale_factor_width:.2f}x",
                    'crop_type': 'vertical',
                    'crop_percent': height_crop_percent * 100,
                    'description': f"Scale by width + crop: {input_w}x{input_h} → {target_w}x{scale_by_width_h} → {target_w}x{target_h}"
                }
        else:
            # Scale by height, minimal width crop
            scaling_type = "up" if scale_factor_height > 1 else "down" if scale_factor_height < 1 else "none"
            if width_crop_percent == 0:
                return False, f"scale={scale_by_height_w}:{target_h}", {
                    'strategy': 'perfect_fit',
                    'scaling': f"scaled {scaling_type} by {scale_factor_height:.2f}x",
                    'crop_type': 'none',
                    'crop_percent': 0,
                    'description': f"Perfect fit by height: {input_w}x{input_h} → {scale_by_height_w}x{target_h}"
                }
            else:
                crop_amount = scale_by_height_w - target_w
                crop_offset = crop_amount // 2
                return True, f"scale={scale_by_height_w}:{target_h},crop={target_w}:{target_h}:{crop_offset}:0", {
                    'strategy': 'minimal_crop',
                    'scaling': f"scaled {scaling_type} by {scale_factor_height:.2f}x",
                    'crop_type': 'horizontal',
                    'crop_percent': width_crop_percent * 100,
                    'description': f"Scale by height + crop: {input_w}x{input_h} → {scale_by_height_w}x{target_h} → {target_w}x{target_h}"
                }
    
    # Need significant cropping - use original method with distortion
    distortion_scale_factor = target_w / input_w
    scaling_type = "up" if distortion_scale_factor > 1 else "down" if distortion_scale_factor < 1 else "none"
    return True, f"scale={target_w}:{distorted_h},crop={crop_w}:{crop_h_final}:{crop_x}:{crop_y}", {
        'strategy': 'distortion_method',
        'scaling': f"scaled {scaling_type} by {distortion_scale_factor:.2f}x + {VERT_DISTORT*100-100:.1f}% vertical stretch",
        'crop_type': 'balanced',
        'crop_percent': max(height_crop_percent, width_crop_percent) * 100,
        'description': f"Heavy crop needed: {input_w}x{input_h} → {target_w}x{distorted_h} → {crop_w}x{crop_h_final}"
    }

def build_filter(input_path):
    """Build the filter chain based on input video dimensions"""
    # Probe the video first
    input_w, input_h = probe_video(input_path)
    
    if input_w is None or input_h is None:
        # Fallback to original method if probing fails
        print(f"  Using fallback method (probing failed)")
        return build_original_filter(), {
            'strategy': 'fallback',
            'scaling': 'unknown',
            'crop_type': 'balanced',
            'crop_percent': (crop_v / distorted_h) * 100,
            'description': "Probe failed - using original distortion method"
        }
    
    print(f"  Input dimensions: {input_w}x{input_h}")
    
    # If rotation is enabled, swap dimensions for calculation
    calc_w, calc_h = (input_h, input_w) if ROTATE else (input_w, input_h)
    
    # Calculate optimal scaling
    needs_crop, scale_filter, report = calculate_optimal_scaling(calc_w, calc_h, target_w, target_h)
    
    # Build filter chain
    filters = []
    
    if scale_filter:
        filters.append(scale_filter)
    
    # Add rotation if specified
    if ROTATE:
        trans = 'transpose=1' if ROTATE_DIR == 'clockwise' else 'transpose=2'
        filters.append(trans)
        # Update report to mention rotation
        if ROTATE:
            report['description'] += f" + rotated {ROTATE_DIR}"
    
    return ','.join(filters), report

def build_original_filter():
    """Original filter method as fallback"""
    trans = None
    if ROTATE:
        trans = 'transpose=1' if ROTATE_DIR == 'clockwise' else 'transpose=2'
    
    filters = []
    # Scale width to 800 and height to distorted height (vertical stretch)
    filters.append(f"scale={target_w}:{distorted_h}")
    # Crop to final target dimensions with balanced crop offsets
    filters.append(f"crop={crop_w}:{crop_h_final}:{crop_x}:{crop_y}")
    
    if trans:
        filters.append(trans)
    
    return ','.join(filters)

def process_video(input_path):
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_path = os.path.join(OUTPUT_DIR, f"{base}.mp4")
    
    if os.path.exists(out_path):
        print(f"Skipping '{base}', output exists.")
        return False, None
    
    vf, report = build_filter(input_path)
    print(f"  Strategy: {report['description']}")
    
    cmd = [
        'ffmpeg', '-i', input_path,
        '-vf', vf,
        '-c:v', 'libx264', '-profile:v', 'main', '-level', '3.0',
        '-preset', 'veryslow', '-crf', '30',
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
        return True, report
    except subprocess.CalledProcessError as e:
        print(f"Error encoding '{base}': {e}")
        return False, None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    vids = find_videos(INPUT_DIR)
    total = len(vids)
    done = 0
    skip = 0
    
    # Statistics tracking
    processing_stats = {
        'perfect_fit': 0,
        'minimal_crop': 0,
        'distortion_method': 0,
        'fallback': 0,
        'scaled_up': 0,
        'scaled_down': 0,
        'no_scaling': 0,
        'vertical_crops': 0,
        'horizontal_crops': 0,
        'balanced_crops': 0,
        'no_crops': 0
    }
    
    detailed_results = []
    
    print(f"Found {total} videos.")
    print(f"Target: {target_w}x{target_h}, Max crop tolerance: {CROP_TOLERANCE*100}%")
    print(f"Rotation: {'ON' if ROTATE else 'OFF'} ({ROTATE_DIR if ROTATE else 'N/A'})")
    print("")
    
    for v in vids:
        filename = os.path.basename(v)
        print(f"Processing: {filename}")
        success, report = process_video(v)
        
        if success and report:
            done += 1
            
            # Update statistics
            processing_stats[report['strategy']] += 1
            
            if 'scaled up' in report['scaling']:
                processing_stats['scaled_up'] += 1
            elif 'scaled down' in report['scaling']:
                processing_stats['scaled_down'] += 1
            elif 'none' in report['scaling']:
                processing_stats['no_scaling'] += 1
            
            crop_type = report['crop_type']
            if crop_type == 'none':
                processing_stats['no_crops'] += 1
            elif crop_type == 'vertical':
                processing_stats['vertical_crops'] += 1
            elif crop_type == 'horizontal':
                processing_stats['horizontal_crops'] += 1
            elif crop_type == 'balanced':
                processing_stats['balanced_crops'] += 1
            
            # Store detailed result
            detailed_results.append({
                'filename': filename,
                'strategy': report['strategy'],
                'scaling': report['scaling'],
                'crop_type': report['crop_type'],
                'crop_percent': report['crop_percent'],
                'description': report['description']
            })
            
            # Print transformation summary
            print(f"  📊 RESULT: {report['scaling']}")
            if report['crop_type'] != 'none':
                print(f"  ✂️  CROP: {report['crop_type']} crop ({report['crop_percent']:.1f}%)")
            else:
                print(f"  ✅ CROP: No cropping needed")
                
        elif success:
            done += 1
        else:
            skip += 1
        print("")
    
    print("=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total processed: {done}/{total} videos")
    print(f"Skipped/Failed: {skip}")
    print("")
    
    print("STRATEGY BREAKDOWN:")
    print(f"  Perfect fit (no crop): {processing_stats['perfect_fit']}")
    print(f"  Minimal crop (≤{CROP_TOLERANCE*100}%): {processing_stats['minimal_crop']}")
    print(f"  Distortion method (>{CROP_TOLERANCE*100}%): {processing_stats['distortion_method']}")
    print(f"  Fallback (probe failed): {processing_stats['fallback']}")
    print("")
    
    print("SCALING BREAKDOWN:")
    print(f"  Scaled up: {processing_stats['scaled_up']}")
    print(f"  Scaled down: {processing_stats['scaled_down']}")
    print(f"  No scaling: {processing_stats['no_scaling']}")
    print("")
    
    print("CROP TYPE BREAKDOWN:")
    print(f"  No cropping: {processing_stats['no_crops']}")
    print(f"  Vertical crops: {processing_stats['vertical_crops']}")
    print(f"  Horizontal crops: {processing_stats['horizontal_crops']}")
    print(f"  Balanced crops: {processing_stats['balanced_crops']}")
    print("")
    
    # Show detailed results for each video
    if detailed_results:
        print("DETAILED RESULTS:")
        print("-" * 60)
        for result in detailed_results:
            print(f"📁 {result['filename']}")
            print(f"   Strategy: {result['strategy'].replace('_', ' ').title()}")
            print(f"   Scaling: {result['scaling']}")
            print(f"   Cropping: {result['crop_type']} ({result['crop_percent']:.1f}%)" if result['crop_type'] != 'none' else "   Cropping: None")
            print(f"   Transform: {result['description']}")
            print("")
    
    print(f"🎉 Finished: {done} processed, {skip} skipped/failed.")

if __name__ == '__main__':
    main()