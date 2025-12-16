"""Caption editor panel with word-level styling."""

from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QListWidget,
    QListWidgetItem, QComboBox, QLabel, QPushButton, QFrame,
    QMenu, QColorDialog, QInputDialog, QFontDialog, QSplitter,
    QToolButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QPoint
from PySide6.QtGui import (
    QTextCursor, QTextCharFormat, QColor, QFont,
    QAction, QSyntaxHighlighter, QTextDocument
)

from ..core.models import Project, Subtitle, Word, Style, StyleOverride
from ..core.settings import Settings


class WordHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for styled words."""

    def __init__(self, document: QTextDocument, words: List[Word] = None):
        super().__init__(document)
        self._words = words or []

    def set_words(self, words: List[Word]) -> None:
        """Set the words to highlight."""
        self._words = words
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        """Highlight words with style overrides."""
        if not self._words:
            return

        pos = 0
        for word in self._words:
            # Find word in text
            idx = text.find(word.text, pos)
            if idx >= 0:
                if word.has_override():
                    fmt = QTextCharFormat()
                    override = word.style_override

                    if override.color:
                        fmt.setForeground(QColor(override.color))
                    if override.bold:
                        fmt.setFontWeight(QFont.Bold)
                    if override.italic:
                        fmt.setFontItalic(True)
                    if override.underline:
                        fmt.setFontUnderline(True)
                    if override.background_color and override.background_opacity:
                        bg = QColor(override.background_color)
                        bg.setAlphaF(override.background_opacity)
                        fmt.setBackground(bg)

                    self.setFormat(idx, len(word.text), fmt)

                pos = idx + len(word.text)


class SubtitleListItem(QListWidgetItem):
    """List item representing a subtitle."""

    def __init__(self, subtitle: Subtitle):
        super().__init__()
        self.subtitle = subtitle
        self._update_display()

    def _update_display(self) -> None:
        """Update the display text."""
        start = self._format_time(self.subtitle.start_ms)
        end = self._format_time(self.subtitle.end_ms)
        text = self.subtitle.get_full_text()
        if len(text) > 50:
            text = text[:47] + "..."
        self.setText(f"[{start} - {end}] {text}")

    def _format_time(self, ms: int) -> str:
        """Format milliseconds as MM:SS.mmm."""
        s = ms // 1000
        m = s // 60
        ms_part = ms % 1000
        return f"{m:02d}:{s % 60:02d}.{ms_part // 10:02d}"


class CaptionPanel(QWidget):
    """Caption editor panel."""

    # Signals
    subtitle_changed = Signal(object)  # subtitle
    subtitles_changed = Signal(list)  # list of subtitles (for multi-selection changes)
    word_style_changed = Signal(int, int, dict)  # subtitle_id, word_index, style
    subtitles_selected = Signal(list)  # list of selected subtitles

    def __init__(self, parent=None):
        super().__init__(parent)

        self._project: Optional[Project] = None
        self._settings: Optional[Settings] = None
        self._current_subtitle: Optional[Subtitle] = None
        self._selected_subtitles: List[Subtitle] = []  # For multi-selection
        self._selected_word_index: Optional[int] = None
        self._highlighter: Optional[WordHighlighter] = None

        self._setup_ui()

    def set_settings(self, settings: Settings) -> None:
        """Set settings for loading presets."""
        self._settings = settings
        self._update_style_combo()

    def _setup_ui(self) -> None:
        """Setup the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Splitter for list and editor
        splitter = QSplitter(Qt.Vertical)

        # Subtitle list
        list_frame = QFrame()
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(0, 0, 0, 0)

        list_header = QHBoxLayout()
        list_header.addWidget(QLabel("Subtitles"))
        list_header.addStretch()

        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(24, 24)
        self.btn_add.setToolTip("Add subtitle")
        self.btn_add.clicked.connect(self._on_add_subtitle)
        list_header.addWidget(self.btn_add)

        self.btn_delete = QPushButton("-")
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.setToolTip("Delete subtitle")
        self.btn_delete.clicked.connect(self._on_delete_subtitle)
        list_header.addWidget(self.btn_delete)

        list_layout.addLayout(list_header)

        self.subtitle_list = QListWidget()
        self.subtitle_list.setSelectionMode(QListWidget.ExtendedSelection)  # Enable multi-selection
        self.subtitle_list.itemClicked.connect(self._on_subtitle_clicked)
        self.subtitle_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.subtitle_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.subtitle_list.customContextMenuRequested.connect(self._on_list_context_menu)
        list_layout.addWidget(self.subtitle_list)

        # Selection info label
        self.selection_label = QLabel("")
        self.selection_label.setStyleSheet("color: #888; font-size: 11px;")
        list_layout.addWidget(self.selection_label)

        splitter.addWidget(list_frame)

        # Editor area
        editor_frame = QFrame()
        editor_layout = QVBoxLayout(editor_frame)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        # Style toolbar
        style_toolbar = QHBoxLayout()

        style_toolbar.addWidget(QLabel("Style:"))

        self.style_combo = QComboBox()
        self.style_combo.setMinimumWidth(120)
        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        style_toolbar.addWidget(self.style_combo)

        self.btn_apply_style = QPushButton("Apply to Selected")
        self.btn_apply_style.setToolTip("Apply style to all selected subtitles")
        self.btn_apply_style.clicked.connect(self._on_apply_style_to_selected)
        self.btn_apply_style.setEnabled(False)
        style_toolbar.addWidget(self.btn_apply_style)

        style_toolbar.addStretch()

        # Word styling buttons
        self.btn_color = QToolButton()
        self.btn_color.setText("A")
        self.btn_color.setToolTip("Word Color (Ctrl+Shift+C)")
        self.btn_color.clicked.connect(self._on_set_word_color)
        style_toolbar.addWidget(self.btn_color)

        self.btn_bold = QToolButton()
        self.btn_bold.setText("B")
        self.btn_bold.setFont(QFont("", -1, QFont.Bold))
        self.btn_bold.setCheckable(True)
        self.btn_bold.setToolTip("Bold")
        self.btn_bold.clicked.connect(self._on_toggle_bold)
        style_toolbar.addWidget(self.btn_bold)

        self.btn_italic = QToolButton()
        self.btn_italic.setText("I")
        self.btn_italic.setFont(QFont("", -1, -1, True))
        self.btn_italic.setCheckable(True)
        self.btn_italic.setToolTip("Italic")
        self.btn_italic.clicked.connect(self._on_toggle_italic)
        style_toolbar.addWidget(self.btn_italic)

        self.btn_karaoke = QToolButton()
        self.btn_karaoke.setText("K")
        self.btn_karaoke.setToolTip("Karaoke Highlight")
        self.btn_karaoke.clicked.connect(self._on_set_karaoke)
        style_toolbar.addWidget(self.btn_karaoke)

        editor_layout.addLayout(style_toolbar)

        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Select a subtitle to edit...")
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self._on_editor_context_menu)
        self.text_edit.cursorPositionChanged.connect(self._on_cursor_changed)
        editor_layout.addWidget(self.text_edit)

        # Timing controls
        timing_layout = QHBoxLayout()

        timing_layout.addWidget(QLabel("Start:"))
        self.start_label = QLabel("00:00.00")
        self.start_label.setMinimumWidth(60)
        timing_layout.addWidget(self.start_label)

        timing_layout.addWidget(QLabel("End:"))
        self.end_label = QLabel("00:00.00")
        self.end_label.setMinimumWidth(60)
        timing_layout.addWidget(self.end_label)

        timing_layout.addWidget(QLabel("Duration:"))
        self.duration_label = QLabel("0.00s")
        self.duration_label.setMinimumWidth(50)
        timing_layout.addWidget(self.duration_label)

        timing_layout.addStretch()

        self.btn_split_words = QPushButton("Split to Words")
        self.btn_split_words.setToolTip("Split subtitle into word-by-word timing")
        self.btn_split_words.clicked.connect(self._on_split_words)
        timing_layout.addWidget(self.btn_split_words)

        editor_layout.addLayout(timing_layout)

        splitter.addWidget(editor_frame)

        # Set initial sizes
        splitter.setSizes([200, 300])

        layout.addWidget(splitter)

        # Setup highlighter
        self._highlighter = WordHighlighter(self.text_edit.document())

    def set_project(self, project: Project) -> None:
        """Set the project."""
        self._project = project
        self._update_subtitle_list()
        self._update_style_combo()

    def update_subtitles(self) -> None:
        """Update the subtitle list."""
        self._update_subtitle_list()

    def select_subtitle(self, subtitle: Subtitle) -> None:
        """Select a subtitle."""
        self._current_subtitle = subtitle
        self._update_editor()

        # Select in list
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            if isinstance(item, SubtitleListItem) and item.subtitle == subtitle:
                self.subtitle_list.setCurrentItem(item)
                break

    def split_subtitle(self) -> None:
        """Split current subtitle at cursor position."""
        if not self._current_subtitle:
            return

        cursor = self.text_edit.textCursor()
        pos = cursor.position()
        text = self._current_subtitle.text

        if 0 < pos < len(text):
            # Split text
            text1 = text[:pos].strip()
            text2 = text[pos:].strip()

            if text1 and text2:
                # Calculate split time
                ratio = pos / len(text)
                duration = self._current_subtitle.end_ms - self._current_subtitle.start_ms
                split_time = self._current_subtitle.start_ms + int(duration * ratio)

                # Modify current subtitle
                self._current_subtitle.text = text1
                self._current_subtitle.end_ms = split_time

                # Create new subtitle
                new_subtitle = Subtitle(
                    start_ms=split_time,
                    end_ms=self._current_subtitle.end_ms + int(duration * (1 - ratio)),
                    text=text2,
                    style_id=self._current_subtitle.style_id
                )

                if self._project:
                    self._project.add_subtitle(new_subtitle)

                self._update_subtitle_list()
                self.subtitle_changed.emit(self._current_subtitle)

    def merge_subtitles(self) -> None:
        """Merge selected subtitles."""
        selected = self.subtitle_list.selectedItems()
        if len(selected) < 2:
            return

        subtitles = [item.subtitle for item in selected if isinstance(item, SubtitleListItem)]
        subtitles.sort(key=lambda s: s.start_ms)

        # Merge into first
        first = subtitles[0]
        texts = [s.get_full_text() for s in subtitles]
        first.text = " ".join(texts)
        first.end_ms = subtitles[-1].end_ms
        first.words = []

        # Remove others
        if self._project:
            for sub in subtitles[1:]:
                self._project.remove_subtitle(sub.id)

        self._update_subtitle_list()
        self.select_subtitle(first)
        self.subtitle_changed.emit(first)

    def _update_subtitle_list(self) -> None:
        """Update the subtitle list widget."""
        self.subtitle_list.clear()

        if not self._project:
            return

        for subtitle in self._project.subtitles:
            item = SubtitleListItem(subtitle)
            self.subtitle_list.addItem(item)

    def _update_style_combo(self) -> None:
        """Update the style combo box with project styles and saved presets."""
        self.style_combo.clear()

        if not self._project:
            return

        # Add project styles
        for style in self._project.styles:
            self.style_combo.addItem(style.name, style.id)

        # Add separator and saved presets if settings available
        if self._settings:
            presets = self._settings.get_style_presets()
            if presets:
                self.style_combo.insertSeparator(self.style_combo.count())
                for preset in presets:
                    # Store preset data with special marker to distinguish from project styles
                    self.style_combo.addItem(f"[Preset] {preset.name}", f"preset:{preset.slot}")

    def _update_editor(self) -> None:
        """Update the editor with current subtitle."""
        if not self._current_subtitle:
            self.text_edit.clear()
            self.start_label.setText("00:00.00")
            self.end_label.setText("00:00.00")
            self.duration_label.setText("0.00s")
            return

        # Block signals while updating
        self.text_edit.blockSignals(True)
        self.text_edit.setText(self._current_subtitle.get_full_text())
        self.text_edit.blockSignals(False)

        # Update timing labels
        self.start_label.setText(self._format_time(self._current_subtitle.start_ms))
        self.end_label.setText(self._format_time(self._current_subtitle.end_ms))
        duration = self._current_subtitle.duration_ms() / 1000
        self.duration_label.setText(f"{duration:.2f}s")

        # Update style combo
        if self._current_subtitle.style_id:
            idx = self.style_combo.findData(self._current_subtitle.style_id)
            if idx >= 0:
                self.style_combo.setCurrentIndex(idx)

        # Update highlighter
        self._highlighter.set_words(self._current_subtitle.words)

    def _format_time(self, ms: int) -> str:
        """Format milliseconds as MM:SS.mm."""
        s = ms // 1000
        m = s // 60
        ms_part = ms % 1000
        return f"{m:02d}:{s % 60:02d}.{ms_part // 10:02d}"

    def _get_word_at_cursor(self) -> Optional[tuple]:
        """Get the word at the current cursor position."""
        if not self._current_subtitle or not self._current_subtitle.words:
            return None

        cursor = self.text_edit.textCursor()
        pos = cursor.position()

        # Find word containing this position
        current_pos = 0
        for i, word in enumerate(self._current_subtitle.words):
            word_start = current_pos
            word_end = current_pos + len(word.text)

            if word_start <= pos <= word_end:
                return (i, word)

            current_pos = word_end + 1  # +1 for space

        return None

    # Slots

    @Slot()
    def _on_selection_changed(self) -> None:
        """Handle selection change in subtitle list."""
        selected_items = self.subtitle_list.selectedItems()
        self._selected_subtitles = [
            item.subtitle for item in selected_items
            if isinstance(item, SubtitleListItem)
        ]

        # Update selection label
        count = len(self._selected_subtitles)
        if count == 0:
            self.selection_label.setText("")
        elif count == 1:
            self.selection_label.setText("1 subtitle selected")
        else:
            self.selection_label.setText(f"{count} subtitles selected (Ctrl+click to add)")

        # Enable/disable apply style button
        self.btn_apply_style.setEnabled(count > 1)

        # Emit signal for external listeners
        self.subtitles_selected.emit(self._selected_subtitles)

    @Slot(QListWidgetItem)
    def _on_subtitle_clicked(self, item: QListWidgetItem) -> None:
        """Handle subtitle list item click."""
        if isinstance(item, SubtitleListItem):
            self._current_subtitle = item.subtitle
            self._update_editor()

    @Slot()
    def _on_add_subtitle(self) -> None:
        """Add a new subtitle."""
        if not self._project:
            return

        # Create subtitle at end or after selected
        if self._current_subtitle:
            start = self._current_subtitle.end_ms + 100
        elif self._project.subtitles:
            start = self._project.subtitles[-1].end_ms + 100
        else:
            start = 0

        subtitle = Subtitle(
            start_ms=start,
            end_ms=start + 2000,
            text="New subtitle",
            style_id=self._project.default_style_id
        )
        self._project.add_subtitle(subtitle)
        self._update_subtitle_list()
        self.select_subtitle(subtitle)
        self.subtitle_changed.emit(subtitle)

    @Slot()
    def _on_delete_subtitle(self) -> None:
        """Delete the selected subtitle."""
        if not self._project or not self._current_subtitle:
            return

        self._project.remove_subtitle(self._current_subtitle.id)
        self._current_subtitle = None
        self._update_subtitle_list()
        self._update_editor()

    @Slot()
    def _on_text_changed(self) -> None:
        """Handle text edit change."""
        if not self._current_subtitle:
            return

        new_text = self.text_edit.toPlainText()
        if new_text != self._current_subtitle.text:
            self._current_subtitle.text = new_text
            self._current_subtitle.words = []  # Clear word-level data
            self.subtitle_changed.emit(self._current_subtitle)

            # Update list item
            for i in range(self.subtitle_list.count()):
                item = self.subtitle_list.item(i)
                if isinstance(item, SubtitleListItem) and item.subtitle == self._current_subtitle:
                    item._update_display()
                    break

    @Slot(int)
    def _on_style_changed(self, index: int) -> None:
        """Handle style combo change."""
        if not self._current_subtitle or index < 0:
            return

        style_data = self.style_combo.itemData(index)

        # Check if it's a preset selection
        if isinstance(style_data, str) and style_data.startswith("preset:"):
            slot = int(style_data.split(":")[1])
            if self._settings:
                preset = self._settings.get_style_preset(slot)
                if preset:
                    # Create new style from preset and add to project
                    from ..core.models import Alignment
                    new_id = max((s.id or 0 for s in self._project.styles), default=0) + 1
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
                    self._project.styles.append(new_style)
                    self._current_subtitle.style_id = new_style.id
                    self._update_style_combo()
                    # Select the newly added style
                    idx = self.style_combo.findData(new_style.id)
                    if idx >= 0:
                        self.style_combo.setCurrentIndex(idx)
        else:
            # Regular project style
            self._current_subtitle.style_id = style_data

        self.subtitle_changed.emit(self._current_subtitle)

    @Slot()
    def _on_apply_style_to_selected(self) -> None:
        """Apply selected style to all selected subtitles."""
        if not self._selected_subtitles:
            return

        style_id = self.style_combo.currentData()
        if style_id is None:
            return

        for subtitle in self._selected_subtitles:
            subtitle.style_id = style_id

        self.subtitles_changed.emit(self._selected_subtitles)

    def get_selected_subtitles(self) -> List[Subtitle]:
        """Get list of selected subtitles."""
        return self._selected_subtitles.copy()

    def select_subtitles(self, subtitles: List[Subtitle]) -> None:
        """Select multiple subtitles programmatically."""
        self.subtitle_list.clearSelection()
        subtitle_ids = {s.id for s in subtitles}

        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            if isinstance(item, SubtitleListItem) and item.subtitle.id in subtitle_ids:
                item.setSelected(True)

    @Slot()
    def _on_cursor_changed(self) -> None:
        """Handle cursor position change."""
        result = self._get_word_at_cursor()
        if result:
            self._selected_word_index, word = result
            # Update toolbar button states
            self.btn_bold.setChecked(word.style_override.bold or False)
            self.btn_italic.setChecked(word.style_override.italic or False)
        else:
            self._selected_word_index = None

    @Slot()
    def _on_split_words(self) -> None:
        """Split subtitle into words."""
        if not self._current_subtitle:
            return

        self._current_subtitle.split_into_words()
        self._highlighter.set_words(self._current_subtitle.words)
        self.subtitle_changed.emit(self._current_subtitle)

    @Slot()
    def _on_set_word_color(self) -> None:
        """Set color for selected word."""
        result = self._get_word_at_cursor()
        if not result:
            return

        idx, word = result
        color = QColorDialog.getColor(
            QColor(word.style_override.color or "#FFFFFF"),
            self,
            "Select Word Color"
        )

        if color.isValid():
            word.style_override.color = color.name()
            self._highlighter.rehighlight()
            self.word_style_changed.emit(
                self._current_subtitle.id, idx, word.style_override.to_dict()
            )

    @Slot()
    def _on_toggle_bold(self) -> None:
        """Toggle bold for selected word."""
        result = self._get_word_at_cursor()
        if not result:
            return

        idx, word = result
        word.style_override.bold = not (word.style_override.bold or False)
        self.btn_bold.setChecked(word.style_override.bold)
        self._highlighter.rehighlight()
        self.word_style_changed.emit(
            self._current_subtitle.id, idx, word.style_override.to_dict()
        )

    @Slot()
    def _on_toggle_italic(self) -> None:
        """Toggle italic for selected word."""
        result = self._get_word_at_cursor()
        if not result:
            return

        idx, word = result
        word.style_override.italic = not (word.style_override.italic or False)
        self.btn_italic.setChecked(word.style_override.italic)
        self._highlighter.rehighlight()
        self.word_style_changed.emit(
            self._current_subtitle.id, idx, word.style_override.to_dict()
        )

    @Slot()
    def _on_set_karaoke(self) -> None:
        """Set karaoke timing for selected word."""
        result = self._get_word_at_cursor()
        if not result:
            return

        idx, word = result
        duration, ok = QInputDialog.getInt(
            self, "Karaoke Duration",
            "Duration (centiseconds):",
            word.style_override.karaoke_duration or 30,
            1, 1000
        )

        if ok:
            word.style_override.karaoke_duration = duration
            self.word_style_changed.emit(
                self._current_subtitle.id, idx, word.style_override.to_dict()
            )

    @Slot(QPoint)
    def _on_list_context_menu(self, pos: QPoint) -> None:
        """Show context menu for subtitle list."""
        menu = QMenu(self)
        menu.addAction("Add Subtitle", self._on_add_subtitle)
        menu.addAction("Delete Subtitle", self._on_delete_subtitle)
        menu.addSeparator()
        menu.addAction("Merge Selected", self.merge_subtitles)
        menu.exec(self.subtitle_list.mapToGlobal(pos))

    @Slot(QPoint)
    def _on_editor_context_menu(self, pos: QPoint) -> None:
        """Show context menu for text editor."""
        menu = QMenu(self)

        # Word styling options
        result = self._get_word_at_cursor()
        if result:
            idx, word = result
            menu.addAction(f"Style: '{word.text}'")
            menu.addSeparator()
            menu.addAction("Set Color...", self._on_set_word_color)
            menu.addAction("Set Font...", self._on_set_word_font)
            menu.addAction("Set Rotation...", self._on_set_word_rotation)
            menu.addAction("Add Box/Outline...", self._on_set_word_box)
            menu.addSeparator()
            menu.addAction("Apply Karaoke Highlight...", self._on_set_karaoke)
            menu.addSeparator()
            menu.addAction("Reset Style", lambda: self._reset_word_style(idx, word))

        menu.addSeparator()
        menu.addAction("Split to Words", self._on_split_words)

        menu.exec(self.text_edit.mapToGlobal(pos))

    def _on_set_word_font(self) -> None:
        """Set font for selected word."""
        result = self._get_word_at_cursor()
        if not result:
            return

        idx, word = result
        ok, font = QFontDialog.getFont(self)
        if ok:
            word.style_override.font_family = font.family()
            word.style_override.font_size = font.pointSize()
            self._highlighter.rehighlight()
            self.word_style_changed.emit(
                self._current_subtitle.id, idx, word.style_override.to_dict()
            )

    def _on_set_word_rotation(self) -> None:
        """Set rotation for selected word."""
        result = self._get_word_at_cursor()
        if not result:
            return

        idx, word = result
        angle, ok = QInputDialog.getDouble(
            self, "Word Rotation",
            "Rotation angle (degrees):",
            word.style_override.rotation or 0,
            -360, 360, 1
        )

        if ok:
            word.style_override.rotation = angle
            self.word_style_changed.emit(
                self._current_subtitle.id, idx, word.style_override.to_dict()
            )

    def _on_set_word_box(self) -> None:
        """Set box/outline for selected word."""
        result = self._get_word_at_cursor()
        if not result:
            return

        idx, word = result

        # Get outline color
        color = QColorDialog.getColor(
            QColor(word.style_override.outline_color or "#000000"),
            self,
            "Select Outline Color"
        )

        if color.isValid():
            word.style_override.outline_color = color.name()
            word.style_override.outline_width = 2

            # Get background
            bg_color = QColorDialog.getColor(
                QColor(word.style_override.background_color or "#000000"),
                self,
                "Select Background Color (Cancel for none)"
            )

            if bg_color.isValid():
                word.style_override.background_color = bg_color.name()
                word.style_override.background_opacity = 0.5

            self._highlighter.rehighlight()
            self.word_style_changed.emit(
                self._current_subtitle.id, idx, word.style_override.to_dict()
            )

    def _reset_word_style(self, idx: int, word: Word) -> None:
        """Reset word style to default."""
        word.style_override = StyleOverride()
        self._highlighter.rehighlight()
        self.word_style_changed.emit(
            self._current_subtitle.id, idx, word.style_override.to_dict()
        )
