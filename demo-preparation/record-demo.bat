@echo off
REM CodeMemory demo recording script
REM Captures browser window showing the landing page

set LOCAL_PORT=3001
set RECORDING_DIR=%~dp0recordings
set OUTPUT_FILE=%RECORDING_DIR%\codememory-demo-raw.mp4

if not exist "%RECORDING_DIR%" mkdir "%RECORDING_DIR%"

echo Starting browser recording...
echo Target: http://127.0.0.1:%LOCAL_PORT%
echo Output: %OUTPUT_FILE%

REM Capture the primary monitor at 1920x1080
ffmpeg -y -f gdigrab -framerate 30 -i desktop -t 45 -c:v libx264 -preset ultrafast -pix_fmt yuv420p "%OUTPUT_FILE%"

echo Recording complete: %OUTPUT_FILE%
echo File size:
dir "%OUTPUT_FILE%" | findstr "bytes"