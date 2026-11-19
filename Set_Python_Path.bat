@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo Type full path to your Python 3.11 64-bit python.exe
set /p "PY_PATH=Python path: "
if not exist "%PY_PATH%" (
 echo File not found.
 pause
 exit /b 1
)
"%PY_PATH%" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,11) and sys.maxsize > 2**32 else 1)"
if errorlevel 1 (
 echo This executable is not Python 3.11 64-bit.
 pause
 exit /b 1
)
if exist ".venv" (
 echo Existing .venv detected. Rename or delete it before creating a new one.
 pause
 exit /b 1
)
"%PY_PATH%" -m venv ".venv"
if errorlevel 1 pause
if errorlevel 1 exit /b 1
call "Start_mimo-myanmar.bat"
