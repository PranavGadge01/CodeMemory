@echo off
setlocal

set R=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recordings

ffmpeg -y ^
  -i "%R%\intro-final.mp4" ^
  -i "%R%\hero-titled.mp4" ^
  -i "%R%\memory-trace-clip.mp4" ^
  -i "%R%\evolution-clip.mp4" ^
  -i "%R%\analytics-clip.mp4" ^
  -i "%R%\knowledge-clip.mp4" ^
  -i "%R%\revision-clip.mp4" ^
  -i "%R%\cta-clip.mp4" ^
  -i "%R%\outro-final.mp4" ^
  -filter_complex ^
  "[0:v]format=yuv420p[f0];" ^
  "[1:v]format=yuv420p[f1];" ^
  "[2:v]format=yuv420p[f2];" ^
  "[3:v]format=yuv420p[f3];" ^
  "[4:v]format=yuv420p[f4];" ^
  "[5:v]format=yuv420p[f5];" ^
  "[6:v]format=yuv420p[f6];" ^
  "[7:v]format=yuv420p[f7];" ^
  "[8:v]format=yuv420p[f8];" ^
  "[f0][f1]xfade=transition=fade:duration=0.5:offset=2.5[f01];" ^
  "[f01][f2]xfade=transition=fade:duration=0.5:offset=7.0[f02];" ^
  "[f02][f3]xfade=transition=fade:duration=0.5:offset=11.0[f03];" ^
  "[f03][f4]xfade=transition=fade:duration=0.5:offset=15.5[f04];" ^
  "[f04][f5]xfade=transition=fade:duration=0.5:offset=19.0[f05];" ^
  "[f05][f6]xfade=transition=fade:duration=0.5:offset=23.0[f06];" ^
  "[f06][f7]xfade=transition=fade:duration=0.5:offset=26.5[f07];" ^
  "[f07][f8]xfade=transition=fade:duration=0.5:offset=29.5[v]" ^
  -map "[v]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4" 2>&1

ffprobe -v error -show_entries format=duration -show_entries stream=width,height -of csv "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4"
dir "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4" | findstr "bytes"

endlocal