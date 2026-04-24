"""Settings dialog for application preferences."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFormLayout, QSpinBox, QComboBox, QCheckBox, QLineEdit,
    QPushButton, QFileDialog, QLabel, QGroupBox
)
from PySide6.QtCore import Qt

from ...core.settings import Settings


class SettingsDialog(QDialog):
    """Settings dialog with tabbed interface."""

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(450, 400)

        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()

        # General tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        general_group = QGroupBox("General")
        general_form = QFormLayout(general_group)

        self.spin_auto_save = QSpinBox()
        self.spin_auto_save.setRange(30, 600)
        self.spin_auto_save.setSuffix(" seconds")
        general_form.addRow("Auto-save interval:", self.spin_auto_save)

        self.check_startup = QCheckBox()
        general_form.addRow("Show startup dialog:", self.check_startup)

        self.spin_recent = QSpinBox()
        self.spin_recent.setRange(5, 20)
        general_form.addRow("Recent files limit:", self.spin_recent)

        general_layout.addWidget(general_group)
        general_layout.addStretch()

        tabs.addTab(general_tab, "General")

        # Transcription tab
        transcription_tab = QWidget()
        transcription_layout = QVBoxLayout(transcription_tab)

        transcription_group = QGroupBox("Whisper Settings")
        transcription_form = QFormLayout(transcription_group)

        self.combo_model = QComboBox()
        self.combo_model.addItems(["small", "medium", "large"])
        transcription_form.addRow("Default model:", self.combo_model)

        self.combo_engine = QComboBox()
        self.combo_engine.addItem("Standard (CPU / NVIDIA CUDA)", "openai-whisper")
        self.combo_engine.addItem("OpenVINO (Intel CPU / Iris GPU)", "openvino")
        transcription_form.addRow("Inference Engine:", self.combo_engine)

        self.combo_language = QComboBox()
        self.combo_language.addItem("English", "en")
        self.combo_language.addItem("Auto-detect", "auto")
        transcription_form.addRow("Language:", self.combo_language)

        transcription_layout.addWidget(transcription_group)
        transcription_layout.addStretch()

        tabs.addTab(transcription_tab, "Transcription")

        # Export tab
        export_tab = QWidget()
        export_layout = QVBoxLayout(export_tab)

        export_group = QGroupBox("Export Settings")
        export_form = QFormLayout(export_group)

        dir_layout = QHBoxLayout()
        self.edit_export_dir = QLineEdit()
        self.edit_export_dir.setPlaceholderText("Default: Videos folder")
        dir_layout.addWidget(self.edit_export_dir)
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_export_dir)
        dir_layout.addWidget(btn_browse)
        export_form.addRow("Export directory:", dir_layout)

        self.combo_resolution = QComboBox()
        self.combo_resolution.addItems(["720p", "1080p"])
        export_form.addRow("Default resolution:", self.combo_resolution)

        self.combo_codec = QComboBox()
        self.combo_codec.addItem("H.264", "h264")
        export_form.addRow("Video codec:", self.combo_codec)

        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["fast", "balanced", "quality"])
        export_form.addRow("Quality preset:", self.combo_quality)

        export_layout.addWidget(export_group)
        export_layout.addStretch()

        tabs.addTab(export_tab, "Export")

        # Appearance tab
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)

        appearance_group = QGroupBox("Appearance")
        appearance_form = QFormLayout(appearance_group)

        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["system", "light", "dark"])
        appearance_form.addRow("Theme:", self.combo_theme)

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 24)
        appearance_form.addRow("Editor font size:", self.spin_font_size)

        appearance_layout.addWidget(appearance_group)
        appearance_layout.addStretch()

        tabs.addTab(appearance_tab, "Appearance")

        layout.addWidget(tabs)

        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)

        btn_save = QPushButton("Save")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)
        buttons.addWidget(btn_save)

        layout.addLayout(buttons)

    def _load_settings(self) -> None:
        """Load current settings into controls."""
        self.spin_auto_save.setValue(self.settings.auto_save_interval_seconds)
        self.check_startup.setChecked(self.settings.show_startup_dialog)
        self.spin_recent.setValue(self.settings.recent_files_limit)

        idx = self.combo_model.findText(self.settings.default_whisper_model)
        if idx >= 0:
            self.combo_model.setCurrentIndex(idx)

        idx = self.combo_engine.findData(self.settings.whisper_engine)
        if idx >= 0:
            self.combo_engine.setCurrentIndex(idx)

        self.edit_export_dir.setText(self.settings.default_export_directory)

        idx = self.combo_resolution.findText(self.settings.default_video_resolution)
        if idx >= 0:
            self.combo_resolution.setCurrentIndex(idx)

        idx = self.combo_quality.findText(self.settings.default_quality_preset)
        if idx >= 0:
            self.combo_quality.setCurrentIndex(idx)

        idx = self.combo_theme.findText(self.settings.theme)
        if idx >= 0:
            self.combo_theme.setCurrentIndex(idx)

        self.spin_font_size.setValue(self.settings.editor_font_size)

    def _browse_export_dir(self) -> None:
        """Browse for export directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Export Directory",
            self.settings.get_export_directory()
        )
        if path:
            self.edit_export_dir.setText(path)

    def _on_save(self) -> None:
        """Save settings and close."""
        self.settings.auto_save_interval_seconds = self.spin_auto_save.value()
        self.settings.show_startup_dialog = self.check_startup.isChecked()
        self.settings.recent_files_limit = self.spin_recent.value()
        self.settings.default_whisper_model = self.combo_model.currentText()
        self.settings.whisper_engine = self.combo_engine.currentData()
        self.settings.default_export_directory = self.edit_export_dir.text()
        self.settings.default_video_resolution = self.combo_resolution.currentText()
        self.settings.default_quality_preset = self.combo_quality.currentText()
        self.settings.theme = self.combo_theme.currentText()
        self.settings.editor_font_size = self.spin_font_size.value()

        self.settings.save()
        self.accept()
