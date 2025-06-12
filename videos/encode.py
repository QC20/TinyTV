# -*- coding: utf-8 -*-
# This script encodes all video files in the current directory to mp4 format
# using ffmpeg, scaling them to a height of 800 pixels while maintaining aspect ratio.
import os

# Ensure ffmpeg is installed and available in the system PATH
newFiles = []
directory = os.path.dirname(os.path.realpath(__file__))
destinationDirectory = os.path.join(directory, 'encoded')

# Ensure the destination directory exists
if not os.path.exists(destinationDirectory):
	os.mkdir(destinationDirectory)

# Function to check if a file is a video file based on its extension
def isVideo(videofile):
	if videofile.lower().endswith('.mp4'):
		return True
	if videofile.lower().endswith('.mkv'):
		return True
	if videofile.lower().endswith('.mov'):
		return True
	if videofile.lower().endswith('.avi'):
		return True
	return False

# Get all video files in the current directory and its subdirectories
newFiles = [os.path.join(dp, f) for dp, dn, filenames in os.walk(directory) for f in filenames if isVideo(f)]

# If no video files are found, exit the script
for filepath in newFiles:
	video = os.path.basename(filepath)
	videoName = os.path.splitext(video)[0]
	newFile = '%s.mp4' % videoName
	i = filepath
	o = os.path.join(destinationDirectory, newFile)
	# Check if the output file already exists
	if os.path.isfile(o):
		continue
	encodeCommand = 'ffmpeg -i "%s" -vf scale=-2:800 -c:v libx264 -profile:v baseline -level 3.0 -preset fast -crf 23 -pix_fmt yuv420p "%s"' % (i, o)
	print('Encoding %s' % newFile)
	encode = os.popen(encodeCommand).read()