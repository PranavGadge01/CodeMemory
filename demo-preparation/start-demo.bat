@echo off
cd /d "C:\Users\Jay Janardan Patil\Desktop\CodeMemory\frontend"
set NEXT_PUBLIC_API_URL=http://127.0.0.1:8001/api/v1
set PORT=3001
start "NextDev" /min cmd /k "npm run dev -- --hostname 127.0.0.1 --port 3001"
timeout /t 20 /nobreak
echo Checking if Next.js is running...
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3001
echo.
echo Done.