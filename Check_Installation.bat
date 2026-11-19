@echo off
setlocal
cd /d "%~dp0"
echo === mimo-myanmar Diagnostics ===
echo.
where python
python --version
if exist ".venv\Scripts\python.exe" (
 echo.
 echo === Virtual Environment ===
 ".venv\Scripts\python.exe" --version
 ".venv\Scripts\python.exe" -m pip --version
 ".venv\Scripts\python.exe" -c "import importlib.util; print('PySide6:', bool(importlib.util.find_spec('PySide6'))); print('huggingface_hub:', bool(importlib.util.find_spec('huggingface_hub'))); print('onnxruntime:', bool(importlib.util.find_spec('onnxruntime')))"
 ".venv\Scripts\python.exe" -c "import onnxruntime as ort; print('ONNX Runtime:', ort.__version__); print('ONNX providers:', ort.get_available_providers())"
 if errorlevel 1 echo ONNX Runtime could not load. Restart using Start_mimo-myanmar.bat.
) else (
 echo No .venv found. Run Start_mimo-myanmar.bat first.
)
if exist ".venv\Scripts\python.exe" (
 ".venv\Scripts\python.exe" -c "from app import VOICE_NAMES, source_present, voice_present; print('Shared model files:', 'ready' if source_present() else 'missing'); [print(name, 'installed' if source_present() and voice_present(voice) else 'needs download') for voice, name in VOICE_NAMES.items()]"
)
echo.
pause
