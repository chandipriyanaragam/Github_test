@echo off
setlocal
set "UV_CACHE_DIR=%~dp0.uv-cache"
pushd "%~dp0"
uv sync
if errorlevel 1 (popd & exit /b 1)
uv run uvicorn app.start:app --reload --host 127.0.0.1 --port 8000
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
