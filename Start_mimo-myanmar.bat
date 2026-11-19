@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title mimo-myanmar - Windows
set "VENV_PY=%CD%\.venv\Scripts\python.exe"
set "BOOTSTRAP_PY="
set "STARTUP_STAGE=checking Python"

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,11) and sys.maxsize > 2**32 else 1)" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Existing .venv is not Python 3.11 64-bit.
        echo Rename or delete the .venv folder, then run this file again.
        goto failure
    )
    goto environment_ready
)

echo [1/3] Looking for Python 3.11 64-bit ...
call :find_python
if defined BOOTSTRAP_PY goto create_environment

where winget >nul 2>&1
if errorlevel 1 goto python_missing
echo Installing Python 3.11 for the current Windows user ...
winget install --id Python.Python.3.11 --exact --source winget --architecture x64 --scope user --accept-source-agreements --accept-package-agreements
call :find_python
if defined BOOTSTRAP_PY goto create_environment

:python_missing
echo [ERROR] Python 3.11 64-bit could not be located or installed.
echo Install it from https://www.python.org/downloads/ and run this file again.
echo You can also use Set_Python_Path.bat to select python.exe manually.
goto failure

:find_python
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,11) and sys.maxsize > 2**32 else 1)" >nul 2>&1
    if not errorlevel 1 set "BOOTSTRAP_PY=python"
)
if defined BOOTSTRAP_PY exit /b 0

where py >nul 2>&1
if not errorlevel 1 (
    py -3.11-64 -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,11) and sys.maxsize > 2**32 else 1)" >nul 2>&1
    if not errorlevel 1 set "BOOTSTRAP_PY=py -3.11-64"
)
if defined BOOTSTRAP_PY exit /b 0

for %%D in ("%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Python\pythoncore-3.11-64\python.exe" "C:\Program Files\Python311\python.exe" "C:\Python311\python.exe") do (
    if exist "%%~D" (
        "%%~D" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,11) and sys.maxsize > 2**32 else 1)" >nul 2>&1
        if not errorlevel 1 set "BOOTSTRAP_PY="%%~D""
    )
)
exit /b 0

:create_environment
set "STARTUP_STAGE=creating the local Python environment"
echo [2/3] Creating virtual environment ...
%BOOTSTRAP_PY% -m venv ".venv"
if errorlevel 1 goto failure

:environment_ready
set "STARTUP_STAGE=checking desktop and speech packages"
"%VENV_PY%" -c "import app, huggingface_hub, numpy, misaki, phonemizer, espeakng_loader" >nul 2>&1
if errorlevel 1 (
    echo [2/3] Installing desktop and speech packages ...
    "%VENV_PY%" -m pip install --disable-pip-version-check -r "requirements-app.txt"
    if errorlevel 1 goto failure
    "%VENV_PY%" -c "import app, huggingface_hub, numpy, misaki, phonemizer, espeakng_loader"
    if errorlevel 1 goto failure
)
set "STARTUP_STAGE=checking the ONNX Runtime"
"%VENV_PY%" -c "from onnxruntime import InferenceSession" >nul 2>&1
if errorlevel 1 (
    echo [2/3] Installing or repairing ONNX Runtime for CPU ...
    "%VENV_PY%" -m pip uninstall -y onnxruntime-gpu
    if errorlevel 1 goto failure
    "%VENV_PY%" -m pip install --disable-pip-version-check --force-reinstall --no-deps "onnxruntime>=1.23.2"
    if errorlevel 1 goto failure
    "%VENV_PY%" -m pip install --disable-pip-version-check "onnxruntime>=1.23.2"
    if errorlevel 1 goto failure
    "%VENV_PY%" -c "from onnxruntime import InferenceSession"
    if errorlevel 1 goto failure
)

set "STARTUP_STAGE=opening the desktop window"
echo [3/3] Starting mimo-myanmar ...
"%VENV_PY%" "app.py"
if errorlevel 1 goto failure
exit /b 0

:failure
echo.
echo mimo-myanmar stopped while %STARTUP_STAGE%.
echo Run Check_Installation.bat for diagnostics. See README.md for troubleshooting.
echo If reporting a problem, include the error shown above.
pause
exit /b 1
