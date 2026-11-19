# mimo-myanmar

mimo-myanmar is a Windows desktop app for generating Burmese and English speech locally with Nara Mini v1. Download the voices you need, then generate, play, and export WAV audio offline.

[Setup](#setup) · [Download voices](#download-voices) · [Generate speech](#generate-speech) · [NVIDIA GPU](#optional-nvidia-gpu) · [Troubleshooting](#troubleshooting) · [Report a bug](#report-a-bug)

## Setup

1. Extract the ZIP into a writable folder, such as a folder under Documents. Keep the extracted files together and run the launcher from that folder.
2. Double-click **`Start_mimo-myanmar.bat`**. It finds 64-bit Python 3.11 or installs it for the current Windows user through WinGet. Then it creates a local `.venv`, installs the desktop and speech packages, and opens mimo-myanmar. Leave the console open while setup runs.
3. If WinGet is unavailable or blocked by Windows policy, install 64-bit Python 3.11 and run the launcher again. If Python is installed in a custom location, run **`Set_Python_Path.bat`** and paste the full path to `python.exe`. [Python downloads](https://www.python.org/downloads/) · [Install WinGet](https://learn.microsoft.com/en-us/windows/package-manager/winget/)

The first setup needs an internet connection and disk space for Python, dependencies, and the voices you select. Later launches check the existing environment and repair missing dependencies as needed. An NVIDIA GPU is optional.

## Download voices

1. Click **Download voices**.
2. Check Shoon, Thazin, Ko Banyar, Htet Myat, or any combination. The dialog shows the estimated total.
3. Click **Download selected**. When a voice is ready, select it from the **Voice** menu.

| Selection | Approximate voice files |
| --- | ---: |
| One voice | 190 MB |
| Two voices | 380 MB |
| Three voices | 570 MB |
| All four voices | 760 MB |

Estimates cover ONNX voice files. Shared model code and Python dependencies also use disk space. Start with one voice to get started sooner. mimo-myanmar reuses available files on retries and when you add more voices. The upstream repository is public, and mimo-myanmar downloads anonymously. [Nara Mini v1 files](https://huggingface.co/YeeNyunn/nara-mini-v1/tree/main)

## Generate speech

1. Enter a short Burmese or English sentence and select a voice marked ready offline.
2. Keep **Processing device** on **Auto**, or select **CPU** to test without CUDA. **CPU threads** controls how many threads the model can use for computation.
3. Leave **Read numbers using Burmese rules** enabled to use the model's built-in number normalization, including for mixed-language text. Turn it off to pass digits as written to the model.
4. Click **Generate speech**. Use **Play** or **Pause** to preview, **Save as** to export a copy, or **Open folder** to see generated files in `Documents\mimo-myanmar`.

mimo-myanmar limits each generation to 18,000 characters. If a passage exceeds the model's phoneme limit, split it into shorter sentences and try again. Preset voice selection and number normalization are the synthesis controls exposed by Nara Mini v1. [Upstream inference guide](https://huggingface.co/YeeNyunn/nara-mini-v1#run-inference)

## Optional NVIDIA GPU

Choose **Install GPU support** to install ONNX Runtime GPU. CUDA requires an NVIDIA GPU and compatible NVIDIA drivers, CUDA, and cuDNN versions. **Auto** tries GPU when available and can fall back to CPU. **NVIDIA GPU (CUDA)** reports a failure if CUDA cannot activate. The GPU adapter is experimental and has not been validated on NVIDIA hardware here. [ONNX Runtime CUDA requirements](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)

## Troubleshooting

| What you see | What to try |
| --- | --- |
| The launcher closes or the window never opens | Open Command Prompt in the extracted folder and run `Start_mimo-myanmar.bat`. Read the startup stage and first error in the console. |
| Python is missing or WinGet fails | Install 64-bit Python 3.11 and reopen the launcher. For a custom Python path, use `Set_Python_Path.bat`. |
| The launcher rejects an existing `.venv` | Close mimo-myanmar, rename `.venv` to `.venv-backup`, and reopen the launcher. Keep the `model` folder to reuse downloaded voices. |
| `No module named onnxruntime` or a Python dependency fails to load | Close mimo-myanmar and rerun `Start_mimo-myanmar.bat`. Run `Check_Installation.bat` if the repair fails. |
| Voice download reports `401 Unauthorized` or `403 Forbidden` | Retry **Download voices**. Check whether your network or proxy allows Hugging Face file downloads if it keeps failing. |
| Voice download is offline, busy, or rate-limited | Check your connection, then retry the same voice when the service is available. A stopped download may take time to finish its current network requests. |
| The drive is full or Windows denies access | Free disk space or move the extracted project to a writable folder. If the error happens after **Generate**, also check your Documents folder. |
| A voice reports missing or damaged ONNX files | Try downloading the voice again. If it still appears installed and repeatedly fails, close mimo-myanmar, rename the affected voice folder under `model\onnx`, then reopen and download that voice. |
| CUDA cannot activate or a CUDA DLL is missing | Select **CPU** to continue. Compare installed GPU libraries with the ONNX Runtime compatibility table above before installing GPU support again. |
| Generate reports a passage or phoneme error | Test with one short sentence on **CPU**. Split longer passages. If **Show Details** points to an English phonemizer error, rerun the launcher to check its bundled dependencies. |
| Speech generates but preview is silent | Check the Windows output device and volume. Open the output folder and play the WAV in another player. |

## Report a bug

Run **`Check_Installation.bat`** and copy the environment, ONNX providers, and voice status. In the GitHub issue, include:

- Your Windows version and whether the problem happens during setup, download, generation, or playback.
- Steps to reproduce, selected voice, and processing device.
- The exact error and **Show Details** output when available, or the first failing lines in the launcher.
- A short sample that reproduces the problem without private text. Redact personal paths, credentials, and signed download URLs from any logs you share.

## Project files

- [Start_mimo-myanmar.bat](Start_mimo-myanmar.bat) installs or repairs the local Python environment and launches mimo-myanmar.
- [Set_Python_Path.bat](Set_Python_Path.bat) creates the environment from a manually selected Python installation.
- [Check_Installation.bat](Check_Installation.bat) reports Python, ONNX Runtime, and voice availability.
- [requirements-app.txt](requirements-app.txt) lists desktop and shared speech dependencies. The launcher installs the CPU ONNX Runtime separately.
- [app.py](app.py) contains the desktop UI, voice downloads, and worker tasks.
- [inference_runner.py](inference_runner.py) runs upstream synthesis with the selected ONNX processing device.

## Credits

mimo-myanmar is by [ThuraHex](https://github.com/thurahex), developed with AI assistance. It uses [Nara Mini v1](https://huggingface.co/YeeNyunn/nara-mini-v1) by the [Nara contributors](https://naraaudio.app), a Kokoro-based Burmese and English speech model. Nara Mini v1 is licensed under Apache 2.0. The model's `LICENSE` and `NOTICE` are downloaded alongside the shared model files.
