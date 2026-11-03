@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\pythonw.exe" goto RUN_PYTHONW
if exist "%~dp0.venv\Scripts\python.exe" goto RUN_PYTHON

set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [Error] uv not found.
    pause
    exit /b 1
)

call uv venv .venv --python 3.12
call uv pip install -r requirements.txt

:RUN_PYTHONW
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py"
exit /b 0

:RUN_PYTHON
start "" "%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
exit /b 0
