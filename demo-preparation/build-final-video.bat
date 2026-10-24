@echo off
setlocal

set R=C:\tmp\cm-video
set OUTPUT=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\codememory-demo.mp4

REM Re-encode all clips with proper quality and add section headers
REM Using the non-faded clips and concat with proper transitions

REM Create individual clips with section titles
ffmpeg -y -i "%R%\intro-final.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='CodeMemory':fontsize=60:fontcolor=#FFA116:x=(w-text_w)/2:y=(h-text_h)/2+30:alpha='if(lt(t,0.8),0,if(gt(t,2.2),1,pow((t-0.8)/1.4,2)))',drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Your coding history, remembered.':fontsize=22:fontcolor=#e4e4ed:x=(w-text_w)/2:y=(h-text_h)/2+100:alpha='if(lt(t,1),0,if(gt(t,2.2),1,pow((t-1)/1.2,2)))'" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\titled-intro.mp4" 2>nul

ffmpeg -y -i "%R%\hero-titled.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Landing':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15:alpha='if(lt(t,0.3),0,1)'" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\hero-labeled.mp4" 2>nul

ffmpeg -y -i "%R%\memory-trace-clip.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Every attempt is preserved':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\memory-labeled.mp4" 2>nul

ffmpeg -y -i "%R%\evolution-clip.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Solution Evolution':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\evolution-labeled.mp4" 2>nul

ffmpeg -y -i "%R%\analytics-clip.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Analytics':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\analytics-labeled.mp4" 2>nul

ffmpeg -y -i "%R%\knowledge-clip.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Knowledge Graph':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\knowledge-labeled.mp4" 2>nul

ffmpeg -y -i "%R%\revision-clip.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Revision Queue':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\revision-labeled.mp4" 2>nul

ffmpeg -y -i "%R%\cta-clip.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Get Started':fontcolor=#e4e4ed:fontsize=24:x=40:y=40:box=1:boxcolor=#07080A80:boxborderw=15" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\cta-labeled.mp4" 2>nul

ffmpeg -y -i "%R%\outro-final.mp4" -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='local-first coding memory':fontsize=22:fontcolor=#e4e4ed:x=(w-text_w)/2:y=(h-text_h)/2+100:alpha='if(lt(t,1),0,if(gt(t,2.5),1,pow((t-1)/1.5,2)))'" -c:v libx264 -crf 18 -pix_fmt yuv420p "%R%\outro-labeled.mp4" 2>nul

REM Create concat list
echo file 'titled-intro.mp4'> "%R%\concat-titled.txt"
echo file 'hero-labeled.mp4'>> "%R%\concat-titled.txt"
echo file 'memory-labeled.mp4'>> "%R%\concat-titled.txt"
echo file 'evolution-labeled.mp4'>> "%R%\concat-titled.txt"
echo file 'analytics-labeled.mp4'>> "%R%\concat-titled.txt"
echo file 'knowledge-labeled.mp4'>> "%R%\concat-titled.txt"
echo file 'revision-labeled.mp4'>> "%R%\concat-titled.txt"
echo file 'cta-labeled.mp4'>> "%R%\concat-titled.txt"
echo file 'outro-labeled.mp4'>> "%R%\concat-titled.txt"

REM Concatenate with re-encoding
ffmpeg -y -f concat -safe 0 -i "%R%\concat-titled.txt" -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p "%OUTPUT%" 2>&1 | findstr /v "Input\|Output\|Stream\|Duration\|Metadata\|handler\|vendor\|^$"

ffprobe -v error -show_entries format=duration -show_entries stream=width,height,nb_frames -of csv "%OUTPUT%"
dir "%OUTPUT%" | findstr "bytes"

endlocal