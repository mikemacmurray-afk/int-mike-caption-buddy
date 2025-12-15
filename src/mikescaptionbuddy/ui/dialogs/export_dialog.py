"""Export dialogs for subtitles and video."""

import os
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QCheckBox, QGroupBox, QFormLayout,
    QLineEdit, QFileDialog, QMessageBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QThread, Signal

from ...core.models import Project
from ...core.settings import Settings


class ExportSubtitlesDialog(QDialog):
    """Dialog for exporting subtitles to file."""

    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.project = project

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("Export Subtitles")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Format selection
        format_group = QGroupBox("Format")
        format_layout = QVBoxLayout(format_group)

        self.btn_group = QButtonGroup(self)

        self.radio_srt = QRadioButton("SRT - Plain text subtitles")
        self.radio_srt.setChecked(True)
        self.btn_group.addButton(self.radio_srt)
        format_layout.addWidget(self.radio_srt)

        self.radio_ass = QRadioButton("ASS - Styled subtitles (colors, fonts, effects)")
        self.btn_group.addButton(self.radio_ass)
        format_layout.addWidget(self.radio_ass)

        layout.addWidget(format_group)

        # Output path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Save to:"))

        self.edit_path = QLineEdit()
        self.edit_path.setPlaceholderText("Select output file...")
        path_layout.addWidget(self.edit_path)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_output)
        path_layout.addWidget(btn_browse)

        layout.addLayout(path_layout)

        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)

        btn_export = QPushButton("Export")
        btn_export.setDefault(True)
        btn_export.clicked.connect(self._on_export)
        buttons.addWidget(btn_export)

        layout.addLayout(buttons)

    def _browse_output(self) -> None:
        """Browse for output file."""
        if self.radio_srt.isChecked():
            filter_str = "SRT Files (*.srt)"
            ext = ".srt"
        else:
            filter_str = "ASS Files (*.ass)"
            ext = ".ass"

        # Default filename based on video
        default_name = ""
        if self.project.video_path:
            base = os.path.splitext(os.path.basename(self.project.video_path))[0]
            default_name = base + ext

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Subtitles",
            default_name,
            filter_str
        )

        if path:
            self.edit_path.setText(path)

    def _on_export(self) -> None:
        """Export subtitles."""
        path = self.edit_path.text()
        if not path:
            QMessageBox.warning(self, "No Path", "Please select an output file.")
            return

        try:
            if self.radio_srt.isChecked():
                content = self.project.export_to_srt()
            else:
                content = self._export_to_ass()

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            QMessageBox.information(
                self, "Export Complete",
                f"Subtitles exported to:\n{path}"
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self, "Export Failed",
                f"Failed to export subtitles:\n{str(e)}"
            )

    def _export_to_ass(self) -> str:
        """Export to ASS format."""
        lines = [
            "[Script Info]",
            f"Title: {self.project.name}",
            "ScriptType: v4.00+",
            "Collisions: Normal",
            f"PlayResX: {self.project.video_info.width}",
            f"PlayResY: {self.project.video_info.height}",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding"
        ]

        # Add styles
        for style in self.project.styles:
            lines.append(style.to_ass_style())

        lines.extend([
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ])

        # Add dialogue lines
        for subtitle in self.project.subtitles:
            start = self._ms_to_ass_time(subtitle.start_ms)
            end = self._ms_to_ass_time(subtitle.end_ms)

            style_name = "Default"
            if subtitle.style_id:
                style = self.project.get_style_by_id(subtitle.style_id)
                if style:
                    style_name = style.name

            # Build text with inline styles
            text = self._build_ass_text(subtitle)

            lines.append(f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}")

        return "\n".join(lines)

    def _ms_to_ass_time(self, ms: int) -> str:
        """Convert milliseconds to ASS time format."""
        h = ms // 3600000
        m = (ms % 3600000) // 60000
        s = (ms % 60000) // 1000
        cs = (ms % 1000) // 10
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def _build_ass_text(self, subtitle) -> str:
        """Build ASS text with inline overrides."""
        if not subtitle.words:
            return subtitle.text

        parts = []
        for word in subtitle.words:
            if word.has_override():
                override = word.style_override
                tags = []

                if override.color:
                    # Convert hex to ASS BGR format
                    color = override.color.lstrip('#')
                    r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
                    tags.append(f"\\c&H{b:02X}{g:02X}{r:02X}&")

                if override.bold:
                    tags.append("\\b1")
                if override.italic:
                    tags.append("\\i1")
                if override.rotation:
                    tags.append(f"\\frz{override.rotation}")
                if override.karaoke_duration:
                    tags.append(f"\\k{override.karaoke_duration}")

                if tags:
                    parts.append("{" + "".join(tags) + "}" + word.text + "{\\r}")
                else:
                    parts.append(word.text)
            else:
                parts.append(word.text)

        return " ".join(parts)


class VideoExportWorker(QThread):
    """Worker thread for video export."""

    progress = Signal(int, str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, project: Project, output_path: str,
                 resolution: str, quality: str, burn_captions: bool):
        super().__init__()
        self.project = project
        self.output_path = output_path
        self.resolution = resolution
        self.quality = quality
        self.burn_captions = burn_captions
        self._cancelled = False

    def run(self) -> None:
        """Run video export."""
        try:
            import ffmpeg
            import tempfile
            import os

            self.progress.emit(0, "Preparing export...")

            # Resolution mapping
            res_map = {
                "720p": (1280, 720),
                "1080p": (1920, 1080),
            }
            width, height = res_map.get(self.resolution, (1920, 1080))

            # Quality preset mapping
            preset_map = {
                "fast": "fast",
                "balanced": "medium",
                "quality": "slow"
            }
            preset = preset_map.get(self.quality, "medium")

            input_path = self.project.video_path

            if self.burn_captions and self.project.subtitles:
                self.progress.emit(10, "Generating subtitle file...")

                # Create temporary ASS file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.ass',
                                                   delete=False, encoding='utf-8') as f:
                    # Generate ASS content (simplified)
                    ass_content = self._generate_ass()
                    f.write(ass_content)
                    ass_path = f.name

                self.progress.emit(20, "Encoding video with captions...")

                try:
                    # Build ffmpeg command with subtitle filter
                    stream = ffmpeg.input(input_path)

                    # Apply subtitle filter
                    stream = ffmpeg.filter(stream, 'ass', ass_path)

                    # Scale to target resolution
                    stream = ffmpeg.filter(stream, 'scale', width, height)

                    # Output with encoding settings
                    stream = ffmpeg.output(
                        stream,
                        self.output_path,
                        vcodec='libx264',
                        acodec='aac',
                        preset=preset,
                        crf=23
                    )

                    # Run ffmpeg
                    ffmpeg.run(stream, overwrite_output=True, quiet=True)

                finally:
                    # Clean up temp file
                    if os.path.exists(ass_path):
                        os.unlink(ass_path)

            else:
                self.progress.emit(20, "Encoding video...")

                # Simple re-encode without captions
                stream = ffmpeg.input(input_path)
                stream = ffmpeg.filter(stream, 'scale', width, height)
                stream = ffmpeg.output(
                    stream,
                    self.output_path,
                    vcodec='libx264',
                    acodec='aac',
                    preset=preset,
                    crf=23
                )
                ffmpeg.run(stream, overwrite_output=True, quiet=True)

            self.progress.emit(100, "Export complete!")
            self.finished.emit(self.output_path)

        except ImportError:
            self.error.emit("ffmpeg-python is not installed.")
        except ffmpeg.Error as e:
            self.error.emit(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
        except Exception as e:
            self.error.emit(f"Export failed: {str(e)}")

    def _generate_ass(self) -> str:
        """Generate ASS subtitle content."""
        lines = [
            "[Script Info]",
            f"Title: {self.project.name}",
            "ScriptType: v4.00+",
            f"PlayResX: {self.project.video_info.width or 1920}",
            f"PlayResY: {self.project.video_info.height or 1080}",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding"
        ]

        for style in self.project.styles:
            lines.append(style.to_ass_style())

        lines.extend([
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ])

        for subtitle in self.project.subtitles:
            start = self._ms_to_ass(subtitle.start_ms)
            end = self._ms_to_ass(subtitle.end_ms)
            style_name = "Default"
            if subtitle.style_id:
                style = self.project.get_style_by_id(subtitle.style_id)
                if style:
                    style_name = style.name
            text = subtitle.get_full_text().replace('\n', '\\N')
            lines.append(f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}")

        return "\n".join(lines)

    def _ms_to_ass(self, ms: int) -> str:
        """Convert ms to ASS time."""
        h = ms // 3600000
        m = (ms % 3600000) // 60000
        s = (ms % 60000) // 1000
        cs = (ms % 1000) // 10
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def cancel(self) -> None:
        """Cancel export."""
        self._cancelled = True


class ExportDialog(QDialog):
    """Dialog for exporting video with captions."""

    def __init__(self, project: Project, settings: Settings, parent=None):
        super().__init__(parent)
        self.project = project
        self.settings = settings
        self.worker: Optional[VideoExportWorker] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("Export Video")
        self.setMinimumSize(450, 350)

        layout = QVBoxLayout(self)

        # Output settings
        output_group = QGroupBox("Output")
        output_form = QFormLayout(output_group)

        path_layout = QHBoxLayout()
        self.edit_path = QLineEdit()
        self.edit_path.setPlaceholderText("Select output file...")

        # Set default path
        if self.project.video_path:
            base = os.path.splitext(self.project.video_path)[0]
            self.edit_path.setText(f"{base}_captioned.mp4")

        path_layout.addWidget(self.edit_path)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_output)
        path_layout.addWidget(btn_browse)

        output_form.addRow("Save to:", path_layout)

        self.combo_resolution = QComboBox()
        self.combo_resolution.addItems(["720p", "1080p"])
        idx = self.combo_resolution.findText(self.settings.default_video_resolution)
        if idx >= 0:
            self.combo_resolution.setCurrentIndex(idx)
        output_form.addRow("Resolution:", self.combo_resolution)

        self.combo_quality = QComboBox()
        self.combo_quality.addItem("Fast (lower quality)", "fast")
        self.combo_quality.addItem("Balanced", "balanced")
        self.combo_quality.addItem("Quality (slower)", "quality")
        self.combo_quality.setCurrentIndex(1)
        output_form.addRow("Quality:", self.combo_quality)

        layout.addWidget(output_group)

        # Caption options
        caption_group = QGroupBox("Captions")
        caption_layout = QVBoxLayout(caption_group)

        self.check_burn = QCheckBox("Burn captions into video")
        self.check_burn.setChecked(True)
        caption_layout.addWidget(self.check_burn)

        self.check_export_subs = QCheckBox("Also export subtitle file (.ass)")
        caption_layout.addWidget(self.check_export_subs)

        subtitle_count = len(self.project.subtitles) if self.project else 0
        info = QLabel(f"Subtitles to include: {subtitle_count}")
        info.setStyleSheet("color: #666;")
        caption_layout.addWidget(info)

        layout.addWidget(caption_group)

        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to export")
        progress_layout.addWidget(self.status_label)

        layout.addWidget(progress_group)

        # Buttons
        buttons = QHBoxLayout()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel)
        buttons.addWidget(self.btn_cancel)

        buttons.addStretch()

        self.btn_export = QPushButton("Export")
        self.btn_export.setDefault(True)
        self.btn_export.clicked.connect(self._on_export)
        buttons.addWidget(self.btn_export)

        layout.addLayout(buttons)

    def _browse_output(self) -> None:
        """Browse for output file."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Video",
            self.edit_path.text() or "",
            "MP4 Files (*.mp4)"
        )
        if path:
            if not path.endswith('.mp4'):
                path += '.mp4'
            self.edit_path.setText(path)

    def _on_export(self) -> None:
        """Start export."""
        path = self.edit_path.text()
        if not path:
            QMessageBox.warning(self, "No Path", "Please select an output file.")
            return

        if not self.project.video_path:
            QMessageBox.warning(self, "No Video", "No video loaded.")
            return

        # Disable controls
        self.btn_export.setEnabled(False)
        self.combo_resolution.setEnabled(False)
        self.combo_quality.setEnabled(False)
        self.check_burn.setEnabled(False)

        # Start worker
        self.worker = VideoExportWorker(
            self.project,
            path,
            self.combo_resolution.currentText(),
            self.combo_quality.currentData(),
            self.check_burn.isChecked()
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_cancel(self) -> None:
        """Cancel export or close dialog."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            self._reset_ui()
        else:
            self.reject()

    def _on_progress(self, progress: int, status: str) -> None:
        """Handle progress update."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)

    def _on_finished(self, path: str) -> None:
        """Handle export complete."""
        # Export subtitle file if requested
        if self.check_export_subs.isChecked():
            ass_path = os.path.splitext(path)[0] + '.ass'
            try:
                dialog = ExportSubtitlesDialog(self.project, self)
                dialog.radio_ass.setChecked(True)
                dialog.edit_path.setText(ass_path)
                dialog._on_export()
            except Exception:
                pass  # Ignore subtitle export errors

        QMessageBox.information(
            self, "Export Complete",
            f"Video exported to:\n{path}"
        )
        self.accept()

    def _on_error(self, error: str) -> None:
        """Handle export error."""
        QMessageBox.critical(self, "Export Failed", error)
        self._reset_ui()

    def _reset_ui(self) -> None:
        """Reset UI to initial state."""
        self.btn_export.setEnabled(True)
        self.combo_resolution.setEnabled(True)
        self.combo_quality.setEnabled(True)
        self.check_burn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready to export")

    def closeEvent(self, event) -> None:
        """Handle dialog close."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        event.accept()
