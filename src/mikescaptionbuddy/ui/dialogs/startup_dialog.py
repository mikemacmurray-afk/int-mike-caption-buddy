"""Startup dialog showing quick start options."""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QCheckBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ...core.settings import Settings


class StartupDialog(QDialog):
    """Startup dialog with overview and quick actions."""

    # Result codes
    OpenVideo = 1
    OpenRecent = 2
    ShowHelp = 3

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.selected_recent: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("Welcome to MikesCaptionBuddy")
        self.setFixedSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Title
        title = QLabel("MikesCaptionBuddy")
        title.setFont(QFont("", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("All-in-One Caption Studio")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # Quick overview
        overview = QLabel(
            "<b>Quick Start:</b><br>"
            "1. Open a video file (MP4, MKV, MOV)<br>"
            "2. Transcribe with Whisper (Tools → Transcribe)<br>"
            "3. Edit and style your captions<br>"
            "4. Export video with burned-in captions"
        )
        overview.setWordWrap(True)
        layout.addWidget(overview)

        # Recent files section
        if self.settings.recent_files:
            recent_label = QLabel("<b>Recent Files:</b>")
            layout.addWidget(recent_label)

            self.recent_list = QListWidget()
            self.recent_list.setMaximumHeight(100)
            for path in self.settings.recent_files[:5]:
                item = QListWidgetItem(path)
                item.setData(Qt.UserRole, path)
                self.recent_list.addItem(item)
            self.recent_list.itemDoubleClicked.connect(self._on_recent_double_clicked)
            layout.addWidget(self.recent_list)

        layout.addStretch()

        # Don't show again checkbox
        self.checkbox_dont_show = QCheckBox("Don't show this at startup")
        self.checkbox_dont_show.setChecked(not self.settings.show_startup_dialog)
        layout.addWidget(self.checkbox_dont_show)

        # Buttons
        buttons = QHBoxLayout()

        btn_help = QPushButton("Help")
        btn_help.clicked.connect(self._on_help)
        buttons.addWidget(btn_help)

        buttons.addStretch()

        if self.settings.recent_files:
            btn_recent = QPushButton("Open Recent")
            btn_recent.clicked.connect(self._on_open_recent)
            buttons.addWidget(btn_recent)

        btn_open = QPushButton("Open Video")
        btn_open.setDefault(True)
        btn_open.clicked.connect(self._on_open_video)
        buttons.addWidget(btn_open)

        layout.addLayout(buttons)

    def _on_open_video(self) -> None:
        """Handle open video button."""
        self._save_preferences()
        self.done(self.OpenVideo)

    def _on_open_recent(self) -> None:
        """Handle open recent button."""
        if hasattr(self, 'recent_list') and self.recent_list.currentItem():
            self.selected_recent = self.recent_list.currentItem().data(Qt.UserRole)
            self._save_preferences()
            self.done(self.OpenRecent)

    def _on_recent_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle recent file double-click."""
        self.selected_recent = item.data(Qt.UserRole)
        self._save_preferences()
        self.done(self.OpenRecent)

    def _on_help(self) -> None:
        """Handle help button."""
        self._save_preferences()
        self.done(self.ShowHelp)

    def _save_preferences(self) -> None:
        """Save user preferences."""
        self.settings.show_startup_dialog = not self.checkbox_dont_show.isChecked()
        self.settings.save()
