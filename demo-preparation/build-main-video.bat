@echo off
setlocal

set R=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recordings
set OUTPUT=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4

REM Create the main demo video using the full landing page screenshot with pan/zoom
REM The full page is 5677px height at 1910px width
REM We'll simulate a smooth scroll with zoom effects

REM Create the intro sequence (3 seconds)
ffmpeg -y -f lavfi -i "color=c=#07080A:s=1920x1080:d=3:r=30" -i "%R%\logo.png" -filter_complex "[1:v]scale=160:160,setsar=1[logo];[0:v][logo]overlay=x=(W-w)/2:y=H/2-150:enable='gte(t,0.8)',drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='CodeMemory':fontsize=70:fontcolor=#FFA116:x=(w-text_w)/2:y=(h-text_h)/2+50:alpha='if(lt(t,0.8),0,if(gt(t,2.5),1,pow((t-0.8)/1.7,2)))',drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Your coding history, remembered.':fontsize=24:fontcolor=#e4e4ed:x=(w-text_w)/2:y=(h-text_h)/2+120:alpha='if(lt(t,1.0),0,if(gt(t,2.5),1,pow((t-1)/1.5,2)))'" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\intro-smooth.mp4" 2>nul

REM Create the main scroll simulation using the full landing page
REM Simulate scrolling: start at hero, scroll to memory trace, evolution, analytics, knowledge, revision, CTA
REM Full page height: 5677, viewport: 1080
REM Scroll positions: hero(0), memory(600), evolution(1200), analytics(1900), knowledge(2500), revision(3100), cta(4600)
REM Time per section: ~4s each

ffmpeg -y -i "%R%\landing-full.png" -vf "
scale=1920:5677,
zoompan=z='if(lte(in,120),1.0+0.05*(sin(in/10)),1.15)':d=1:fps=30:x='if(lte(in,40),0,if(lte(in,80),40*(in-40)/40,if(lte(in,120),40,if(lte(in,160),40+20*(in-120)/40,if(lte(in,200),60+40*(in-160)/40,if(lte(in,240),100+20*(in-200)/40,120))))':y='if(lte(in,40),0,0)':s=1920x1080,
fps=30,format=yuv420p
" -t 12 -c:v libx264 -crf 23 -pix_fmt yuv420p "%R%\scroll-demo.mp4" 2>nul

REM Create fade transition clip
ffmpeg -y -i "%R%\scroll-demo.mp4" -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=11.5:d=0.5" -c:v libx264 -crf 23 -pix_fmt yuv420p "%R%\scroll-faded.mp4" 2>nul

REM Create outro (3 seconds)
ffmpeg -y -f lavfi -i "color=c=#07080A:s=1920x1080:d=3:r=30" -i "%R%\logo.png" -filter_complex "[1:v]scale=160:160,setsar=1[logo];[0:v][logo]overlay=x=(W-w)/2:y=H/2-150:enable='gte(t,0.8)',drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='CodeMemory':fontsize=70:fontcolor=#FFA116:x=(w-text_w)/2:y=(h-text_h)/2+50:alpha='if(lt(t,0.8),0,if(gt(t,2.5),1,pow((t-0.8)/1.7,2)))',drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='local-first coding memory':fontsize=24:fontcolor=#e4e4ed:x=(w-text_w)/2:y=(h-text_h)/2+120:alpha='if(lt(t,1.0),0,if(gt(t,2.5),1,pow((t-1)/1.5,2)))'" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\outro-smooth.mp4" 2>nul

REM Concatenate with crossfade
ffmpeg -y -i "%R%\intro-smooth.mp4" -i "%R%\scroll-faded.mp4" -i "%R%\outro-smooth.mp4" -filter_complex "[0:v]format=yuv420p[f0];[1:v]format=yuv420p[f1];[2:v]format=yuv420p[f2];[f0][f1]xfade=transition=fade:duration=0.5:offset=2.5[f01];[f01][f2]xfade=transition=fade:duration=0.5:offset=14.5[fout]" -map "[fout]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "%OUTPUT%" 2>&1 | findstr /v "Input\|Output\|Stream\|Duration\|Metadata\|handler\|vendor\|^$"

ffprobe -v error -show_entries format=duration -show_entries stream=width,height,nb_frames -of csv "%OUTPUT%"
dir "%OUTPUT%" | findstr "bytes"

endlocal