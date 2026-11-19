"""mimo-myanmar - local Windows desktop front-end for Nara Mini v1.
Nara Mini v1 is developed by Nara contributors and not bundled in this application.
"""
import os
import sys
import shutil
import subprocess
import errno
import wave
from tempfile import TemporaryDirectory
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import QObject, QThread, Signal, QUrl, Qt
from PySide6.QtGui import QFont, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QComboBox, QPushButton, QFrame, QProgressBar, QFileDialog,
    QMessageBox, QSpinBox, QCheckBox, QDialog, QDialogButtonBox
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "model"
OUT_DIR = Path.home() / "Documents" / "mimo-myanmar"
MODEL_ID = "YeeNyunn/nara-mini-v1"
VOICE_IDS = ["shoon", "thazin", "ko-banyar", "htet-myat"]
VOICE_NAMES = dict(zip(VOICE_IDS, ("Shoon", "Thazin", "Ko Banyar", "Htet Myat")))
VOICE_FILES = ("encoder.onnx", "decoder.onnx", "voice.json")


def source_present():
    return all((MODEL_DIR / name).is_file() for name in (
        "synthesize.py", "frontend/english.py", "frontend/nara_frontend.py",
        "frontend/my_numbers.py", "frontend/g2p_my.py", "frontend/char_map.py",
        "frontend/nara_names.py", "frontend/lexicon_exceptions.tsv", "frontend/mined_rules.tsv",
    ))


def voice_present(voice):
    folder = MODEL_DIR / "onnx" / voice
    return all((folder / name).is_file() for name in VOICE_FILES)


class OperationError(RuntimeError):
    def __init__(self, message, details=""):
        super().__init__(message)
        self.details = details

STYLE = """
QWidget { background: #0b1020; color: #e5ebf7; font-family: 'Segoe UI'; font-size: 13px; }
QLabel#brand { font-size: 25px; font-weight: 750; color: #f8fafc; }
QLabel#sub { font-size: 12px; color: #8191ac; }
QLabel#heading { font-size: 15px; font-weight: 700; }
QLabel#field { font-size: 12px; font-weight: 600; color: #9babca; }
QLabel#note { font-size: 12px; color: #8b9dbb; }
QFrame#panel { background: #141d32; border: 1px solid #25314b; border-radius: 16px; }
QFrame#header { background: #11192a; border: 1px solid #25314b; border-radius: 14px; }
QTextEdit { background: #0e1627; border: 1px solid #30405d; border-radius: 11px; padding: 15px; font-size: 16px; selection-background-color: #4d74f5; }
QTextEdit:focus { border-color: #728dff; }
QComboBox, QSpinBox { background: #0e1627; border: 1px solid #34445e; border-radius: 9px; padding: 9px 12px; min-height: 22px; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox QAbstractItemView { background: #19233a; color: white; selection-background-color: #3f5bb0; }
QPushButton { border-radius: 10px; padding: 11px 15px; font-weight: 650; border: 1px solid #354765; background: #1b2942; color: #e5eefd; }
QPushButton:hover { background: #2b3e60; }
QPushButton:disabled { background: #172036; color: #687991; border-color: #26324c; }
QPushButton#primary { background: #647cf8; color: #ffffff; border: 1px solid #8397ff; font-size: 14px; }
QPushButton#primary:hover { background: #7a8efc; }
QPushButton#secondary { background: #172b30; color: #91ebd5; border: 1px solid #28534c; }
QProgressBar { background: #1c2943; border: none; height: 7px; border-radius: 3px; text-align: center; }
QProgressBar::chunk { background: #7189ff; border-radius: 3px; }
"""


def panel(title=None):
    p = QFrame()
    p.setObjectName("panel")
    layout = QVBoxLayout(p)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(12)
    if title:
        h = QLabel(title)
        h.setObjectName("heading")
        layout.addWidget(h)
    return p, layout


class Work(QObject):
    status = Signal(str)
    done = Signal(str)
    failed = Signal(str, str)
    stopped = Signal()
    finished = Signal()

    def __init__(self, mode, voice="shoon", content="", threads=4, backend="auto",
                 *, voices=(), normalize_numbers=True):
        super().__init__()
        self.mode = mode
        self.voice = voice
        self.content = content
        self.threads = threads
        self.backend = backend
        self.voices = voices
        self.normalize_numbers = normalize_numbers
        self.proc = None
        self.cancelled = False

    def cancel(self):
        self.cancelled = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def run_cmd(self, argv, cwd=None):
        if self.cancelled:
            raise RuntimeError("Operation cancelled")
        self.status.emit("Running: " + " ".join(str(a) for a in argv[:3]) + " …")
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        self.proc = subprocess.Popen(
            argv, cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            startupinfo=startupinfo, bufsize=1
        )
        lines = []
        for line in self.proc.stdout:
            line = line.strip()
            if line:
                lines.append(line)
                if len(lines) > 30:
                    lines.pop(0)
                self.status.emit(line[:260])
        code = self.proc.wait()
        if self.cancelled:
            raise RuntimeError("Operation cancelled")
        if code != 0:
            details = "\n".join(lines[-12:]) or f"Process exited with code {code}"
            if self.mode == "generate":
                message = (
                    "Speech generation failed. Try a short sentence with CPU selected. "
                    "If the error mentions a missing Python package, restart using Start_mimo-myanmar.bat."
                )
            else:
                message = (
                    "GPU setup failed. Restart using Start_mimo-myanmar.bat to check or restore the CPU runtime."
                )
            raise OperationError(message, details)

    def run(self):
        try:
            if self.cancelled:
                self.stopped.emit()
                return
            if self.mode == "setup":
                voices = self.voices or (self.voice,)
                self.status.emit("Downloading " + ", ".join(VOICE_NAMES[voice] for voice in voices) + "…")
                from huggingface_hub import snapshot_download
                from huggingface_hub.errors import HfHubHTTPError, LocalEntryNotFoundError, OfflineModeIsEnabled

                try:
                    snapshot_download(
                        repo_id=MODEL_ID,
                        local_dir=str(MODEL_DIR),
                        token=False,
                        allow_patterns=[
                            "frontend/*", "synthesize.py", "requirements.txt",
                            "LICENSE", "NOTICE", "README.md",
                            *(f"onnx/{voice}/{name}" for voice in voices for name in VOICE_FILES),
                        ],
                    )
                except (LocalEntryNotFoundError, OfflineModeIsEnabled) as exc:
                    raise OperationError(
                        "The voice files are unavailable offline. Check your network and try Download voices again.",
                        str(exc),
                    ) from exc
                except HfHubHTTPError as exc:
                    code = exc.response.status_code if exc.response is not None else None
                    if code in (401, 403):
                        raise OperationError(
                            "Hugging Face denied access to the public model download. "
                            "Check whether your network or proxy allows Hugging Face file downloads, then retry.",
                            str(exc),
                        ) from exc
                    if code == 429 or (code is not None and code >= 500):
                        raise OperationError("Hugging Face is busy or unavailable. Try the download again later.", str(exc)) from exc
                    raise OperationError("Hugging Face could not complete the voice download.", str(exc)) from exc
                if self.cancelled:
                    raise RuntimeError("Operation cancelled")
                if not source_present() or not all(map(voice_present, voices)):
                    raise RuntimeError("Some required voice files are missing. Try the download again.")
                self.done.emit("Selected voices are ready for offline speech.")
            elif self.mode == "gpu_setup":
                self.status.emit("Installing NVIDIA ONNX Runtime GPU support …")
                pip = [sys.executable, "-m", "pip"]
                with TemporaryDirectory() as staging:
                    self.run_cmd([*pip, "download", "--only-binary=:all:", "--dest", staging, "onnxruntime-gpu"])
                    wheel, = Path(staging).glob("onnxruntime_gpu-*.whl")
                    self.run_cmd([*pip, "uninstall", "-y", "onnxruntime", "onnxruntime-gpu"])
                    self.run_cmd([*pip, "install", "--no-index", "--find-links", staging, str(wheel)])
                self.done.emit("GPU runtime installed. CUDA also requires compatible NVIDIA drivers and CUDA/cuDNN libraries.")
            else:
                if not source_present() or not voice_present(self.voice):
                    raise RuntimeError("Download this voice before generating speech.")
                OUT_DIR.mkdir(parents=True, exist_ok=True)
                output = OUT_DIR / f"mimo-myanmar_{datetime.now():%Y%m%d_%H%M%S_%f}.wav"
                self.run_cmd([
                    sys.executable, str(ROOT / "inference_runner.py"), "--backend", self.backend, "--voice", self.voice,
                    "--text", self.content, "--output", str(output),
                    "--threads", str(self.threads),
                    *([] if self.normalize_numbers else ["--no-normalize-numbers"]),
                ], cwd=MODEL_DIR)
                if not output.exists() or output.stat().st_size < 44:
                    raise RuntimeError("Speech generation produced an empty audio file. Try a shorter passage.")
                try:
                    with wave.open(str(output), "rb") as audio:
                        if not audio.readframes(1):
                            raise wave.Error("WAV contains no audio frames")
                except (wave.Error, EOFError) as exc:
                    raise OperationError("Speech generation produced invalid WAV audio.", str(exc)) from exc
                self.done.emit(str(output))
        except Exception as exc:
            if self.cancelled:
                self.stopped.emit()
            elif isinstance(exc, OperationError):
                self.failed.emit(str(exc), exc.details)
            elif isinstance(exc, OSError) and (exc.errno == errno.ENOSPC or getattr(exc, "winerror", None) == 112):
                self.failed.emit("The drive is out of space. Free some space and try again.", str(exc))
            elif isinstance(exc, PermissionError):
                self.failed.emit("Windows denied access to a file. Use a writable app or output folder.", str(exc))
            else:
                self.failed.emit(str(exc) or type(exc).__name__, "")
        finally:
            self.finished.emit()


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mimo-myanmar · Local AI Voice")
        self.setMinimumSize(790, 660)
        self.resize(970, 770)
        self.setStyleSheet(STYLE)
        self.active_thread = None
        self.active_work = None
        self.latest_file = None
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.9)
        self.player.setAudioOutput(self.audio)
        self.player.playbackStateChanged.connect(self.playback_changed)
        self.player.errorOccurred.connect(lambda error, msg: self.status_label.setText("Audio playback error: " + msg) if hasattr(self, "status_label") else None)
        self.make_ui()
        self.update_install_state()

    def make_ui(self):
        body = QWidget()
        self.setCentralWidget(body)
        outer = QVBoxLayout(body)
        outer.setContentsMargins(26, 23, 26, 24)
        outer.setSpacing(18)

        header = QFrame()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 15, 20, 15)
        brand_stack = QVBoxLayout()
        brand_stack.setSpacing(3)
        b = QLabel("◈  mimo-myanmar")
        b.setObjectName("brand")
        s = QLabel("Local Burmese & English text-to-speech • CPU / NVIDIA GPU")
        s.setObjectName("sub")
        brand_stack.addWidget(b)
        brand_stack.addWidget(s)
        hl.addLayout(brand_stack, 1)
        self.ready_label = QLabel("Checking model…")
        self.ready_label.setObjectName("note")
        hl.addWidget(self.ready_label)
        outer.addWidget(header)

        main_panel, pl = panel("Write your script")
        instructions = QLabel("Enter Burmese or English text. Choose a voice and generate natural speech.")
        instructions.setObjectName("note")
        instructions.setWordWrap(True)
        pl.addWidget(instructions)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("မြန်မာစာ သို့မဟုတ် English စာသားကို ဒီနေရာမှာ ရေးပါ…")
        self.editor.setPlainText("မင်္ဂလာပါ။ mimo-myanmar မှ ကြိုဆိုပါတယ်။")
        self.editor.setMinimumHeight(185)
        pl.addWidget(self.editor, 1)
        lower = QHBoxLayout()
        lower.setSpacing(15)
        voice_stack = QVBoxLayout()
        voice_stack.addWidget(self.small_label("VOICE"))
        self.voice_combo = QComboBox()
        for voice, name in VOICE_NAMES.items():
            self.voice_combo.addItem(name, voice)
        voice_stack.addWidget(self.voice_combo)
        lower.addLayout(voice_stack, 2)
        thread_stack = QVBoxLayout()
        thread_stack.addWidget(self.small_label("CPU THREADS"))
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, max(1, os.cpu_count() or 4))
        self.thread_spin.setValue(min(4, os.cpu_count() or 4))
        thread_stack.addWidget(self.thread_spin)
        lower.addLayout(thread_stack, 1)
        device_stack = QVBoxLayout()
        device_stack.addWidget(self.small_label("PROCESSING DEVICE"))
        self.device_combo = QComboBox()
        self.device_combo.addItem("Auto (GPU if available)", "auto")
        self.device_combo.addItem("CPU", "cpu")
        self.device_combo.addItem("NVIDIA GPU (CUDA)", "cuda")
        device_stack.addWidget(self.device_combo)
        lower.addLayout(device_stack, 2)
        pl.addLayout(lower)
        self.normalize_numbers = QCheckBox("Read numbers using Burmese rules")
        self.normalize_numbers.setChecked(True)
        self.normalize_numbers.setToolTip("Turn off to pass numbers to Nara Mini as written.")
        pl.addWidget(self.normalize_numbers)
        actions = QHBoxLayout()
        self.generate_btn = QPushButton("▶  Generate speech")
        self.generate_btn.setObjectName("primary")
        self.generate_btn.clicked.connect(self.generate)
        actions.addWidget(self.generate_btn, 2)
        self.cancel_btn = QPushButton("Stop")
        self.cancel_btn.clicked.connect(self.cancel)
        self.cancel_btn.setEnabled(False)
        actions.addWidget(self.cancel_btn, 1)
        pl.addLayout(actions)
        outer.addWidget(main_panel, 1)

        result_panel, rl = panel("Your audio")
        self.output_label = QLabel("No audio generated yet")
        self.output_label.setObjectName("note")
        self.output_label.setWordWrap(True)
        rl.addWidget(self.output_label)
        buttons = QHBoxLayout()
        self.play_btn = QPushButton("▶  Play")
        self.play_btn.clicked.connect(self.play_pause)
        self.save_btn = QPushButton("⇩  Save as…")
        self.save_btn.clicked.connect(self.save_as)
        self.folder_btn = QPushButton("Open folder")
        self.folder_btn.clicked.connect(self.open_folder)
        for btn in (self.play_btn, self.save_btn):
            btn.setEnabled(False)
        buttons.addWidget(self.play_btn)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.folder_btn)
        rl.addLayout(buttons)
        outer.addWidget(result_panel)

        footer = QHBoxLayout()
        self.install_btn = QPushButton("Download voices…")
        self.install_btn.setObjectName("secondary")
        self.install_btn.clicked.connect(self.install_model)
        footer.addWidget(self.install_btn)
        self.gpu_btn = QPushButton("Install GPU support")
        self.gpu_btn.clicked.connect(self.install_gpu)
        footer.addWidget(self.gpu_btn)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setMaximumWidth(105)
        footer.addWidget(self.progress)
        self.status_label = QLabel("Choose a voice to get started.")
        self.status_label.setObjectName("note")
        self.status_label.setWordWrap(True)
        footer.addWidget(self.status_label, 1)
        about = QPushButton("Credits")
        about.clicked.connect(self.about)
        footer.addWidget(about)
        outer.addLayout(footer)
        self.voice_combo.currentIndexChanged.connect(self.update_install_state)

    def small_label(self, txt):
        w = QLabel(txt)
        w.setObjectName("field")
        return w

    def update_install_state(self):
        has_source = source_present()
        for index, (voice, name) in enumerate(VOICE_NAMES.items()):
            installed = has_source and voice_present(voice)
            self.voice_combo.setItemText(index, name if installed else f"{name} · 190 MB download")
        ready = has_source and voice_present(self.voice_combo.currentData())
        self.ready_label.setText("●  Voice ready offline" if ready else "○  Voice needs download")
        self.ready_label.setStyleSheet("color: #65dabd;" if ready else "color: #e4bb7e;")
        self.generate_btn.setEnabled(ready and not self.active_thread)

    def start(self, work, title):
        if self.active_thread:
            return
        self.status_label.setText(title)
        self.progress.setRange(0, 0)
        self.install_btn.setEnabled(False)
        self.gpu_btn.setEnabled(False)
        self.voice_combo.setEnabled(False)
        self.generate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.active_work = work
        self.active_thread = QThread(self)
        work.moveToThread(self.active_thread)
        self.active_thread.started.connect(work.run)
        work.status.connect(self.status_label.setText)
        work.done.connect(lambda result: self.success(work.mode, result))
        work.failed.connect(self.error)
        work.stopped.connect(self.operation_stopped)
        work.finished.connect(self.active_thread.quit)
        work.finished.connect(work.deleteLater)
        self.active_thread.finished.connect(self.thread_finished)
        self.active_thread.start()

    def install_model(self):
        if self.active_thread:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Download voices")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Choose which Nara Mini voices to keep available offline."))
        choices = {}
        has_source = source_present()
        for voice, name in VOICE_NAMES.items():
            installed = has_source and voice_present(voice)
            choice = QCheckBox(f"{name} · {'Installed' if installed else '190 MB'}")
            choice.setEnabled(not installed)
            choice.setChecked(not installed and voice == self.voice_combo.currentData())
            choices[voice] = choice
            layout.addWidget(choice)
        total = QLabel()
        layout.addWidget(total)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        download = buttons.addButton("Download selected", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        def update_total():
            count = sum(choice.isChecked() for choice in choices.values())
            total.setText(f"About {190 * count:,} MB of voice files")
            download.setEnabled(count > 0)

        for choice in choices.values():
            choice.toggled.connect(update_total)
        update_total()
        if dialog.exec():
            voices = tuple(voice for voice, choice in choices.items() if choice.isChecked())
            if self.voice_combo.currentData() not in voices:
                self.voice_combo.setCurrentIndex(self.voice_combo.findData(voices[0]))
            self.start(Work("setup", voices=voices), "Downloading selected voices…")

    def install_gpu(self):
        if self.active_thread:
            return
        answer = QMessageBox.question(
            self, "Optional NVIDIA GPU support",
            "Install ONNX Runtime GPU into this app's Python environment?\n\n"
            "Requires a supported NVIDIA GPU, drivers, and CUDA/cuDNN libraries matching "
            "the installed ONNX Runtime GPU package. AMD/Intel GPUs are not supported "
            "by this CUDA option. CPU mode remains available.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.start(Work("gpu_setup"), "Installing CUDA ONNX Runtime …")

    def generate(self):
        txt = self.editor.toPlainText().strip()
        if not txt:
            QMessageBox.warning(self, "Missing text", "Please enter some text first.")
            return
        if len(txt) > 18000:
            QMessageBox.warning(self, "Long text", "Use 18,000 characters or fewer per generation.")
            return
        self.player.stop()
        self.start(Work(
            "generate", self.voice_combo.currentData(), txt, self.thread_spin.value(),
            self.device_combo.currentData(), normalize_numbers=self.normalize_numbers.isChecked(),
        ), "Generating speech locally…")

    def success(self, mode, result):
        if mode in ("setup", "gpu_setup"):
            self.status_label.setText(result)
            self.update_install_state()
        else:
            self.latest_file = Path(result)
            self.output_label.setText(f"✓  {self.latest_file.name}")
            self.play_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.status_label.setText("Speech generated successfully. Ready to play or export.")
            self.player.setSource(QUrl.fromLocalFile(str(self.latest_file)))
            self.player.play()

    def error(self, message, details=""):
        self.status_label.setText("Operation failed. See error details.")
        box = QMessageBox(QMessageBox.Icon.Critical, "mimo-myanmar", message, parent=self)
        box.setTextFormat(Qt.TextFormat.PlainText)
        if details:
            box.setDetailedText(details[-4500:])
        box.exec()

    def operation_stopped(self):
        self.status_label.setText("Operation cancelled.")

    def thread_finished(self):
        self.active_thread.deleteLater()
        self.active_thread = None
        self.active_work = None
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.cancel_btn.setEnabled(False)
        self.install_btn.setEnabled(True)
        self.gpu_btn.setEnabled(True)
        self.voice_combo.setEnabled(True)
        self.update_install_state()

    def cancel(self):
        if self.active_work:
            self.active_work.cancel()
            self.cancel_btn.setEnabled(False)
            self.status_label.setText("Stopping …")

    def play_pause(self):
        if not self.latest_file:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.source().isEmpty():
                self.player.setSource(QUrl.fromLocalFile(str(self.latest_file)))
            self.player.play()

    def playback_changed(self, state):
        self.play_btn.setText("Ⅱ  Pause" if state == QMediaPlayer.PlaybackState.PlayingState else "▶  Play")

    def save_as(self):
        if not self.latest_file:
            return
        name, _ = QFileDialog.getSaveFileName(self, "Export WAV", str(Path.home() / "Desktop" / self.latest_file.name), "Wave audio (*.wav)")
        if name:
            try:
                if Path(name).resolve() != self.latest_file.resolve():
                    shutil.copy2(self.latest_file, name)
                self.status_label.setText(f"Saved: {name}")
            except OSError as exc:
                QMessageBox.critical(self, "Export failed", str(exc))

    def open_folder(self):
        try:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.error("Could not create the audio output folder.", str(exc))
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(OUT_DIR))):
            self.error("Windows could not open the audio output folder.", str(OUT_DIR))

    def about(self):
        QMessageBox.information(
            self, "About mimo-myanmar",
            '<p>mimo-myanmar is an open-source desktop app by '
            '<a href="https://github.com/thurahex">ThuraHex on GitHub</a>, developed with AI assistance.</p>'
            '<p>Uses <a href="https://huggingface.co/YeeNyunn/nara-mini-v1">Nara Mini v1</a> by '
            '<a href="https://naraaudio.app">Nara contributors</a>, a Kokoro-based Burmese and English speech model.</p>'
            "<p>"
            "Nara Mini v1 is licensed under Apache 2.0. The model's LICENSE and NOTICE "
            "are included in the model folder after installation.</p>"
        )

    def closeEvent(self, event):
        if self.active_thread:
            QMessageBox.information(self, "Task running", "Stop the current task before closing the app.")
            event.ignore()
            return
        self.player.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("mimo-myanmar")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    win = Main()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
