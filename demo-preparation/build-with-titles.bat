@echo off
setlocal

set R=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recordings

REM Add section titles as overlays

ffmpeg -y -i "%R%\intro-smooth.mp4" -vf "drawbox=x=0:y=0:w=1920:h=80:color=#07080A@0.7:t=fill" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\t0.mp4" 2>nul

ffmpeg -y -i "%R%\c1.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Landing Page':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\t1.mp4" 2>nul

ffmpeg -y -i "%R%\c2.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Every attempt is preserved':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\t2.mp4" 2>nul

ffmpeg -y -i "%R%\c3.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Solution Evolution':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\t3.mp4" 2>nul

ffmpeg -y -i "%R%\c4.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Analytics':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\t4.mp4" 2>nul

ffmpeg -y -i "%R%\c5.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Knowledge Graph':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\t5.mp4" 2>nul

ffmpeg -y -i "%R%\c6.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Revision Queue':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\t6.mp4" 2>nul

ffmpeg -y -i "%R%\c7.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Get Started':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\t7.mp4" 2>nul

ffmpeg -y -i "%R%\outro-smooth.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Import your submissions. CodeMemory indexes them, connects them, and remembers the parts worth revisiting.':fontcolor=#e4e4ed:fontsize=20:x=(w-text_w)/2:y=h/2+80:box=1:boxcolor=#07080A80:boxborderw=30" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\t8.mp4" 2>nul

echo file 't0.mp4'> "%R%\concat-titled.txt"
echo file 't1.mp4'>> "%R%\concat-titled.txt"
echo file 't2.mp4'>> "%R%\concat-titled.txt"
echo file 't3.mp4'>> "%R%\concat-titled.txt"
echo file 't4.mp4'>> "%R%\concat-titled.txt"
echo file 't5.mp4'>> "%R%\concat-titled.txt"
echo file 't6.mp4'>> "%R%\concat-titled.txt"
echo file 't7.mp4'>> "%R%\concat-titled.txt"
echo file 't8.mp4'>> "%R%\concat-titled.txt"

ffmpeg -y -f concat -safe 0 -i "%R%\concat-titled.txt" -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4" 2>nul

ffprobe -v error -show_entries format=duration -show_entries stream=width,height,nb_frames -of csv "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4"
dir "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4" | findstr "bytes"

endlocal