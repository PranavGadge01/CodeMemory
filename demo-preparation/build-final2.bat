@echo off
setlocal

set R=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recordings
set OUTPUT=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4

REM The intro was already created successfully in previous step
REM Let's just create the section clips with zoom and combine

REM Hero section with zoom-in (4 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-hero.png" -vf "fps=30,zoompan=z='min(zoom+0.0015,1.15)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',scale=1920:1080,format=yuv420p" -t 4 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c1.mp4" 2>nul

REM Memory trace section (3 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-memory-trace.png" -vf "fps=30,zoompan=z='min(zoom+0.001,1.12)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',scale=1920:1080,format=yuv420p" -t 3 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c2.mp4" 2>nul

REM Solution evolution section with slight zoom (4 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-solution-evolution.png" -vf "fps=30,zoompan=z='min(zoom+0.001,1.1)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',scale=1920:1080,format=yuv420p" -t 4 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c3.mp4" 2>nul

REM Analytics section (3 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-analytics.png" -vf "fps=30,zoompan=z='min(zoom+0.001,1.1)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',scale=1920:1080,format=yuv420p" -t 3 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c4.mp4" 2>nul

REM Knowledge graph section with slight zoom (3 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-knowledge.png" -vf "fps=30,zoompan=z='min(zoom+0.0015,1.15)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',scale=1920:1080,format=yuv420p" -t 3 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c5.mp4" 2>nul

REM Revision section (3 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-revision.png" -vf "fps=30,zoompan=z='min(zoom+0.001,1.1)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',scale=1920:1080,format=yuv420p" -t 3 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c6.mp4" 2>nul

REM CTA section (3 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-cta.png" -vf "fps=30,scale=1920:1080,format=yuv420p" -t 3 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c7.mp4" 2>nul

REM Create concat list
echo file 'intro-smooth.mp4'> "%R%\concat-full.txt"
echo file 'c1.mp4'>> "%R%\concat-full.txt"
echo file 'c2.mp4'>> "%R%\concat-full.txt"
echo file 'c3.mp4'>> "%R%\concat-full.txt"
echo file 'c4.mp4'>> "%R%\concat-full.txt"
echo file 'c5.mp4'>> "%R%\concat-full.txt"
echo file 'c6.mp4'>> "%R%\concat-full.txt"
echo file 'c7.mp4'>> "%R%\concat-full.txt"
echo file 'outro-smooth.mp4'>> "%R%\concat-full.txt"

REM Concatenate with re-encode for smooth playback
ffmpeg -y -f concat -safe 0 -i "%R%\concat-full.txt" -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p "%OUTPUT%" 2>nul

ffprobe -v error -show_entries format=duration -show_entries stream=width,height,nb_frames -of csv "%OUTPUT%"
dir "%OUTPUT%" | findstr "bytes"

endlocal