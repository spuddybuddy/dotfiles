#!/bin/bash
set -x
ffmpeg -y -i "$1.mp4" -c:v libx264 -preset medium -profile:v baseline -level 3.0 -b:v $2 -pass 1 -c:a libmp3lame -b:a 128k -f mp4 /dev/null && \
ffmpeg -i "$1.mp4" -c:v libx264 -preset medium -profile:v baseline -level 3.0 -b:v $2 -pass 2 -c:a libmp3lame -b:a 128k "$1-xcode.mp4"
