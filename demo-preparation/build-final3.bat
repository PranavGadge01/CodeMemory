@echo off
set R=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recordings

ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-hero.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.0015,1.3)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 4 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c1.mp4" 2>nul

ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-memory-trace.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.001,1.2)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 3 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c2.mp4" 2>nul

ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-solution-evolution.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.001,1.15)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 4 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c3.mp4" 2>nul

ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-analytics.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.001,1.1)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 3 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c4.mp4" 2>nul

ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-knowledge.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.0015,1.25)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 3 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c5.mp4" 2>nul

ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-revision.png" -vf "scale=2560:1440,zoompan=z='min(zoom+0.001,1.1)':d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':fps=30,scale=1920:1080,format=yuv420p" -t 3 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c6.mp4" 2>nul

ffmpeg -y -loop 1 -framerate 30 -i "%R%\section-cta.png" -vf "fps=30,scale=1920:1080,format=yuv420p" -t 3 -c:v libx264 -crf 21 -pix_fmt yuv420p "%R%\c7.mp4" 2>nul

echo file 'intro-smooth.mp4'> "%R%\concat-full.txt"
echo file 'c1.mp4'>> "%R%\concat-full.txt"
echo file 'c2.mp4'>> "%R%\concat-full.txt"
echo file 'c3.mp4'>> "%R%\concat-full.txt"
echo file 'c4.mp4'>> "%R%\concat-full.txt"
echo file 'c5.mp4'>> "%R%\concat-full.txt"
echo file 'c6.mp4'>> "%R%\concat-full.txt"
echo file 'c7.mp4'>> "%R%\concat-full.txt"
echo file 'outro-smooth.mp4'>> "%R%\concat-full.txt"

ffmpeg -y -f concat -safe 0 -i "%R%\concat-full.txt" -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4" 2>nul

ffprobe -v error -show_entries format=duration -show_entries stream=width,height,nb_frames -of csv "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4"
dir "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4" | findstr "bytes"