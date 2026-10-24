@echo off
setlocal

set R=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recordings

REM Recreate clips with longer durations for a more substantial demo
REM Total target: ~45-60 seconds

REM Hero section (6 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-hero.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.0015,1.2)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 6 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c1.mp4" 2>nul

REM Memory trace section (5 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-memory-trace.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.001,1.12)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 5 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c2.mp4" 2>nul

REM Solution evolution section (7 seconds) - important for demo
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-solution-evolution.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.001,1.1)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 7 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c3.mp4" 2>nul

REM Analytics section (5 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-analytics.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.001,1.1)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 5 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c4.mp4" 2>nul

REM Knowledge graph section (5 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-knowledge.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.0015,1.25)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 5 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c5.mp4" 2>nul

REM Revision section (4 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-revision.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.001,1.1)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 4 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c6.mp4" 2>nul

REM CTA section (4 seconds)
ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-cta.png" -vf "fps=30,scale=1920:1080,format=yuv420p" -t 4 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c7.mp4" 2>nul

echo file 'intro-smooth.mp4'> "%R%\concat-long.txt"
echo file 'c1.mp4'>> "%R%\concat-long.txt"
echo file 'c2.mp4'>> "%R%\concat-long.txt"
echo file 'c3.mp4'>> "%R%\concat-long.txt"
echo file 'c4.mp4'>> "%R%\concat-long.txt"
echo file 'c5.mp4'>> "%R%\concat-long.txt"
echo file 'c6.mp4'>> "%R%\concat-long.txt"
echo file 'c7.mp4'>> "%R%\concat-long.txt"
echo file 'outro-smooth.mp4'>> "%R%\concat-long.txt"

ffmpeg -y -f concat -safe 0 -i "%R%\concat-long.txt" -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo-novoice.mp4" 2>nul

ffprobe -v error -show_entries format=duration -show_entries stream=width,height,nb_frames -of csv "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo-novoice.mp4"
dir "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo-novoice.mp4" | findstr "bytes"

endlocal