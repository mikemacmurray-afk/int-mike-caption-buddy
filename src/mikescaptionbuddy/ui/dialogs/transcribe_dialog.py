"""Transcription dialog using Whisper."""

import os
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QTextEdit, QGroupBox, QFormLayout,
    QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

from ...core.models import Project, Subtitle
from ...core.settings import Settings


class TranscriptionWorker(QThread):
    """Worker thread for transcription."""

    progress = Signal(int, str)  # progress %, status message
    finished = Signal(list)  # list of subtitles
    error = Signal(str)  # error message

    def __init__(self, audio_path: str, model: str, language: str):
        super().__init__()
        self.audio_path = audio_path
        self.model = model
        self.language = language
        self._cancelled = False

    def run(self) -> None:
        """Run transcription."""
        try:
            self.progress.emit(0, "Loading Whisper model...")

            import whisper

            # Load model
            self.progress.emit(10, f"Loading {self.model} model...")
            model = whisper.load_model(self.model)

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

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("Transcribe with Whisper")
        self.setMinimumSize(450, 350)

        layout = QVBoxLayout(self)

        # Info
        info = QLabel(
            "Whisper will analyze your video's audio and generate captions.\n"
            "Larger models are more accurate but slower."
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
            language
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

        self._log("Starting transcription...")

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

        # Add new subtitles
        for subtitle in subtitles:
            self.project.subtitles.append(subtitle)

        self._log(f"Transcription complete! Generated {len(subtitles)} subtitles.")

        QMessageBox.information(
            self, "Transcription Complete",
            f"Successfully generated {len(subtitles)} subtitle segments."
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
