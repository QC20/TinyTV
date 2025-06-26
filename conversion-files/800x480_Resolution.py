import os
import subprocess
import time

# Configuration
DESKTOP = os.path.expanduser('~/Desktop')
INPUT_DIR = os.path.join(DESKTOP, 'input')
OUTPUT_DIR = os.path.join(DESKTOP, 'output')

ROTATE = True                        # Rotate 90 degrees or not
ROTATE_DIR = 'counterclockwise'     # 'clockwise' or 'counterclockwise'

target_w = 800
target_h = 480
VERT_DISTORT = 1.05  # vertical stretch factor (~5%)

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
    return path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv', '.webm'))

def find_videos(directory):
    videos = []
    for root, _, files in os.walk(directory):
        for f in files:
            if is_video_file(f):
                videos.append(os.path.join(root, f))
    return sorted(videos, key=lambda p: os.path.basename(p).lower())

def build_filter():
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
        return False

    vf = build_filter()
cmd = [
    'ffmpeg', '-i', input_path,
    '-vf', vf,
    '-c:v', 'libx264', '-profile:v', 'baseline', '-level', '3.0',
    '-preset', 'veryslow', '-crf', '26',
    '-c:a', 'aac', '-b:a', '96k',
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
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error encoding '{base}': {e}")
        return False

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    vids = find_videos(INPUT_DIR)
    total = len(vids)
    done = 0
    skip = 0

    print(f"Found {total} videos. Applying vertical stretch {VERT_DISTORT*100-100:.1f}%, balanced cropping.")
    for v in vids:
        if process_video(v):
            done += 1
        else:
            skip += 1

    print(f"Finished: {done} processed, {skip} skipped/failed.")

if __name__ == '__main__':
    main()
