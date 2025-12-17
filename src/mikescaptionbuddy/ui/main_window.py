"""Main application window."""

import os
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QToolBar, QStatusBar, QFileDialog, QMessageBox,
    QLabel, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QKeySequence, QCloseEvent

from ..core import ProjectManager, Settings, UndoManager, Project
from .video_panel import VideoPanel
from .timeline_panel import TimelinePanel
from .caption_panel import CaptionPanel
from .dialogs import StartupDialog, SettingsDialog, TranscribeDialog, ExportDialog, StylesManagerDialog


class MainWindow(QMainWindow):
    """Main application window with three-panel layout."""

    def __init__(self):
        super().__init__()

        # Core services
        self.settings = Settings.load()
        self.project_manager = ProjectManager(self)
        self.undo_manager = UndoManager(self)

        # Setup UI
        self._setup_window()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_panels()
        self._setup_status_bar()
        self._connect_signals()

        # Apply settings
        self._apply_settings()

        # Show startup dialog if enabled
        if self.settings.show_startup_dialog:
            QTimer.singleShot(100, self._show_startup_dialog)

    def _setup_window(self) -> None:
        """Setup main window properties."""
        self.setWindowTitle("MikesCaptionBuddy")
        self.setMinimumSize(1200, 800)

        # Restore window size
        self.resize(self.settings.window_width, self.settings.window_height)
        if self.settings.window_maximized:
            self.showMaximized()

    def _setup_menu_bar(self) -> None:
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        self.action_open = QAction("&Open Video...", self)
        self.action_open.setShortcut(QKeySequence.Open)
        self.action_open.triggered.connect(self._on_open_video)
        file_menu.addAction(self.action_open)

        self.action_import_audio = QAction("Import &Audio...", self)
        self.action_import_audio.triggered.connect(self._on_import_audio)
        file_menu.addAction(self.action_import_audio)

        # Recent files submenu
        self.recent_menu = file_menu.addMenu("Open &Recent")
        self._update_recent_menu()

        file_menu.addSeparator()

        self.action_save = QAction("&Save Project", self)
        self.action_save.setShortcut(QKeySequence.Save)
        self.action_save.triggered.connect(self._on_save_project)
        self.action_save.setEnabled(False)
        file_menu.addAction(self.action_save)

        self.action_save_as = QAction("Save Project &As...", self)
        self.action_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.action_save_as.triggered.connect(self._on_save_project_as)
        self.action_save_as.setEnabled(False)
        file_menu.addAction(self.action_save_as)

        file_menu.addSeparator()

        self.action_export_subtitles = QAction("Export &Subtitles...", self)
        self.action_export_subtitles.triggered.connect(self._on_export_subtitles)
        self.action_export_subtitles.setEnabled(False)
        file_menu.addAction(self.action_export_subtitles)

        self.action_export_video = QAction("&Export Video...", self)
        self.action_export_video.setShortcut(QKeySequence("Ctrl+E"))
        self.action_export_video.triggered.connect(self._on_export_video)
        self.action_export_video.setEnabled(False)
        file_menu.addAction(self.action_export_video)

        file_menu.addSeparator()

        action_exit = QAction("E&xit", self)
        action_exit.setShortcut(QKeySequence.Quit)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        self.action_undo = QAction("&Undo", self)
        self.action_undo.setShortcut(QKeySequence.Undo)
        self.action_undo.triggered.connect(self._on_undo)
        self.action_undo.setEnabled(False)
        edit_menu.addAction(self.action_undo)

        self.action_redo = QAction("&Redo", self)
        self.action_redo.setShortcut(QKeySequence.Redo)
        self.action_redo.triggered.connect(self._on_redo)
        self.action_redo.setEnabled(False)
        edit_menu.addAction(self.action_redo)

        edit_menu.addSeparator()

        self.action_split = QAction("&Split Subtitle", self)
        self.action_split.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.action_split.triggered.connect(self._on_split_subtitle)
        self.action_split.setEnabled(False)
        edit_menu.addAction(self.action_split)

        self.action_merge = QAction("&Merge Subtitles", self)
        self.action_merge.setShortcut(QKeySequence("Ctrl+Shift+M"))
        self.action_merge.triggered.connect(self._on_merge_subtitles)
        self.action_merge.setEnabled(False)
        edit_menu.addAction(self.action_merge)

        self.action_shift = QAction("Shift &Timings...", self)
        self.action_shift.triggered.connect(self._on_shift_timings)
        self.action_shift.setEnabled(False)
        edit_menu.addAction(self.action_shift)

        # View menu
        view_menu = menubar.addMenu("&View")

        self.action_toggle_waveform = QAction("Toggle &Waveform", self)
        self.action_toggle_waveform.setCheckable(True)
        self.action_toggle_waveform.setChecked(True)
        self.action_toggle_waveform.triggered.connect(self._on_toggle_waveform)
        view_menu.addAction(self.action_toggle_waveform)

        self.action_show_styles = QAction("Show &Styles Panel", self)
        self.action_show_styles.triggered.connect(self._on_show_styles)
        view_menu.addAction(self.action_show_styles)

        view_menu.addSeparator()

        self.action_fullscreen = QAction("&Fullscreen Preview", self)
        self.action_fullscreen.setShortcut(QKeySequence("F11"))
        self.action_fullscreen.triggered.connect(self._on_fullscreen)
        view_menu.addAction(self.action_fullscreen)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        self.action_transcribe = QAction("&Transcribe (Whisper)...", self)
        self.action_transcribe.setShortcut(QKeySequence("Ctrl+T"))
        self.action_transcribe.triggered.connect(self._on_transcribe)
        self.action_transcribe.setEnabled(False)
        tools_menu.addAction(self.action_transcribe)

        tools_menu.addSeparator()

        self.action_styles_manager = QAction("Style &Presets Manager...", self)
        self.action_styles_manager.triggered.connect(self._on_styles_manager)
        tools_menu.addAction(self.action_styles_manager)

        tools_menu.addSeparator()

        self.action_settings = QAction("&Settings...", self)
        self.action_settings.triggered.connect(self._on_settings)
        tools_menu.addAction(self.action_settings)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        action_getting_started = QAction("&Getting Started", self)
        action_getting_started.triggered.connect(self._on_getting_started)
        help_menu.addAction(action_getting_started)

        action_shortcuts = QAction("&Keyboard Shortcuts", self)
        action_shortcuts.triggered.connect(self._on_shortcuts)
        help_menu.addAction(action_shortcuts)

        help_menu.addSeparator()

        action_about = QAction("&About MikesCaptionBuddy", self)
        action_about.triggered.connect(self._on_about)
        help_menu.addAction(action_about)

    def _setup_toolbar(self) -> None:
        """Setup the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_save)
        toolbar.addSeparator()
        toolbar.addAction(self.action_undo)
        toolbar.addAction(self.action_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.action_transcribe)
        toolbar.addAction(self.action_styles_manager)
        toolbar.addAction(self.action_export_video)
        toolbar.addAction(self.action_export_subtitles)

    def _setup_panels(self) -> None:
        """Setup the three-panel layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Main splitter (horizontal: video+caption panels | timeline at bottom)
        main_splitter = QSplitter(Qt.Vertical)

        # Top area splitter (video panel | caption panel)
        top_splitter = QSplitter(Qt.Horizontal)

        # Video preview panel (left)
        self.video_panel = VideoPanel(self)
        top_splitter.addWidget(self.video_panel)

        # Caption editor panel (right)
        self.caption_panel = CaptionPanel(self)
        self.caption_panel.set_settings(self.settings)
        top_splitter.addWidget(self.caption_panel)

        # Set initial sizes (60% video, 40% caption)
        top_splitter.setSizes([600, 400])

        main_splitter.addWidget(top_splitter)

        # Timeline/waveform panel (bottom)
        self.timeline_panel = TimelinePanel(self)
        main_splitter.addWidget(self.timeline_panel)

        # Set initial sizes (70% top, 30% timeline)
        main_splitter.setSizes([700, 300])

        main_layout.addWidget(main_splitter)

    def _setup_status_bar(self) -> None:
        """Setup the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Project status label
        self.status_label = QLabel("Ready")
        self.statusbar.addWidget(self.status_label, 1)

        # Time position label
        self.time_label = QLabel("00:00:00 / 00:00:00")
        self.statusbar.addPermanentWidget(self.time_label)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusbar.addPermanentWidget(self.progress_bar)

    def _connect_signals(self) -> None:
        """Connect signals between components."""
        # Project manager signals
        self.project_manager.project_loaded.connect(self._on_project_loaded)
        self.project_manager.project_saved.connect(self._on_project_saved)
        self.project_manager.project_modified.connect(self._on_project_modified)
        self.project_manager.auto_save_triggered.connect(self._on_auto_saved)

        # Undo manager signals
        self.undo_manager.can_undo_changed.connect(self.action_undo.setEnabled)
        self.undo_manager.can_redo_changed.connect(self.action_redo.setEnabled)

        # Video panel signals
        self.video_panel.position_changed.connect(self._on_video_position_changed)
        self.video_panel.duration_changed.connect(self._on_video_duration_changed)

        # Timeline panel signals
        self.timeline_panel.position_changed.connect(self.video_panel.seek)
        self.timeline_panel.subtitle_selected.connect(self.caption_panel.select_subtitle)
        self.timeline_panel.subtitle_timing_changed.connect(self._on_subtitle_timing_changed)
        self.timeline_panel.subtitles_selected.connect(self._on_timeline_selection_changed)

        # Caption panel signals
        self.caption_panel.subtitle_changed.connect(self._on_subtitle_changed)
        self.caption_panel.subtitles_changed.connect(self._on_subtitles_changed)
        self.caption_panel.word_style_changed.connect(self._on_word_style_changed)
        self.caption_panel.subtitles_selected.connect(self._on_caption_selection_changed)

    def _apply_settings(self) -> None:
        """Apply settings to the application."""
        self.project_manager.set_auto_save_interval(self.settings.auto_save_interval_seconds)

    def _update_recent_menu(self) -> None:
        """Update the recent files menu."""
        self.recent_menu.clear()

        if not self.settings.recent_files:
            action = QAction("(No recent files)", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
            return

        for path in self.settings.recent_files:
            if os.path.exists(path):
                action = QAction(os.path.basename(path), self)
                action.setData(path)
                action.triggered.connect(lambda checked, p=path: self._open_recent_file(p))
                self.recent_menu.addAction(action)

        self.recent_menu.addSeparator()
        action_clear = QAction("Clear Recent Files", self)
        action_clear.triggered.connect(self._clear_recent_files)
        self.recent_menu.addAction(action_clear)

    def _update_window_title(self) -> None:
        """Update the window title with project info."""
        title = "MikesCaptionBuddy"
        if self.project_manager.current_project:
            name = self.project_manager.current_project.name
            if self.project_manager.is_modified():
                name += " *"
            title = f"{name} - {title}"
        self.setWindowTitle(title)

    def _enable_project_actions(self, enabled: bool) -> None:
        """Enable or disable project-related actions."""
        self.action_save.setEnabled(enabled)
        self.action_save_as.setEnabled(enabled)
        self.action_export_subtitles.setEnabled(enabled)
        self.action_export_video.setEnabled(enabled)
        self.action_transcribe.setEnabled(enabled)
        self.action_split.setEnabled(enabled)
        self.action_merge.setEnabled(enabled)
        self.action_shift.setEnabled(enabled)

    # Slots

    def _show_startup_dialog(self) -> None:
        """Show the startup dialog."""
        dialog = StartupDialog(self.settings, self)
        result = dialog.exec()

        if result == StartupDialog.OpenVideo:
            self._on_open_video()
        elif result == StartupDialog.OpenRecent and dialog.selected_recent:
            self._open_recent_file(dialog.selected_recent)

    @Slot()
    def _on_open_video(self) -> None:
        """Open a video file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Video",
            "",
            "Video Files (*.mp4 *.mkv *.mov);;All Files (*)"
        )
        if path:
            self._load_video(path)

    @Slot()
    def _on_import_audio(self) -> None:
        """Import an audio file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Audio",
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.flac);;All Files (*)"
        )
        if path:
            self._load_video(path, audio_only=True)

    def _load_video(self, path: str, audio_only: bool = False) -> None:
        """Load a video or audio file."""
        # Create new project
        project = self.project_manager.new_project(os.path.basename(path))
        project.video_path = path

        # Load into video panel
        self.video_panel.load_video(path, audio_only=audio_only)

        # Set project on video panel for caption display
        self.video_panel.set_project(project)

        # Load waveform in timeline
        self.timeline_panel.load_audio(path)

        # Enable actions
        self._enable_project_actions(True)

        # Update UI
        self._update_window_title()
        self.status_label.setText(f"Loaded: {os.path.basename(path)}")

        # Add to recent files
        self.settings.add_recent_file(path)
        self._update_recent_menu()

    def _open_recent_file(self, path: str) -> None:
        """Open a recent file."""
        if path.endswith('.captionstudio'):
            self.project_manager.load_project(path)
        else:
            self._load_video(path)

    def _clear_recent_files(self) -> None:
        """Clear recent files list."""
        self.settings.clear_recent_files()
        self._update_recent_menu()

    @Slot()
    def _on_save_project(self) -> None:
        """Save the current project."""
        if self.project_manager.current_path:
            self.project_manager.save_project()
        else:
            self._on_save_project_as()

    @Slot()
    def _on_save_project_as(self) -> None:
        """Save the current project with a new name."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project",
            "",
            "Caption Studio Project (*.captionstudio)"
        )
        if path:
            self.project_manager.save_project(path)

    @Slot()
    def _on_export_subtitles(self) -> None:
        """Export subtitles to file."""
        if not self.project_manager.current_project:
            return

        project = self.project_manager.current_project

        # Get save path
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Subtitles",
            os.path.join(self.settings.get_export_directory(), f"{project.name}_subtitles"),
            "SRT Subtitles (*.srt);;ASS Subtitles (*.ass);;All Files (*)"
        )

        if not path:
            return

        try:
            if path.lower().endswith('.ass') or 'ASS' in selected_filter:
                # Export as ASS
                content = self._export_to_ass(project)
                if not path.lower().endswith('.ass'):
                    path += '.ass'
            else:
                # Export as SRT
                content = project.export_to_srt()
                if not path.lower().endswith('.srt'):
                    path += '.srt'

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.status_label.setText(f"Subtitles exported to {os.path.basename(path)}")
            QMessageBox.information(self, "Export Complete",
                                  f"Subtitles exported successfully to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export subtitles:\n{str(e)}")

    def _export_to_ass(self, project) -> str:
        """Export project to ASS format."""
        lines = [
            "[Script Info]",
            f"Title: {project.name}",
            "ScriptType: v4.00+",
            "Collisions: Normal",
            f"PlayResX: {project.video_info.width}",
            f"PlayResY: {project.video_info.height}",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        ]

        # Add styles
        for style in project.styles:
            lines.append(style.to_ass_style())

        lines.extend(["", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"])

        # Add subtitles
        def ms_to_ass_time(ms: int) -> str:
            h = ms // 3600000
            m = (ms % 3600000) // 60000
            s = (ms % 60000) // 1000
            cs = (ms % 1000) // 10
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

        for sub in project.subtitles:
            style_name = "Default"
            if sub.style_id:
                style = project.get_style_by_id(sub.style_id)
                if style:
                    style_name = style.name

            start = ms_to_ass_time(sub.start_ms)
            end = ms_to_ass_time(sub.end_ms)
            text = sub.get_full_text().replace("\n", "\\N")
            lines.append(f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}")

        return "\n".join(lines)

    @Slot()
    def _on_export_video(self) -> None:
        """Export video with burned-in captions."""
        dialog = ExportDialog(
            self.project_manager.current_project,
            self.settings,
            self
        )
        dialog.exec()

    @Slot()
    def _on_undo(self) -> None:
        """Undo last action."""
        desc = self.undo_manager.undo()
        if desc:
            self.status_label.setText(f"Undone: {desc}")

    @Slot()
    def _on_redo(self) -> None:
        """Redo last undone action."""
        desc = self.undo_manager.redo()
        if desc:
            self.status_label.setText(f"Redone: {desc}")

    @Slot()
    def _on_split_subtitle(self) -> None:
        """Split selected subtitle at cursor."""
        self.caption_panel.split_subtitle()

    @Slot()
    def _on_merge_subtitles(self) -> None:
        """Merge selected subtitles."""
        self.caption_panel.merge_subtitles()

    @Slot()
    def _on_shift_timings(self) -> None:
        """Shift subtitle timings."""
        from .dialogs import ShiftTimingsDialog
        dialog = ShiftTimingsDialog(self)
        if dialog.exec():
            shift_ms = dialog.get_shift_ms()
            self.timeline_panel.shift_all_subtitles(shift_ms)

    @Slot()
    def _on_toggle_waveform(self) -> None:
        """Toggle waveform visibility."""
        self.timeline_panel.toggle_waveform(self.action_toggle_waveform.isChecked())

    @Slot()
    def _on_show_styles(self) -> None:
        """Show styles panel."""
        self._on_styles_manager()

    @Slot()
    def _on_fullscreen(self) -> None:
        """Toggle fullscreen preview."""
        self.video_panel.toggle_fullscreen()

    @Slot()
    def _on_transcribe(self) -> None:
        """Open transcription dialog."""
        dialog = TranscribeDialog(
            self.project_manager.current_project,
            self.settings,
            self
        )
        if dialog.exec():
            # Transcription complete, update UI
            self.timeline_panel.update_subtitles()
            self.caption_panel.update_subtitles()
            # Update caption overlay on video panel
            self.video_panel.update_captions()
            self.project_manager.mark_modified()

    @Slot()
    def _on_styles_manager(self) -> None:
        """Open styles manager dialog."""
        dialog = StylesManagerDialog(
            self.project_manager.current_project,
            self.settings,
            self
        )
        # Connect styles_updated signal to refresh UI
        dialog.styles_updated.connect(self._on_styles_updated)
        dialog.exec()

    @Slot()
    def _on_styles_updated(self) -> None:
        """Handle styles updated from styles manager."""
        # Update caption panel's style dropdown
        self.caption_panel._update_style_combo()
        # Refresh subtitles on video (regenerate ASS file)
        self.video_panel.refresh_subtitles()
        # Mark project as modified
        self.project_manager.mark_modified()

    @Slot()
    def _on_settings(self) -> None:
        """Open settings dialog."""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self._apply_settings()

    @Slot()
    def _on_getting_started(self) -> None:
        """Show getting started help."""
        QMessageBox.information(
            self, "Getting Started",
            "<h3>MikesCaptionBuddy - Quick Start</h3>"
            "<ol>"
            "<li><b>Open Video:</b> File → Open Video</li>"
            "<li><b>Transcribe:</b> Tools → Transcribe (Whisper)</li>"
            "<li><b>Edit:</b> Click subtitles in timeline to edit</li>"
            "<li><b>Style:</b> Right-click words to change colors, fonts</li>"
            "<li><b>Preview:</b> Press Space to play/pause</li>"
            "<li><b>Export:</b> File → Export Video</li>"
            "</ol>"
        )

    @Slot()
    def _on_shortcuts(self) -> None:
        """Show keyboard shortcuts."""
        QMessageBox.information(
            self, "Keyboard Shortcuts",
            "<h3>Keyboard Shortcuts</h3>"
            "<table>"
            "<tr><td><b>Space</b></td><td>Play/Pause</td></tr>"
            "<tr><td><b>Ctrl+O</b></td><td>Open Video</td></tr>"
            "<tr><td><b>Ctrl+S</b></td><td>Save Project</td></tr>"
            "<tr><td><b>Ctrl+E</b></td><td>Export Video</td></tr>"
            "<tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>"
            "<tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr>"
            "<tr><td><b>Ctrl+T</b></td><td>Transcribe</td></tr>"
            "<tr><td><b>Left/Right</b></td><td>Nudge timing ±100ms</td></tr>"
            "<tr><td><b>Shift+Left/Right</b></td><td>Nudge timing ±1s</td></tr>"
            "<tr><td><b>F11</b></td><td>Fullscreen Preview</td></tr>"
            "</table>"
        )

    @Slot()
    def _on_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self, "About MikesCaptionBuddy",
            "<h2>MikesCaptionBuddy</h2>"
            "<p>Version 1.0</p>"
            "<p>All-in-One Caption Studio</p>"
            "<p>Create beautiful, animated captions for your videos "
            "with word-by-word styling and karaoke effects.</p>"
            "<p>Author: Mike</p>"
        )

    @Slot(object)
    def _on_project_loaded(self, project: Project) -> None:
        """Handle project loaded."""
        self._enable_project_actions(True)
        self._update_window_title()

        # Update panels
        if project.video_path:
            self.video_panel.load_video(project.video_path)
            self.timeline_panel.load_audio(project.video_path)

        self.video_panel.set_project(project)
        self.timeline_panel.set_project(project)
        self.caption_panel.set_project(project)

    @Slot(str)
    def _on_project_saved(self, path: str) -> None:
        """Handle project saved."""
        self._update_window_title()
        self.status_label.setText(f"Saved: {os.path.basename(path)}")

    @Slot()
    def _on_project_modified(self) -> None:
        """Handle project modified."""
        self._update_window_title()

    @Slot()
    def _on_auto_saved(self) -> None:
        """Handle auto-save."""
        self.status_label.setText("Auto-saved")
        QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))

    @Slot(int)
    def _on_video_position_changed(self, position_ms: int) -> None:
        """Handle video position change."""
        self.timeline_panel.set_position(position_ms)
        self._update_time_label(position_ms)
        self.video_panel.update_captions()

    @Slot(int)
    def _on_video_duration_changed(self, duration_ms: int) -> None:
        """Handle video duration change."""
        self.timeline_panel.set_duration(duration_ms)
        if self.project_manager.current_project:
            self.project_manager.current_project.video_info.duration_ms = duration_ms

    def _update_time_label(self, position_ms: int) -> None:
        """Update the time label in status bar."""
        duration_ms = self.video_panel.get_duration()

        def format_time(ms: int) -> str:
            s = ms // 1000
            m = s // 60
            h = m // 60
            return f"{h:02d}:{m % 60:02d}:{s % 60:02d}"

        self.time_label.setText(f"{format_time(position_ms)} / {format_time(duration_ms)}")

    @Slot(object)
    def _on_subtitle_changed(self, subtitle) -> None:
        """Handle subtitle content change."""
        self.timeline_panel.update_subtitle(subtitle)
        self.video_panel.refresh_subtitles()
        self.project_manager.mark_modified()

    @Slot(list)
    def _on_subtitles_changed(self, subtitles: list) -> None:
        """Handle multiple subtitles changed (e.g., Apply to Selected)."""
        self.timeline_panel.update_subtitles()
        self.video_panel.refresh_subtitles()
        self.project_manager.mark_modified()

    @Slot(int, int, dict)
    def _on_word_style_changed(self, subtitle_id: int, word_index: int, style: dict) -> None:
        """Handle word style change."""
        self.video_panel.refresh_subtitles()
        self.project_manager.mark_modified()

    @Slot(object, int, int, int, int)
    def _on_subtitle_timing_changed(self, subtitle, old_start: int, old_end: int, new_start: int, new_end: int) -> None:
        """Handle subtitle timing change from timeline drag (with undo support)."""
        from ..core.undo_manager import SubtitleTimingCommand

        # Create undo command
        command = SubtitleTimingCommand(
            subtitle_id=subtitle.id,
            old_start=old_start,
            old_end=old_end,
            new_start=new_start,
            new_end=new_end,
            get_subtitle=lambda sid: self.project_manager.current_project.get_subtitle_by_id(sid) if self.project_manager.current_project else None,
            on_change=self._on_timeline_undo_change
        )

        # Add to undo stack without re-executing (timing already applied by drag)
        self.undo_manager._undo_stack.append(command)
        self.undo_manager._redo_stack.clear()
        self.undo_manager._emit_changes()

        self.timeline_panel.update_subtitles()
        self.caption_panel.update_subtitles()
        self.project_manager.mark_modified()

    def _on_timeline_undo_change(self) -> None:
        """Callback for timeline undo/redo operations."""
        self.timeline_panel.update_subtitles()
        self.caption_panel.update_subtitles()
        self.video_panel.update_captions()
        self.project_manager.mark_modified()

    @Slot(list)
    def _on_timeline_selection_changed(self, subtitles: list) -> None:
        """Handle selection change in timeline - sync to caption panel."""
        self._syncing_selection = True
        self.caption_panel.select_subtitles(subtitles)
        self._syncing_selection = False

    @Slot(list)
    def _on_caption_selection_changed(self, subtitles: list) -> None:
        """Handle selection change in caption panel - sync to timeline."""
        if getattr(self, '_syncing_selection', False):
            return
        # Sync selection to timeline
        self.timeline_panel.waveform._selected_subtitles.clear()
        for sub in subtitles:
            if sub.id:
                self.timeline_panel.waveform._selected_subtitles.add(sub.id)
        self.timeline_panel.waveform.update()
        self.timeline_panel._update_selection_label()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        if self.project_manager.is_modified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                self._on_save_project()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return

        # Save window state
        self.settings.window_width = self.width()
        self.settings.window_height = self.height()
        self.settings.window_maximized = self.isMaximized()
        self.settings.save()

        # Cleanup
        self.video_panel.cleanup()
        self.project_manager.stop_auto_save()

        event.accept()
