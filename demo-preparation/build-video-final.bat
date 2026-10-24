@echo off
set R=C:\tmp\cm-video

REM Step 1: Add fade in/out to each clip
ffmpeg -y -i "%R%\intro-final.mp4" -vf "format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st=2.5:d=0.5" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\faded-intro.mp4" 2>nul
ffmpeg -y -i "%R%\hero-titled.mp4" -vf "format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st=4.5:d=0.5" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\faded-hero.mp4" 2>nul
ffmpeg -y -i "%R%\memory-trace-clip.mp4" -vf "format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st=3.5:d=0.5" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\faded-memory.mp4" 2>nul
ffmpeg -y -i "%R%\evolution-clip.mp4" -vf "format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st=4.5:d=0.5" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\faded-evolution.mp4" 2>nul
ffmpeg -y -i "%R%\analytics-clip.mp4" -vf "format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st=3.5:d=0.5" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\faded-analytics.mp4" 2>nul
ffmpeg -y -i "%R%\knowledge-clip.mp4" -vf "format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st=3.5:d=0.5" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\faded-knowledge.mp4" 2>nul
ffmpeg -y -i "%R%\revision-clip.mp4" -vf "format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st=3.5:d=0.5" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\faded-revision.mp4" 2>nul
ffmpeg -y -i "%R%\cta-clip.mp4" -vf "format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st=2.5:d=0.5" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\faded-cta.mp4" 2>nul
ffmpeg -y -i "%R%\outro-final.mp4" -vf "format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st=2.5:d=0.5" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\faded-outro.mp4" 2>nul

REM Step 2: Create concat list
echo file 'faded-intro.mp4'> "%R%\concat-faded.txt"
echo file 'faded-hero.mp4'>> "%R%\concat-faded.txt"
echo file 'faded-memory.mp4'>> "%R%\concat-faded.txt"
echo file 'faded-evolution.mp4'>> "%R%\concat-faded.txt"
echo file 'faded-analytics.mp4'>> "%R%\concat-faded.txt"
echo file 'faded-knowledge.mp4'>> "%R%\concat-faded.txt"
echo file 'faded-revision.mp4'>> "%R%\concat-faded.txt"
echo file 'faded-cta.mp4'>> "%R%\concat-faded.txt"
echo file 'faded-outro.mp4'>> "%R%\concat-faded.txt"

REM Step 3: Concatenate with re-encoding for smooth playback
ffmpeg -y -f concat -safe 0 -i "%R%\concat-faded.txt" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4" 2>&1 | findstr /v "Input\|Output\|Stream\|Duration\|Metadata\|handler\|vendor\|^$"

ffprobe -v error -show_entries format=duration -show_entries stream=width,height,nb_frames -of csv "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4"