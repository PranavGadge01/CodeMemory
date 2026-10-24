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
  -filter_complex "[0:v]format=yuv420p,fade=t=out:st=2.3:d=0.4[a0];[1:v]format=yuv420p,fade=t=in:st=0:d=0.4,fade=t=out:st=4.3:d=0.4[a1];[2:v]format=yuv420p,fade=t=in:st=0:d=0.4[a2];[3:v]format=yuv420p,fade=t=in:st=0:d=0.4,fade=t=out:st=4.3:d=0.4[a3];[4:v]format=yuv420p,fade=t=in:st=0:d=0.4[a4];[5:v]format=yuv420p,fade=t=in:st=0:d=0.4[a5];[6:v]format=yuv420p,fade=t=in:st=0:d=0.4[a6];[7:v]format=yuv420p,fade=t=in:st=0:d=0.4[a7];[8:v]format=yuv420p,fade=t=in:st=0:d=0.4[a8];[a0][a1]blend=all_expr='A*(1-T/0.4)+B*(T/0.4)',[a1][a2]blend=all_expr='A*(1-T/0.4)+B*(T/0.4)',[a2][a3]blend=all_expr='A*(1-T/0.4)+B*(T/0.4)',[a3][a4]blend=all_expr='A*(1-T/0.4)+B*(T/0.4)'" -map_complex "v" -c:v libx264 -crf 20 -pix_fmt yuv420p "%R%\codememory-demo.mp4" 2>&1 | findstr /v "Input\|Output\|Stream\|Duration\|Metadata\|handler\|vendor\|encoder\|^$"

ffprobe -v error -show_entries format=duration -show_entries stream=width,height -of csv "%R%\codememory-demo.mp4"
dir "%R%\codememory-demo.mp4" | findstr "bytes"

endlocal