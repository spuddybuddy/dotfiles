#!/bin/bash
# These are settings recommended by YouTube for 1080p, 30fps video, e.g. as recorded by my Pixel 6.
# This transcodes the video stream from HEVC to 8Mbps h.264 high profile (using 2-pass mode).
# The audio stream is passthrough as it is already AAC-LC at around 200 kpbs.
set -x
root=$(basename $1 .mp4)
ffmpeg -y -i "$1" -c:v libx264 -preset slow -profile:v high -b:v 8192k -pass 1 -an -f null /dev/null && \
  ffmpeg -i "$1" -c:v libx264 -preset slow -profile:v high -b:v 8192k -pass 2 -c:a copy "$root-xcode.mp4"
