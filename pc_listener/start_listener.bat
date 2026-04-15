@echo off
setlocal
cd /d Y:\projects\nfc\pc_listener
set "PYTHON_EXE=%~dp0.venv_clean\Scripts\pythonw.exe"

if exist "%PYTHON_EXE%" (
	"%PYTHON_EXE%" listener.py
	exit /b %errorlevel%
)

rem pythonw not found, try python.exe
set "PYTHON_EXE=%~dp0.venv_clean\Scripts\python.exe"
if exist "%PYTHON_EXE%" (
	"%PYTHON_EXE%" listener.py
	exit /b %errorlevel%
)

echo Python executable not found in venv
echo Recreate venv with: C:\Users\bhanu\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv_clean
exit /b 1