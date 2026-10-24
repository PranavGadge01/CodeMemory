@echo off
setlocal
set "CODEMEMORY_DATA_DIR=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recording-data"
set "CODEMEMORY_KNOWLEDGE_DIR=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recording-knowledge"
set "CODEMEMORY_DB_PATH=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recording-data\codememory-demo.duckdb"
set "CODEMEMORY_API_HOST=127.0.0.1"
set "CODEMEMORY_API_PORT=8001"
set "CODEMEMORY_LOG_LEVEL=INFO"
set "CODEMEMORY_PROBLEM_SOURCE=local"
set "AI_PROVIDER=heuristic"
set "PYTHONPATH=C:\Users\Jay Janardan Patil\Desktop\CodeMemory\src"
cd /d "C:\Users\Jay Janardan Patil\Desktop\CodeMemory"
.venv-demo\Scripts\python.exe -m uvicorn api.app:create_app --factory --host 127.0.0.1 --port 8001