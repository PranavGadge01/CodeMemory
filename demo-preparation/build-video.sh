#!/bin/bash
# CodeMemory Demo Video Compilation Script
# Creates a polished 1920x1080 demo video from captured screenshots

# All paths are relative to the repo root
RECORDINGS="C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation/recordings"

# Function to create a pan/zoom clip from a screenshot
# Args: input.png output.mp4 duration zoom_level start_x start_y end_x end_y
create_pan_clip() {
    local input="$1"
    local output="$2"
    local duration="$3"
    local zoom="$4"
    local start_x="$5"
    local start_y="$6"
    local end_x="$7"
    local end_y="$8"
    
    ffmpeg -y -loop 1 -framerate 30 -i "$input" -vf "
        scale=3840:2160,
        zoompan=z='if(lte(in,0.1),$zoom,$zoom)':d=1:fps=30:x='$start_x':y='$start_y',
        fps=30,
        scale=1920:1080,
        format=yuv420p
    " -t "$duration" -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "$output" < /dev/null 2>&1
}

# Let's use a simpler approach - create individual clips with zoompan
echo "Creating intro..."
ffmpeg -y -f lavfi -i "color=c=#07080A:s=1920x1080:d=3:r=30" -vf "
drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='CodeMemory':fontsize=80:fontcolor=#FFA116:x=(w-text_w)/2:y=(h-text_h)/2-50:alpha='if(lt(t,1),0,if(gt(t,2.5),1,pow((t-1)/1,2)))',
drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Your coding history, remembered.':fontsize=28:fontcolor=#e4e4ed:x=(w-text_w)/2:y=(h-text_h)/2+50:alpha='if(lt(t,1.2),0,if(gt(t,2.5),1,pow((t-1.2)/1.3,2)))'
" -c:v libx264 -pix_fmt yuv420p -preset ultrafast "$RECORDINGS/intro.mp4" 2>&1 | tail -1

echo "Creating hero section clip (5s with zoom)..."
ffmpeg -y -loop 1 -framerate 30 -i "$RECORDINGS/section-hero.png" -vf "
    zoompan=z='min(zoom+0.005,1.2)':d=1:fps=30:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',
    fps=30,
    scale=1920:1080,
    format=yuv420p
" -t 5 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "$RECORDINGS/hero-clip.mp4" 2>&1 | tail -1

echo "Creating memory trace section..."
ffmpeg -y -loop 1 -framerate 30 -i "$RECORDINGS/section-memory-trace.png" -vf "
    zoompan=z='min(zoom+0.003,1.1)':d=1:fps=30:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',
    fps=30,
    scale=1920:1080,
    format=yuv420p
" -t 4 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "$RECORDINGS/memory-trace-clip.mp4" 2>&1 | tail -1

echo "Creating solution evolution section..."
ffmpeg -y -loop 1 -framerate 30 -i "$RECORDINGS/section-solution-evolution.png" -vf "
    zoompan=z='min(zoom+0.002,1.08)':d=1:fps=30:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',
    fps=30,
    scale=1920:1080,
    format=yuv420p
" -t 5 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "$RECORDINGS/evolution-clip.mp4" 2>&1 | tail -1

echo "Creating analytics section..."
ffmpeg -y -loop 1 -framerate 30 -i "$RECORDINGS/section-analytics.png" -vf "
    fps=30,
    scale=1920:1080,
    format=yuv420p
" -t 4 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "$RECORDINGS/analytics-clip.mp4" 2>&1 | tail -1

echo "Creating knowledge graph section..."
ffmpeg -y -loop 1 -framerate 30 -i "$RECORDINGS/section-knowledge.png" -vf "
    zoompan=z='min(zoom+0.004,1.15)':d=1:fps=30:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',
    fps=30,
    scale=1920:1080,
    format=yuv420p
" -t 4 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "$RECORDINGS/knowledge-clip.mp4" 2>&1 | tail -1

echo "Creating revision section..."
ffmpeg -y -loop 1 -framerate 30 -i "$RECORDINGS/section-revision.png" -vf "
    fps=30,
    scale=1920:1080,
    format=yuv420p
" -t 4 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "$RECORDINGS/revision-clip.mp4" 2>&1 | tail -1

echo "Creating CTA section..."
ffmpeg -y -loop 1 -framerate 30 -i "$RECORDINGS/section-cta.png" -vf "
    fps=30,
    scale=1920:1080,
    format=yuv420p,
    fade=in:0:15
" -t 4 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "$RECORDINGS/cta-clip.mp4" 2>&1 | tail -1

echo "All clips created!"