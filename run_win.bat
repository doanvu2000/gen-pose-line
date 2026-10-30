@echo off
chcp 65001 >nul
cd /d "%~dp0"
set VENV=.venv
set REQ=requirements.txt
if /i "%1"=="gpu" (
  set VENV=.venv-gpu
  set REQ=requirements-gpu.txt
  set POSE_TOOL_DEVICE=cuda
)
if not exist "%VENV%\Scripts\python.exe" (
  echo Tao moi truong %VENV% ...
  py -3 -m venv %VENV% 2>nul || python -m venv %VENV%
  if errorlevel 1 ( echo Can Python 3.10+ tu python.org & pause & exit /b 1 )
)
fc /b %REQ% %VENV%\.req_stamp >nul 2>&1
if errorlevel 1 (
  echo Cai thu vien lan dau, vui long cho ...
  "%VENV%\Scripts\python.exe" -m pip install -U pip -q
  "%VENV%\Scripts\python.exe" -m pip install -r %REQ%
  if errorlevel 1 ( echo Loi cai thu vien & pause & exit /b 1 )
  copy /y %REQ% %VENV%\.req_stamp >nul
)
echo Mo http://127.0.0.1:7860 - dong cua so nay de tat tool.
"%VENV%\Scripts\python.exe" app.py
pause
