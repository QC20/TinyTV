import os
from pathlib import Path

def find_mp4_files():
    # Get the directory where the script is located
    script_dir = Path(__file__).parent.resolve()
    
    # Output file path
    output_file = script_dir / "list_files.txt"
    
    # List to store all MP4 files with their paths
    mp4_files = []
    
    # Walk through all directories and subdirectories
    for root, dirs, files in os.walk(script_dir):
        # Get relative path from script directory
        rel_path = Path(root).relative_to(script_dir)
        
        # Find all MP4 files in current directory
        mp4_in_dir = [f for f in files if f.lower().endswith('.mp4')]
        
        if mp4_in_dir:
            # Add folder path
            if str(rel_path) == '.':
                folder_name = "."
            else:
                folder_name = str(rel_path)
            
            mp4_files.append(f"\n{folder_name}")
            
            # Add all MP4 files in this folder
            for mp4_file in sorted(mp4_in_dir):
                mp4_files.append(f"{mp4_file}")
    
    # Write to text file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            if mp4_files:
                f.write("\n".join(mp4_files))
            else:
                f.write("No MP4 files found.")
        
        # Verify file was created
        if output_file.exists():
            print(f"✓ Scan complete!")
            print(f"✓ File created successfully: {output_file}")
            print(f"✓ File size: {output_file.stat().st_size} bytes")
            mp4_count = sum(1 for line in mp4_files if line and not line.startswith('\n') and '\\' not in line and '/' not in line)
            print(f"✓ Found {mp4_count} MP4 files")
        else:
            print(f"✗ ERROR: File was not created at {output_file}")
    
    except Exception as e:
        print(f"✗ ERROR writing file: {e}")
        print(f"✗ Attempted to write to: {output_file}")

if __name__ == "__main__":
    find_mp4_files()