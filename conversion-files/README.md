# Raspberry Pi Video Encoder Suite

A collection of FFmpeg-based video conversion tools optimized for Raspberry Pi displays, with comprehensive support for the Waveshare 4" 480×800 IPS touchscreen and other common Pi screen configurations.

## Overview

These scripts solve common video playback issues on Raspberry Pi systems by automatically converting videos to hardware-optimized formats. The suite addresses choppy playback, incorrect aspect ratios, and provides intelligent processing features including black bar removal, subtitle burning, and adaptive scaling.

**Primary Tool: TinyTV_Converter.py**  
The flagship script designed specifically for the Waveshare 4" 480×800 resistive touch IPS display. This is the recommended starting point for most users.

## Supported Hardware

### Primary Target: Waveshare 4" Display
- **Model**: 480×800, 4" Resistive Touch Screen IPS LCD (Type H)
- **Interface**: HDMI with touch panel I/O
- **Features**: 3.5mm audio jack, adjustable backlight
- **Compatibility**: All Raspberry Pi models with HDMI (Pi 1 Model B and Pi Zero require HDMI cable)

### Alternative Configurations
The suite includes converters for other common screen types and resolutions used in Pi projects.

## Requirements

### FFmpeg Installation

**Linux/Raspberry Pi:**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**  
Download from [ffmpeg.org](https://ffmpeg.org)

**Python 3** (typically pre-installed on Raspberry Pi)

## Setup

Create input and output directories on your desktop:

```
~/Desktop/
├── c_input/   # Place source videos here
└── output/    # Converted files appear here
```

The default paths can be modified directly in the script configuration section.

## TinyTV_Converter.py Features

### Intelligent Scaling System
The converter employs an adaptive scaling algorithm that:
- Targets 770-800px width with 480px height (prefers 780px to account for screen bezels)
- Minimizes geometric distortion while staying within 15% stretch/squeeze limits
- Automatically detects optimal dimensions based on source aspect ratio
- Applies smart cropping only when necessary

### Black Bar Detection and Removal
- Samples video at multiple points (10%, 50%, 90%) to detect letterboxing
- Removes black bars automatically when they exceed 2% of frame size
- Preserves content while maximizing usable screen area

### Subtitle Support
- Automatically detects and burns-in matching .srt subtitle files
- Optimized font rendering for 4" displays (18px Arial with 2px outline)
- Subtitles rotate correctly with video orientation

### Video Rotation
- Configurable 90-degree rotation (clockwise or counterclockwise)
- Useful for portrait-oriented content on landscape displays
- Subtitle text rotates with video content

### Performance Optimization
- Configurable CPU thread allocation
- Real-time progress tracking with percentage and time estimates
- Batch processing with automatic skip of existing outputs
- Uses H.264 Main profile with optimized encoding settings

### Processing Output
```
(1/10)
Analyzing 'sample_video'...
  Original dimensions: 1920x1080
  Duration: 00:05:23
  Found subtitle file: sample_video.srt
  Detecting black bars (sampling 10s)...
  Black bars detected! Original: 1920x1080, After crop: 1920x800
  Optimal target dimensions: 780x480
  Burning in subtitles: sample_video.srt
    Font: Arial, Size: 18px
  Applying rotation: counterclockwise
Encoding 'sample_video' with filters: crop=1920:800:0:140,scale=780:480,...
  Progress: [====================] 100.00% (00:05:23 / 00:05:23)
 -> Done in 142.3s, size=8472 KB
```

## Configuration

Key parameters in `TinyTV_Converter.py`:

```python
# Target dimensions
TARGET_HEIGHT = 480
TARGET_WIDTH_PREFERRED = 780
TARGET_WIDTH_MIN = 770
TARGET_WIDTH_MAX = 800

# Rotation
ROTATE = True
ROTATE_DIR = 'counterclockwise'

# Scaling limits
MAX_STRETCH = 1.15
MIN_SQUEEZE = 0.85

# Subtitle settings
SUBTITLE_FONT_SIZE = 18
SUBTITLE_FONT_NAME = 'Arial'
SUBTITLE_OUTLINE = 2

# CPU threads
MAX_CPU_THREADS = multiprocessing.cpu_count() // 2
```

## Usage

### For Waveshare 4" Display (Primary)

```bash
python3 TinyTV_Converter.py
```

This processes all videos in `c_input/` with:
- Automatic black bar removal
- Subtitle burning (if .srt files present)
- Intelligent scaling to 780×480 (optimal for 800×480 display with bezels)
- Optional 90-degree rotation
- Progress tracking and estimates

### Alternative Converters

**For standard displays (TVs/monitors):**
```bash
python3 video-converter_800x480.py
```
- Maintains aspect ratio
- Scales to 480p height
- HDMI output optimized

**For small embedded screens (2.8"-3.5"):**
```bash
python3 video-converter_480x320.py
```
- Fixed 480×320 output
- Adds letterboxing to maintain proportions

**For 750×480 displays:**
```bash
python3 video-converter_750x480.py
```
- Specialized for slightly narrower screens
- Handles rotation and aspect ratio forcing

## Processing Performance

Approximate conversion times on modern hardware:

| Video Length | TinyTV_Converter | Standard 480p |
|:-------------|:-----------------|:--------------|
| 5 minutes    | 1-2 minutes     | 1.5 minutes  |
| 30 minutes   | 6-8 minutes     | 9 minutes    |
| 2 hours      | 25-30 minutes   | 35 minutes   |

Performance scales with CPU thread allocation and encoding preset settings.

## Technical Details

### Encoding Specifications (TinyTV_Converter)
- **Video Codec**: H.264 (libx264)
- **Profile**: Main (Level 3.0)
- **Preset**: veryslow (maximum quality)
- **CRF**: 23 (balanced quality/size)
- **Audio Codec**: AAC at 256kbps
- **Pixel Format**: yuv420p
- **Container**: MP4 with faststart flag

### Filter Chain Processing Order
1. Black bar cropping (if detected)
2. Initial scaling to target dimensions
3. Aspect ratio correction (minimal distortion)
4. Subtitle rendering (if .srt available)
5. Rotation (if enabled)
6. Final dimension adjustment

## Troubleshooting

**FFmpeg not found:**  
Verify installation with `ffmpeg -version`

**Videos appear distorted:**  
Adjust `MAX_STRETCH` and `MIN_SQUEEZE` parameters to tighten scaling limits

**Slow processing:**  
Increase `MAX_CPU_THREADS` or change preset from 'veryslow' to 'medium' or 'fast'

**Subtitles too small/large:**  
Modify `SUBTITLE_FONT_SIZE` parameter

**Wrong rotation direction:**  
Change `ROTATE_DIR` from 'counterclockwise' to 'clockwise'

## Best Practices

- Use descriptive filenames without special characters or spaces
- Place matching .srt files in the same directory with identical base names
- Maintain original files as backups (scripts never overwrite sources)
- Process test videos first to verify settings match your display
- For quality adjustments, modify CRF values (18=higher quality, 26=smaller files)

## Quality Tuning

Edit the CRF value in the encoding command to adjust quality/size tradeoff:

- **CRF 18**: High quality, larger files (near-lossless)
- **CRF 23**: Balanced (default)
- **CRF 26**: Smaller files, acceptable quality

Change encoding preset for speed vs. quality:

- **veryslow**: Maximum quality (default)
- **slow**: Good balance
- **medium/fast**: Faster encoding, slightly lower quality

## License

This project is licensed under the MIT License.

## Author

Jonas, December 2025 