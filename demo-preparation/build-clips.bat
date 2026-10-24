@echo off
setlocal

set RECORDINGS=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recordings

echo Creating hero clip (5s)...
ffmpeg -y -loop 1 -framerate 30 -i "%RECORDINGS%\section-hero.png" -vf "zoompan=z='min(zoom+0.005,1.2)':d=1:fps=30:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',fps=30,scale=1920:1080,format=yuv420p" -t 5 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "%RECORDINGS%\hero-clip.mp4" 2>nul

echo Creating memory-trace clip (4s)...
ffmpeg -y -loop 1 -framerate 30 -i "%RECORDINGS%\section-memory-trace.png" -vf "zoompan=z='min(zoom+0.003,1.1)':d=1:fps=30:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',fps=30,scale=1920:1080,format=yuv420p" -t 4 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "%RECORDINGS%\memory-trace-clip.mp4" 2>nul

echo Creating evolution clip (5s)...
ffmpeg -y -loop 1 -framerate 30 -i "%RECORDINGS%\section-solution-evolution.png" -vf "zoompan=z='min(zoom+0.002,1.08)':d=1:fps=30:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',fps=30,scale=1920:1080,format=yuv420p" -t 5 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "%RECORDINGS%\evolution-clip.mp4" 2>nul

echo Creating analytics clip (4s)...
ffmpeg -y -loop 1 -framerate 30 -i "%RECORDINGS%\section-analytics.png" -vf "fps=30,scale=1920:1080,format=yuv420p" -t 4 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "%RECORDINGS%\analytics-clip.mp4" 2>nul

echo Creating knowledge graph clip (4s)...
ffmpeg -y -loop 1 -framerate 30 -i "%RECORDINGS%\section-knowledge.png" -vf "zoompan=z='min(zoom+0.004,1.15)':d=1:fps=30:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',fps=30,scale=1920:1080,format=yuv420p" -t 4 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "%RECORDINGS%\knowledge-clip.mp4" 2>nul

echo Creating revision clip (4s)...
ffmpeg -y -loop 1 -framerate 30 -i "%RECORDINGS%\section-revision.png" -vf "fps=30,scale=1920:1080,format=yuv420p" -t 4 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "%RECORDINGS%\revision-clip.mp4" 2>nul

echo Creating CTA clip (3s)...
ffmpeg -y -loop 1 -framerate 30 -i "%RECORDINGS%\section-cta.png" -vf "fps=30,scale=1920:1080,format=yuv420p,fade=in:0:15" -t 3 -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "%RECORDINGS%\cta-clip.mp4" 2>nul

echo Creating outro clip (3s)...
ffmpeg -y -f lavfi -i "color=c=#07080A:s=1920x1080:d=3:r=30" -vf "drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='CodeMemory':fontsize=80:fontcolor=#FFA116:x=(w-text_w)/2:y=(h-text_h)/2-50:alpha='if(lt(t,1),0,if(gt(t,2.5),1,pow((t-1)/1,2)))',drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='local-first coding memory':fontsize=28:fontcolor=#e4e4ed:x=(w-text_w)/2:y=(h-text_h)/2+50:alpha='if(lt(t,1.2),0,if(gt(t,2.5),1,pow((t-1.2)/1.3,2)))'" -c:v libx264 -pix_fmt yuv420p -preset ultrafast "%RECORDINGS%\outro.mp4" 2>nul

echo All clips created!
endlocal