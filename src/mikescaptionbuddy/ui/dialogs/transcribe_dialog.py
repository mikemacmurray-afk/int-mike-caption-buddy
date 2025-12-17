"""Transcription dialog using Whisper."""

import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QTextEdit, QGroupBox, QFormLayout,
    QMessageBox, QLineEdit, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal

from ...core.models import Project, Subtitle
from ...core.settings import Settings


def get_whisper_cache_dir() -> str:
    """Get the default Whisper cache directory."""
    # Check environment variable first
    if 'WHISPER_CACHE' in os.environ:
        return os.environ['WHISPER_CACHE']

    # Default locations
    if os.name == 'nt':  # Windows
        # Common locations on Windows
        candidates = [
            os.path.join(os.environ.get('USERPROFILE', ''), '.cache', 'whisper'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'whisper'),
            os.path.join(os.environ.get('APPDATA', ''), 'whisper'),
        ]
    else:
        candidates = [
            os.path.join(os.path.expanduser('~'), '.cache', 'whisper'),
        ]

    # Return first existing directory, or default
    for path in candidates:
        if os.path.isdir(path):
            return path

    # Default to user's .cache/whisper
    return os.path.join(os.path.expanduser('~'), '.cache', 'whisper')


def check_model_exists(model_name: str, cache_dir: str) -> bool:
    """Check if a Whisper model exists in the cache directory."""
    model_file = f"{model_name}.pt"
    model_path = os.path.join(cache_dir, model_file)
    return os.path.exists(model_path)


class TranscriptionWorker(QThread):
    """Worker thread for transcription."""

    progress = Signal(int, str)  # progress %, status message
    finished = Signal(list)  # list of subtitles
    error = Signal(str)  # error message

    def __init__(self, audio_path: str, model: str, language: str, cache_dir: str = None):
        super().__init__()
        self.audio_path = audio_path
        self.model = model
        self.language = language
        self.cache_dir = cache_dir or get_whisper_cache_dir()
        self._cancelled = False

    def run(self) -> None:
        """Run transcription."""
        try:
            self.progress.emit(0, "Loading Whisper model...")

            import whisper

            # Check if model exists locally
            model_exists = check_model_exists(self.model, self.cache_dir)

            if model_exists:
                self.progress.emit(10, f"Loading {self.model} model from local cache...")
            else:
                self.progress.emit(10, f"Model {self.model} not found locally. Downloading...")

            # Load model with explicit download directory to use existing cache
            model = whisper.load_model(
                self.model,
                download_root=self.cache_dir
            )

            if self._cancelled:
                return

            # Transcribe
            self.progress.emit(30, "Transcribing audio...")

            result = model.transcribe(
                self.audio_path,
                language=self.language if self.language != "auto" else None,
                word_timestamps=True,
                verbose=False
            )

            if self._cancelled:
                return

            self.progress.emit(80, "Processing segments...")

            # Convert to subtitles
            subtitles = []
            for i, segment in enumerate(result.get('segments', [])):
                subtitle = Subtitle(
                    id=i + 1,
                    start_ms=int(segment['start'] * 1000),
                    end_ms=int(segment['end'] * 1000),
                    text=segment['text'].strip()
                )

                # Add word-level timing if available
                if 'words' in segment:
                    subtitle.words = []
                    for j, word_data in enumerate(segment['words']):
                        from ...core.models import Word
                        word = Word(
                            subtitle_id=subtitle.id,
                            word_index=j,
                            text=word_data.get('word', '').strip(),
                            start_ms=int(word_data.get('start', 0) * 1000),
                            end_ms=int(word_data.get('end', 0) * 1000)
                        )
                        subtitle.words.append(word)

                subtitles.append(subtitle)

            self.progress.emit(100, "Done!")
            self.finished.emit(subtitles)

        except ImportError:
            self.error.emit("Whisper is not installed. Please install openai-whisper.")
        except Exception as e:
            self.error.emit(f"Transcription failed: {str(e)}")

    def cancel(self) -> None:
        """Cancel the transcription."""
        self._cancelled = True


class TranscribeDialog(QDialog):
    """Dialog for transcribing audio using Whisper."""

    def __init__(self, project: Project, settings: Settings, parent=None):
        super().__init__(parent)
        self.project = project
        self.settings = settings
        self.worker: Optional[TranscriptionWorker] = None
        self.cache_dir = get_whisper_cache_dir()

        self._setup_ui()
        self._check_available_models()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("Transcribe with Whisper")
        self.setMinimumSize(500, 420)

        layout = QVBoxLayout(self)

        # Info
        info = QLabel(
            "Whisper will analyze your video's audio and generate captions.\n"
            "Using locally installed Whisper models (no download needed if models exist)."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Settings group
        settings_group = QGroupBox("Transcription Settings")
        settings_form = QFormLayout(settings_group)

        self.combo_model = QComboBox()
        self.combo_model.addItem("small - Fast, good accuracy", "small")
        self.combo_model.addItem("medium - Balanced", "medium")
        self.combo_model.addItem("large - Best accuracy, slowest", "large")

        # Set default from settings
        for i in range(self.combo_model.count()):
            if self.settings.default_whisper_model in self.combo_model.itemData(i):
                self.combo_model.setCurrentIndex(i)
                break

        settings_form.addRow("Model:", self.combo_model)

        self.combo_language = QComboBox()
        self.combo_language.addItem("English", "en")
        self.combo_language.addItem("Auto-detect", "auto")
        settings_form.addRow("Language:", self.combo_language)

        layout.addWidget(settings_group)

        # Model cache location
        cache_group = QGroupBox("Whisper Model Location")
        cache_layout = QVBoxLayout(cache_group)

        cache_path_layout = QHBoxLayout()
        self.edit_cache_dir = QLineEdit(self.cache_dir)
        self.edit_cache_dir.setReadOnly(True)
        cache_path_layout.addWidget(self.edit_cache_dir)

        btn_browse_cache = QPushButton("Browse...")
        btn_browse_cache.clicked.connect(self._browse_cache_dir)
        cache_path_layout.addWidget(btn_browse_cache)

        cache_layout.addLayout(cache_path_layout)

        # Model status labels
        self.model_status_label = QLabel()
        self.model_status_label.setWordWrap(True)
        cache_layout.addWidget(self.model_status_label)

        layout.addWidget(cache_group)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to transcribe")
        progress_layout.addWidget(self.status_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        progress_layout.addWidget(self.log_text)

        layout.addWidget(progress_group)

        # Buttons
        buttons = QHBoxLayout()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel)
        buttons.addWidget(self.btn_cancel)

        buttons.addStretch()

        self.btn_transcribe = QPushButton("Start Transcription")
        self.btn_transcribe.setDefault(True)
        self.btn_transcribe.clicked.connect(self._on_transcribe)
        buttons.addWidget(self.btn_transcribe)

        layout.addLayout(buttons)

    def _check_available_models(self) -> None:
        """Check which models are available locally."""
        models = ['small', 'medium', 'large']
        available = []
        missing = []

        for model in models:
            if check_model_exists(model, self.cache_dir):
                available.append(model)
            else:
                missing.append(model)

        if available:
            status = f"Available locally: {', '.join(available)}"
            if missing:
                status += f"\nNot found (will download): {', '.join(missing)}"
            self.model_status_label.setText(status)
            self.model_status_label.setStyleSheet("color: #4a9;")
        else:
            self.model_status_label.setText(
                "No models found locally. Models will be downloaded on first use.\n"
                "If you have Whisper models installed elsewhere, use Browse to locate them."
            )
            self.model_status_label.setStyleSheet("color: #a94;")

    def _browse_cache_dir(self) -> None:
        """Browse for Whisper cache directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Whisper Models Directory",
            self.cache_dir
        )
        if path:
            self.cache_dir = path
            self.edit_cache_dir.setText(path)
            self._check_available_models()

    def _on_transcribe(self) -> None:
        """Start transcription."""
        if not self.project.video_path:
            QMessageBox.warning(self, "No Video", "Please load a video first.")
            return

        if not os.path.exists(self.project.video_path):
            QMessageBox.warning(self, "File Not Found",
                              f"Video file not found: {self.project.video_path}")
            return

        # Disable controls
        self.btn_transcribe.setEnabled(False)
        self.combo_model.setEnabled(False)
        self.combo_language.setEnabled(False)

        # Start worker
        model = self.combo_model.currentData()
        language = self.combo_language.currentData()

        self.worker = TranscriptionWorker(
            self.project.video_path,
            model,
            language,
            self.cache_dir
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

        self._log("Starting transcription...")
        self._log(f"Using model cache: {self.cache_dir}")

    def _on_cancel(self) -> None:
        """Cancel transcription or close dialog."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            self._log("Transcription cancelled.")
            self._reset_ui()
        else:
            self.reject()

    def _on_progress(self, progress: int, status: str) -> None:
        """Handle progress update."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
        self._log(status)

    def _on_finished(self, subtitles: list) -> None:
        """Handle transcription complete."""
        # Clear existing subtitles
        self.project.subtitles.clear()

        # Get the first style ID to apply to all subtitles
        first_style_id = None
        if self.project.styles:
            first_style_id = self.project.styles[0].id
            self._log(f"Applying style '{self.project.styles[0].name}' to all subtitles")

        # Add new subtitles with first style applied
        for subtitle in subtitles:
            if first_style_id is not None:
                subtitle.style_id = first_style_id
            self.project.subtitles.append(subtitle)

        self._log(f"Transcription complete! Generated {len(subtitles)} subtitles.")

        QMessageBox.information(
            self, "Transcription Complete",
            f"Successfully generated {len(subtitles)} subtitle segments.\n"
            f"Applied style: {self.project.styles[0].name if self.project.styles else 'Default'}"
        )

        self.accept()

    def _on_error(self, error: str) -> None:
        """Handle transcription error."""
        self._log(f"Error: {error}")
        QMessageBox.critical(self, "Transcription Error", error)
        self._reset_ui()

    def _reset_ui(self) -> None:
        """Reset UI to initial state."""
        self.btn_transcribe.setEnabled(True)
        self.combo_model.setEnabled(True)
        self.combo_language.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready to transcribe")

    def _log(self, message: str) -> None:
        """Add message to log."""
        self.log_text.append(message)

    def closeEvent(self, event) -> None:
        """Handle dialog close."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        event.accept()
