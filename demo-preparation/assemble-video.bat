@echo off
setlocal

set R=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recordings

echo Adding title overlays to sections...

REM Add section title to hero clip
ffmpeg -y -i "%R%\hero-clip.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='CodeMemory':fontcolor=#FFA116:fontsize=42:x=80:y=60:box=1:boxcolor=#07080A80:boxborderw=20",drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Your coding history, remembered.':fontcolor=#e4e4ed:fontsize=20:x=80:y=120" -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "%R%\hero-titled.mp4" 2>nul

REM Create filter_complex for concatenation with transitions
REM Using crossfade between clips

echo Assembling final video...

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
  "[0:v]format=yuv420p,fade=d=0.5[s0];" ^
  "[1:v]format=yuv420p,fade=d=0.5[s1];" ^
  "[2:v]format=yuv420p,fade=d=0.5[s2];" ^
  "[3:v]format=yuv420p,fade=d=0.5[s3];" ^
  "[4:v]format=yuv420p,fade=d=0.5[s4];" ^
  "[5:v]format=yuv420p,fade=d=0.5[s5];" ^
  "[6:v]format=yuv420p,fade=d=0.5[s6];" ^
  "[7:v]format=yuv420p,fade=d=0.5[s7];" ^
  "[8:v]format=yuv420p,fade=d=0.5[s8];" ^
  "[s0][s1]xfade=transition=fade:duration=0.5:offset=2.5[fade01];" ^
  "[fade01][s2]xfade=transition=fade:duration=0.5:offset=6.5[fade02];" ^
  "[fade02][s3]xfade=transition=fade:duration=0.5:offset=10.5[fade03];" ^
  "[fade03][s4]xfade=transition=fade:duration=0.5:offset=15.0[fade04];" ^
  "[fade04][s5]xfade=transition=fade:duration=0.5:offset=18.5[fade05];" ^
  "[fade05][s6]xfade=transition=fade:duration=0.5:offset=22.5[fade06];" ^
  "[fade06][s7]xfade=transition=fade:duration=0.5:offset=25.5[fade07];" ^
  "[fade07][s8]xfade=transition=fade:duration=0.5:offset=28.5[vout]" ^
  -map "[vout]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4" 2>&1 | Select-Object -Last 5

echo.
echo Final video created: codememory-demo.mp4
Get-Item "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4" | Select-Object Name, Length

endlocal