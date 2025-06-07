# Raspberry Pi Video Encoder Suite

## 🎯 Purpose
These scripts automatically convert videos to Raspberry Pi-optimized formats, solving:
- Choppy playback on Pi Zero
- Incorrect aspect ratios on small screens
- Long conversion times with manual tools

---

## 🌟 Features
- **One-click processing** of entire video collections
- **Smart detection** of screen types
- **Progress tracking** with time estimates
- **Preset quality** optimized for Pi hardware

---

## 📦 Requirements

```bash
# Required: FFmpeg
# Linux:
sudo apt install ffmpeg
# Mac:
brew install ffmpeg
# Windows: Download from ffmpeg.org
# Python 3 (usually pre-installed)
```

---

## 🛠 Setup
Create these folders:

1. Create these folders directly on your desktop:
```text
~/Desktop/
├── input/   # Put source videos here
└── output/  # Processed files appear here
```
2. Place videos in `input/` (supports MP4, MKV, MOV, AVI)
3. You can always change the input and output folders directly in the code

---

## 🚀 Usage Instructions

### For Normal Displays (TVs/Monitors)

```bash
python3 video-converter_800x480.py
```
What it does:
- Converts to 480p height
- Maintains original aspect ratio
- Optimized for HDMI output

### For Small Screens (2.8"-4")

```bash
python3 video-converter_480x320.py
```
What it does:
- Fixed 480×320 output
- Adds black bars to maintain proportions
- Perfect for Pi touchscreens

---

## 🔍 What Happens During Processing
Script scans `input/` folder
Skips already processed files
Shows real-time progress:

```text
[PROCESS 3/10] 'my_video.mp4'
  Input: /input/my_video.mp4
  Output: /output/my_video.mp4
  Encoding time: 00:01:23
  Progress: 30% (3/10)
```
Saves results in `output/`

---

## ⏱️ Sample Processing Times

| Video | Small Screen | Standard 480p |
| :---- | :----------- | :------------ |
| 5min  | ~1min        | ~1.5min       |
| 30min | ~6min        | ~9min         |
| 2hr   | ~25min       | ~35min        |

---

## 🛑 Troubleshooting

**Q: Script won't start?**
A: Check FFmpeg is installed (`ffmpeg -version`)

**Q: Videos look distorted?**
A: Try the other script version

**Q: Processing seems slow?**
A: Close other programs during encoding

---

## 💡 Pro Tips

**File Names:** Use simple names (no spaces/special chars)
**Batch Processing:** Works with 1000+ videos automatically
**Quality Adjustment:** Edit the scripts to change CRF values:
- Lower number = better quality (try 18)
- Higher number = smaller files (try 26)

---

## 📜 Script Comparison Table

| Feature          | Standard Version | Small Screen Version |
| :--------------- | :--------------- | :------------------- |
| Resolution       | 480p height      | 480×320              |
| Best For         | TVs/Projectors   | Integrated displays  |
| File Size        | Medium           | Smaller              |
| Pi Zero Performance | Good             | Excellent            |

---

## 📌 Final Notes
Always back up originals before processing
Scripts create new files (never overwrite originals)
For help: Open an issue on the GitHub repository or reach out to @QC20

---

## 📄 License
This project is licensed under the MIT License - see the `LICENSE` file (if you choose to add one) for details.