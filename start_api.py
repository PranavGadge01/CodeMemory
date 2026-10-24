call activate_py312.bat
python -m uvicorn api.app:create_app --factory --host 127.0.0.1 --port 8001