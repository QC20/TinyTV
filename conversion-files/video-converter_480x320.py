import os
import time

# Get the path to the desktop
desktop_path = os.path.expanduser("~/Desktop")

# Set input and output directories
input_directory = os.path.join(desktop_path, 'input')
destination_directory = os.path.join(desktop_path, 'output')

# Create output directory if it doesn't exist
if not os.path.exists(destination_directory):
    os.makedirs(destination_directory)

def isVideo(videofile):
    video_extensions = ('.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv', '.webm')
    return videofile.lower().endswith(video_extensions)

def get_sorted_video_files(directory):
    video_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if isVideo(file):
                video_files.append(os.path.join(root, file))
    return sorted(video_files, key=lambda x: os.path.basename(x).lower())

def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def check_existing_output(input_path, output_dir):
    """Check if output file already exists and return its path if it does"""
    filename = os.path.basename(input_path)
    name_without_ext = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{name_without_ext}.mp4")
    return output_path if os.path.exists(output_path) else None

# Get sorted list of video files
video_files = get_sorted_video_files(input_directory)
total_files = len(video_files)
processed_files = 0
skipped_files = 0

print(f"Found {total_files} video files to process in '{input_directory}'")
print(f"Output will be saved to: {destination_directory}")
print("Encoding specs: 480p height, H.264 baseline (Pi-optimized)")
print("Processing files in alphabetical order...\n")

for input_file in video_files:
    start_time = time.time()
    filename = os.path.basename(input_file)
    existing_output = check_existing_output(input_file, destination_directory)
    
    if existing_output:
        skipped_files += 1
        print(f"[SKIP {skipped_files}/{total_files}] '{filename}'")
        print(f"  Reason: Output already exists at {existing_output}")
        print("-" * 60)
        continue
    
    # Prepare output path
    name_without_ext = os.path.splitext(filename)[0]
    output_file = os.path.join(destination_directory, f"{name_without_ext}.mp4")
    
    print(f"[PROCESS {processed_files+1}/{total_files}] '{filename}'")
    print(f"  Input: {input_file}")
    print(f"  Output: {output_file}")
    
    # Original 480p encoding command (Pi Zero optimized)
    encode_command = (
        f'ffmpeg -i "{input_file}" '
        f'-vf "scale=-2:480" '  # Original 480p height, maintain aspect
        f'-c:v libx264 -profile:v baseline -level 3.0 '
        f'-preset fast -crf 23 '  # Original quality setting
        f'-pix_fmt yuv420p -movflags +faststart '
        f'"{output_file}"'
    )
    
    # Execute the command
    try:
        encode_start = time.time()
        print("  Starting encoding...")
        encode = os.popen(encode_command).read()
        encode_time = time.time() - encode_start
        
        processed_files += 1
        elapsed_time = time.time() - start_time
        
        print(f"  [DONE] Encoded successfully in {format_time(encode_time)}")
        print(f"  Final size: {os.path.getsize(output_file)//1024} KB")
        
        # Progress reporting
        progress = (processed_files / total_files) * 100
        remaining_files = total_files - processed_files - skipped_files
        avg_time = elapsed_time / processed_files if processed_files > 0 else 0
        estimated_remaining = avg_time * remaining_files
        
        print(f"  Progress: {progress:.1f}% | Remaining: {remaining_files} files")
        print(f"  Estimated completion in: {format_time(estimated_remaining)}")
        print("-" * 60)
        
    except Exception as e:
        print(f"  [ERROR] Failed to encode: {str(e)}")
        continue

print("\nProcessing complete!")
print(f"Summary:")
print(f"  Total files: {total_files}")
print(f"  Processed: {processed_files}")
print(f"  Skipped (already existed): {skipped_files}")
print(f"  Failed: {total_files - processed_files - skipped_files}")
print(f"\nOutput files available in: {destination_directory}")