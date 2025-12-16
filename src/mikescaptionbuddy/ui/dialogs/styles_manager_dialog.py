"""Styles manager dialog."""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QGroupBox, QFormLayout, QLineEdit, QSpinBox,
    QCheckBox, QComboBox, QLabel, QColorDialog, QFontComboBox,
    QFrame, QSplitter, QMessageBox, QInputDialog, QTabWidget
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont

from ...core.models import Project, Style, Alignment
from ...core.settings import Settings, StylePreset


class StylePreviewWidget(QFrame):
    """Widget showing a preview of the style."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.style: Optional[Style] = None
        self.setMinimumSize(200, 60)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

    def set_style(self, style: Style) -> None:
        """Set the style to preview."""
        self.style = style
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the preview."""
        from PySide6.QtGui import QPainter, QPen, QBrush

        super().paintEvent(event)

        if not self.style:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(40, 40, 45))

        # Setup font
        font = QFont(self.style.font_family, self.style.font_size // 2)
        font.setBold(self.style.bold)
        font.setItalic(self.style.italic)
        font.setUnderline(self.style.underline)
        painter.setFont(font)

        text = "Sample Caption"
        rect = self.rect().adjusted(10, 10, -10, -10)

        # Draw background box if enabled
        if self.style.background_opacity > 0:
            bg_color = QColor(self.style.background_color)
            bg_color.setAlphaF(self.style.background_opacity)
            text_rect = painter.boundingRect(rect, Qt.AlignCenter, text)
            text_rect.adjust(-4, -2, 4, 2)
            painter.fillRect(text_rect, bg_color)

        # Draw shadow
        if self.style.shadow_offset_x or self.style.shadow_offset_y:
            painter.setPen(QColor(self.style.shadow_color))
            shadow_rect = rect.translated(
                self.style.shadow_offset_x // 2,
                self.style.shadow_offset_y // 2
            )
            painter.drawText(shadow_rect, Qt.AlignCenter, text)

        # Draw outline
        if self.style.outline_width > 0:
            pen = QPen(QColor(self.style.outline_color))
            pen.setWidth(self.style.outline_width)
            painter.setPen(pen)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx or dy:
                        painter.drawText(rect.translated(dx, dy), Qt.AlignCenter, text)

        # Draw main text
        painter.setPen(QColor(self.style.primary_color))
        painter.drawText(rect, Qt.AlignCenter, text)


class StylesManagerDialog(QDialog):
    """Dialog for managing caption styles."""

    def __init__(self, project: Project, settings: Settings = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.settings = settings or Settings.load()
        self.current_style: Optional[Style] = None
        self._updating = False

        self._setup_ui()
        self._load_styles()
        self._load_presets()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("Style Presets Manager")
        self.setMinimumSize(700, 550)

        layout = QHBoxLayout(self)

        # Left side - tabs for Project Styles and Saved Presets
        left_widget = QVBoxLayout()

        self.tabs = QTabWidget()

        # Tab 1: Project Styles
        project_tab = QFrame()
        project_layout = QVBoxLayout(project_tab)

        project_layout.addWidget(QLabel("Project Styles:"))

        self.style_list = QListWidget()
        self.style_list.itemClicked.connect(self._on_style_selected)
        project_layout.addWidget(self.style_list)

        # List buttons
        list_buttons = QHBoxLayout()

        btn_add = QPushButton("+")
        btn_add.setFixedWidth(30)
        btn_add.setToolTip("Add new style")
        btn_add.clicked.connect(self._on_add_style)
        list_buttons.addWidget(btn_add)

        btn_delete = QPushButton("-")
        btn_delete.setFixedWidth(30)
        btn_delete.setToolTip("Delete selected style")
        btn_delete.clicked.connect(self._on_delete_style)
        list_buttons.addWidget(btn_delete)

        btn_duplicate = QPushButton("Dup")
        btn_duplicate.setToolTip("Duplicate selected style")
        btn_duplicate.clicked.connect(self._on_duplicate_style)
        list_buttons.addWidget(btn_duplicate)

        list_buttons.addStretch()
        project_layout.addLayout(list_buttons)

        # Save to preset button
        btn_save_preset = QPushButton("Save to Preset...")
        btn_save_preset.setToolTip("Save current style as a global preset")
        btn_save_preset.clicked.connect(self._on_save_to_preset)
        project_layout.addWidget(btn_save_preset)

        self.tabs.addTab(project_tab, "Project Styles")

        # Tab 2: Saved Presets
        presets_tab = QFrame()
        presets_layout = QVBoxLayout(presets_tab)

        presets_layout.addWidget(QLabel("Saved Presets (10 slots):"))

        self.preset_list = QListWidget()
        self.preset_list.itemClicked.connect(self._on_preset_selected)
        presets_layout.addWidget(self.preset_list)

        # Preset buttons
        preset_buttons = QHBoxLayout()

        btn_load_preset = QPushButton("Load to Project")
        btn_load_preset.setToolTip("Add selected preset to project styles")
        btn_load_preset.clicked.connect(self._on_load_preset)
        preset_buttons.addWidget(btn_load_preset)

        btn_delete_preset = QPushButton("Delete")
        btn_delete_preset.setToolTip("Delete selected preset")
        btn_delete_preset.clicked.connect(self._on_delete_preset)
        preset_buttons.addWidget(btn_delete_preset)

        preset_buttons.addStretch()
        presets_layout.addLayout(preset_buttons)

        self.tabs.addTab(presets_tab, "Saved Presets")

        left_widget.addWidget(self.tabs)

        left_frame = QFrame()
        left_frame.setLayout(left_widget)
        left_frame.setMaximumWidth(220)
        layout.addWidget(left_frame)

        # Right side - style editor
        right_widget = QVBoxLayout()

        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview = StylePreviewWidget()
        preview_layout.addWidget(self.preview)
        right_widget.addWidget(preview_group)

        # Properties
        props_group = QGroupBox("Properties")
        props_form = QFormLayout(props_group)

        self.edit_name = QLineEdit()
        self.edit_name.textChanged.connect(self._on_property_changed)
        props_form.addRow("Name:", self.edit_name)

        self.combo_font = QFontComboBox()
        self.combo_font.currentFontChanged.connect(self._on_property_changed)
        props_form.addRow("Font:", self.combo_font)

        self.spin_size = QSpinBox()
        self.spin_size.setRange(8, 200)
        self.spin_size.valueChanged.connect(self._on_property_changed)
        props_form.addRow("Size:", self.spin_size)

        # Font style
        font_style = QHBoxLayout()
        self.check_bold = QCheckBox("Bold")
        self.check_bold.stateChanged.connect(self._on_property_changed)
        font_style.addWidget(self.check_bold)

        self.check_italic = QCheckBox("Italic")
        self.check_italic.stateChanged.connect(self._on_property_changed)
        font_style.addWidget(self.check_italic)

        self.check_underline = QCheckBox("Underline")
        self.check_underline.stateChanged.connect(self._on_property_changed)
        font_style.addWidget(self.check_underline)

        font_style.addStretch()
        props_form.addRow("Style:", font_style)

        # Colors
        color_layout = QHBoxLayout()

        self.btn_primary = QPushButton("Primary")
        self.btn_primary.clicked.connect(lambda: self._pick_color('primary'))
        color_layout.addWidget(self.btn_primary)

        self.btn_secondary = QPushButton("Secondary")
        self.btn_secondary.clicked.connect(lambda: self._pick_color('secondary'))
        color_layout.addWidget(self.btn_secondary)

        props_form.addRow("Colors:", color_layout)

        # Outline
        outline_layout = QHBoxLayout()

        self.btn_outline = QPushButton("Outline")
        self.btn_outline.clicked.connect(lambda: self._pick_color('outline'))
        outline_layout.addWidget(self.btn_outline)

        self.spin_outline = QSpinBox()
        self.spin_outline.setRange(0, 10)
        self.spin_outline.valueChanged.connect(self._on_property_changed)
        outline_layout.addWidget(self.spin_outline)
        outline_layout.addWidget(QLabel("px"))

        outline_layout.addStretch()
        props_form.addRow("Outline:", outline_layout)

        # Shadow
        shadow_layout = QHBoxLayout()

        self.btn_shadow = QPushButton("Shadow")
        self.btn_shadow.clicked.connect(lambda: self._pick_color('shadow'))
        shadow_layout.addWidget(self.btn_shadow)

        self.spin_shadow_x = QSpinBox()
        self.spin_shadow_x.setRange(0, 20)
        self.spin_shadow_x.valueChanged.connect(self._on_property_changed)
        shadow_layout.addWidget(self.spin_shadow_x)

        self.spin_shadow_y = QSpinBox()
        self.spin_shadow_y.setRange(0, 20)
        self.spin_shadow_y.valueChanged.connect(self._on_property_changed)
        shadow_layout.addWidget(self.spin_shadow_y)

        shadow_layout.addStretch()
        props_form.addRow("Shadow:", shadow_layout)

        # Background
        bg_layout = QHBoxLayout()

        self.btn_bg = QPushButton("Background")
        self.btn_bg.clicked.connect(lambda: self._pick_color('background'))
        bg_layout.addWidget(self.btn_bg)

        self.spin_bg_opacity = QSpinBox()
        self.spin_bg_opacity.setRange(0, 100)
        self.spin_bg_opacity.setSuffix("%")
        self.spin_bg_opacity.valueChanged.connect(self._on_property_changed)
        bg_layout.addWidget(self.spin_bg_opacity)

        bg_layout.addStretch()
        props_form.addRow("Background:", bg_layout)

        # Alignment
        self.combo_align = QComboBox()
        self.combo_align.addItem("Bottom Left", Alignment.BOTTOM_LEFT.value)
        self.combo_align.addItem("Bottom Center", Alignment.BOTTOM_CENTER.value)
        self.combo_align.addItem("Bottom Right", Alignment.BOTTOM_RIGHT.value)
        self.combo_align.addItem("Middle Left", Alignment.MIDDLE_LEFT.value)
        self.combo_align.addItem("Middle Center", Alignment.MIDDLE_CENTER.value)
        self.combo_align.addItem("Middle Right", Alignment.MIDDLE_RIGHT.value)
        self.combo_align.addItem("Top Left", Alignment.TOP_LEFT.value)
        self.combo_align.addItem("Top Center", Alignment.TOP_CENTER.value)
        self.combo_align.addItem("Top Right", Alignment.TOP_RIGHT.value)
        self.combo_align.currentIndexChanged.connect(self._on_property_changed)
        props_form.addRow("Alignment:", self.combo_align)

        right_widget.addWidget(props_group)

        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        buttons.addWidget(btn_close)

        right_widget.addLayout(buttons)

        right_frame = QFrame()
        right_frame.setLayout(right_widget)
        layout.addWidget(right_frame, 1)

        # Initially disable editor
        self._set_editor_enabled(False)

    def _load_styles(self) -> None:
        """Load styles into the list."""
        self.style_list.clear()

        for style in self.project.styles:
            item = QListWidgetItem(style.name)
            item.setData(Qt.UserRole, style)
            self.style_list.addItem(item)

        if self.style_list.count() > 0:
            self.style_list.setCurrentRow(0)
            self._on_style_selected(self.style_list.item(0))

    def _set_editor_enabled(self, enabled: bool) -> None:
        """Enable or disable the style editor."""
        self.edit_name.setEnabled(enabled)
        self.combo_font.setEnabled(enabled)
        self.spin_size.setEnabled(enabled)
        self.check_bold.setEnabled(enabled)
        self.check_italic.setEnabled(enabled)
        self.check_underline.setEnabled(enabled)
        self.btn_primary.setEnabled(enabled)
        self.btn_secondary.setEnabled(enabled)
        self.btn_outline.setEnabled(enabled)
        self.spin_outline.setEnabled(enabled)
        self.btn_shadow.setEnabled(enabled)
        self.spin_shadow_x.setEnabled(enabled)
        self.spin_shadow_y.setEnabled(enabled)
        self.btn_bg.setEnabled(enabled)
        self.spin_bg_opacity.setEnabled(enabled)
        self.combo_align.setEnabled(enabled)

    def _update_editor(self) -> None:
        """Update editor with current style."""
        if not self.current_style:
            return

        self._updating = True

        self.edit_name.setText(self.current_style.name)
        self.combo_font.setCurrentFont(QFont(self.current_style.font_family))
        self.spin_size.setValue(self.current_style.font_size)
        self.check_bold.setChecked(self.current_style.bold)
        self.check_italic.setChecked(self.current_style.italic)
        self.check_underline.setChecked(self.current_style.underline)

        self.spin_outline.setValue(self.current_style.outline_width)
        self.spin_shadow_x.setValue(self.current_style.shadow_offset_x)
        self.spin_shadow_y.setValue(self.current_style.shadow_offset_y)
        self.spin_bg_opacity.setValue(int(self.current_style.background_opacity * 100))

        # Set alignment combo
        for i in range(self.combo_align.count()):
            if self.combo_align.itemData(i) == self.current_style.alignment.value:
                self.combo_align.setCurrentIndex(i)
                break

        # Update color buttons
        self._update_color_button(self.btn_primary, self.current_style.primary_color)
        self._update_color_button(self.btn_secondary, self.current_style.secondary_color)
        self._update_color_button(self.btn_outline, self.current_style.outline_color)
        self._update_color_button(self.btn_shadow, self.current_style.shadow_color)
        self._update_color_button(self.btn_bg, self.current_style.background_color)

        self.preview.set_style(self.current_style)

        self._updating = False

    def _update_color_button(self, button: QPushButton, color: str) -> None:
        """Update a color button's appearance."""
        qcolor = QColor(color)
        button.setStyleSheet(
            f"background-color: {color}; "
            f"color: {'white' if qcolor.lightness() < 128 else 'black'};"
        )

    def _pick_color(self, color_type: str) -> None:
        """Open color picker for a color property."""
        if not self.current_style:
            return

        current = getattr(self.current_style, f"{color_type}_color")
        color = QColorDialog.getColor(QColor(current), self, f"Select {color_type.title()} Color")

        if color.isValid():
            setattr(self.current_style, f"{color_type}_color", color.name())
            self._update_editor()

    @Slot(QListWidgetItem)
    def _on_style_selected(self, item: QListWidgetItem) -> None:
        """Handle style selection."""
        self.current_style = item.data(Qt.UserRole)
        self._set_editor_enabled(True)
        self._update_editor()

    @Slot()
    def _on_property_changed(self) -> None:
        """Handle property change in editor."""
        if self._updating or not self.current_style:
            return

        self.current_style.name = self.edit_name.text()
        self.current_style.font_family = self.combo_font.currentFont().family()
        self.current_style.font_size = self.spin_size.value()
        self.current_style.bold = self.check_bold.isChecked()
        self.current_style.italic = self.check_italic.isChecked()
        self.current_style.underline = self.check_underline.isChecked()
        self.current_style.outline_width = self.spin_outline.value()
        self.current_style.shadow_offset_x = self.spin_shadow_x.value()
        self.current_style.shadow_offset_y = self.spin_shadow_y.value()
        self.current_style.background_opacity = self.spin_bg_opacity.value() / 100.0
        self.current_style.alignment = Alignment(self.combo_align.currentData())

        # Update list item text
        current_item = self.style_list.currentItem()
        if current_item:
            current_item.setText(self.current_style.name)

        self.preview.set_style(self.current_style)

    @Slot()
    def _on_add_style(self) -> None:
        """Add a new style."""
        new_id = max((s.id or 0 for s in self.project.styles), default=0) + 1
        style = Style(id=new_id, name=f"Style {new_id}")
        self.project.styles.append(style)

        item = QListWidgetItem(style.name)
        item.setData(Qt.UserRole, style)
        self.style_list.addItem(item)
        self.style_list.setCurrentItem(item)
        self._on_style_selected(item)

    @Slot()
    def _on_delete_style(self) -> None:
        """Delete the selected style."""
        current_item = self.style_list.currentItem()
        if not current_item:
            return

        style = current_item.data(Qt.UserRole)

        # Don't delete the last style
        if len(self.project.styles) <= 1:
            return

        # Remove from project
        self.project.styles.remove(style)

        # Remove from list
        row = self.style_list.row(current_item)
        self.style_list.takeItem(row)

        if self.style_list.count() > 0:
            self.style_list.setCurrentRow(min(row, self.style_list.count() - 1))

    @Slot()
    def _on_duplicate_style(self) -> None:
        """Duplicate the selected style."""
        if not self.current_style:
            return

        new_id = max((s.id or 0 for s in self.project.styles), default=0) + 1
        new_style = Style(
            id=new_id,
            name=f"{self.current_style.name} Copy",
            font_family=self.current_style.font_family,
            font_size=self.current_style.font_size,
            bold=self.current_style.bold,
            italic=self.current_style.italic,
            underline=self.current_style.underline,
            primary_color=self.current_style.primary_color,
            secondary_color=self.current_style.secondary_color,
            outline_color=self.current_style.outline_color,
            outline_width=self.current_style.outline_width,
            shadow_color=self.current_style.shadow_color,
            shadow_offset_x=self.current_style.shadow_offset_x,
            shadow_offset_y=self.current_style.shadow_offset_y,
            background_color=self.current_style.background_color,
            background_opacity=self.current_style.background_opacity,
            alignment=self.current_style.alignment
        )

        self.project.styles.append(new_style)

        item = QListWidgetItem(new_style.name)
        item.setData(Qt.UserRole, new_style)
        self.style_list.addItem(item)
        self.style_list.setCurrentItem(item)
        self._on_style_selected(item)

    # Preset management methods

    def _load_presets(self) -> None:
        """Load saved presets into the list."""
        self.preset_list.clear()

        presets = self.settings.get_style_presets()
        for preset in presets:
            item = QListWidgetItem(f"[{preset.slot}] {preset.name}")
            item.setData(Qt.UserRole, preset)
            self.preset_list.addItem(item)

        if not presets:
            empty_item = QListWidgetItem("(No saved presets)")
            empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsSelectable)
            self.preset_list.addItem(empty_item)

    @Slot()
    def _on_save_to_preset(self) -> None:
        """Save current style as a preset."""
        if not self.current_style:
            QMessageBox.warning(self, "No Style Selected",
                              "Please select a style to save as preset.")
            return

        # Get next available slot
        next_slot = self.settings.get_next_available_preset_slot()

        if next_slot == 0:
            # All slots used, ask which to overwrite
            presets = self.settings.get_style_presets()
            slot_names = [f"Slot {p.slot}: {p.name}" for p in presets]
            slot_choice, ok = QInputDialog.getItem(
                self, "All Slots Full",
                "All 10 preset slots are used. Select one to overwrite:",
                slot_names, 0, False
            )
            if not ok:
                return
            # Extract slot number from choice
            next_slot = int(slot_choice.split(":")[0].replace("Slot ", ""))
        else:
            # Ask for slot number
            slot, ok = QInputDialog.getInt(
                self, "Select Preset Slot",
                f"Save to slot (1-10).\nNext available: {next_slot}",
                next_slot, 1, 10
            )
            if not ok:
                return
            next_slot = slot

            # Check if slot is already used
            existing = self.settings.get_style_preset(next_slot)
            if existing:
                reply = QMessageBox.question(
                    self, "Overwrite Preset?",
                    f"Slot {next_slot} already contains '{existing.name}'.\n"
                    "Do you want to overwrite it?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

        # Create preset from current style
        preset = StylePreset(
            slot=next_slot,
            name=self.current_style.name,
            font_family=self.current_style.font_family,
            font_size=self.current_style.font_size,
            bold=self.current_style.bold,
            italic=self.current_style.italic,
            underline=self.current_style.underline,
            primary_color=self.current_style.primary_color,
            secondary_color=self.current_style.secondary_color,
            outline_color=self.current_style.outline_color,
            outline_width=self.current_style.outline_width,
            shadow_color=self.current_style.shadow_color,
            shadow_offset_x=self.current_style.shadow_offset_x,
            shadow_offset_y=self.current_style.shadow_offset_y,
            background_color=self.current_style.background_color,
            background_opacity=self.current_style.background_opacity,
            alignment=self.current_style.alignment.value
        )

        self.settings.save_style_preset(preset)
        self._load_presets()

        QMessageBox.information(
            self, "Preset Saved",
            f"Style '{preset.name}' saved to slot {preset.slot}."
        )

    @Slot(QListWidgetItem)
    def _on_preset_selected(self, item: QListWidgetItem) -> None:
        """Handle preset selection - show preview."""
        preset = item.data(Qt.UserRole)
        if not preset:
            return

        # Create a temporary style for preview
        temp_style = Style(
            name=preset.name,
            font_family=preset.font_family,
            font_size=preset.font_size,
            bold=preset.bold,
            italic=preset.italic,
            underline=preset.underline,
            primary_color=preset.primary_color,
            secondary_color=preset.secondary_color,
            outline_color=preset.outline_color,
            outline_width=preset.outline_width,
            shadow_color=preset.shadow_color,
            shadow_offset_x=preset.shadow_offset_x,
            shadow_offset_y=preset.shadow_offset_y,
            background_color=preset.background_color,
            background_opacity=preset.background_opacity,
            alignment=Alignment(preset.alignment)
        )
        self.preview.set_style(temp_style)

    @Slot()
    def _on_load_preset(self) -> None:
        """Load selected preset into project styles."""
        current_item = self.preset_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Preset Selected",
                              "Please select a preset to load.")
            return

        preset = current_item.data(Qt.UserRole)
        if not preset:
            return

        # Create new style from preset
        new_id = max((s.id or 0 for s in self.project.styles), default=0) + 1
        new_style = Style(
            id=new_id,
            name=preset.name,
            font_family=preset.font_family,
            font_size=preset.font_size,
            bold=preset.bold,
            italic=preset.italic,
            underline=preset.underline,
            primary_color=preset.primary_color,
            secondary_color=preset.secondary_color,
            outline_color=preset.outline_color,
            outline_width=preset.outline_width,
            shadow_color=preset.shadow_color,
            shadow_offset_x=preset.shadow_offset_x,
            shadow_offset_y=preset.shadow_offset_y,
            background_color=preset.background_color,
            background_opacity=preset.background_opacity,
            alignment=Alignment(preset.alignment)
        )

        self.project.styles.append(new_style)
        self._load_styles()

        # Switch to project styles tab and select the new style
        self.tabs.setCurrentIndex(0)
        for i in range(self.style_list.count()):
            item = self.style_list.item(i)
            if item.data(Qt.UserRole) == new_style:
                self.style_list.setCurrentItem(item)
                self._on_style_selected(item)
                break

        QMessageBox.information(
            self, "Preset Loaded",
            f"Preset '{preset.name}' added to project styles."
        )

    @Slot()
    def _on_delete_preset(self) -> None:
        """Delete selected preset."""
        current_item = self.preset_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Preset Selected",
                              "Please select a preset to delete.")
            return

        preset = current_item.data(Qt.UserRole)
        if not preset:
            return

        reply = QMessageBox.question(
            self, "Delete Preset?",
            f"Are you sure you want to delete preset '{preset.name}' "
            f"from slot {preset.slot}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.settings.delete_style_preset(preset.slot)
            self._load_presets()
