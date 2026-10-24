import subprocess
import os
import sys
import threading
import time

# Set environment variables without trailing spaces
os.environ["CODEMEMORY_DATA_DIR"] = r"C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recording-data"
os.environ["CODEMEMORY_KNOWLEDGE_DIR"] = r"C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recording-knowledge"
os.environ["CODEMEMORY_DB_PATH"] = r"C:\Users\Jay Janardan Patil\Desktop\CodeMemory\demo-preparation\recording-data\codememory-demo.duckdb"
os.environ["CODEMEMORY_API_HOST"] = "127.0.0.1"
os.environ["CODEMEMORY_API_PORT"] = "8001"
os.environ["CODEMEMORY_LOG_LEVEL"] = "INFO"
os.environ["CODEMEMORY_PROBLEM_SOURCE"] = "local"
os.environ["AI_PROVIDER"] = "heuristic"
os.environ["PYTHONPATH"] = r"C:\Users\Jay Janardan Patil\Desktop\CodeMemory\src"

# Verify paths
for var in ["CODEMEMORY_DATA_DIR", "CODEMEMORY_KNOWLEDGE_DIR", "CODEMEMORY_DB_PATH"]:
    val = os.environ.get(var)
    print(f"{var}: repr={repr(val)}")
    if val and val.endswith(' '):
        print(f"  WARNING: trailing space detected! Trimming...")
        os.environ[var] = val.rstrip()

# Verify directories exist
for d in [os.environ["CODEMEMORY_DATA_DIR"], os.environ["CODEMEMORY_KNOWLEDGE_DIR"]]:
    from pathlib import Path
    Path(d).mkdir(parents=True, exist_ok=True)
    print(f"Directory exists: {Path(d).exists()}")

# Start uvicorn
import uvicorn
from api.app import create_app

if __name__ == "__main__":
    print("Starting CodeMemory API server...")
    uvicorn.run(
        create_app,
        host="127.0.0.1",
        port=8001,
        log_level="info",
    )
