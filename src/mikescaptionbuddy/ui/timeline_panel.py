"""Timeline panel with waveform and subtitle blocks."""

import os
from typing import Optional, List, Set
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QSlider, QLabel, QPushButton, QSizePolicy, QScrollBar
)
from PySide6.QtCore import Qt, Signal, Slot, QRectF, QPointF, QTimer
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath,
    QMouseEvent, QWheelEvent, QFont
)

from ..core.models import Project, Subtitle


class WaveformWidget(QWidget):
    """Widget displaying audio waveform and subtitle blocks."""

    # Signals
    position_changed = Signal(int)  # clicked position in ms
    subtitle_selected = Signal(object)  # selected subtitle (for single selection)
    subtitles_selected = Signal(list)  # selected subtitles (for multi-selection)
    subtitle_moved = Signal(object, int, int, int, int)  # subtitle, old_start, old_end, new_start, new_end
    zoom_changed = Signal(float)  # new zoom level

    def __init__(self, parent=None):
        super().__init__(parent)

        self._waveform_data: Optional[np.ndarray] = None
        self._duration_ms = 0
        self._position_ms = 0
        self._zoom_level = 0.1  # pixels per millisecond
        self._scroll_offset = 0
        self._project: Optional[Project] = None
        self._selected_subtitles: Set[int] = set()  # Set of subtitle IDs
        self._last_selected_index: int = -1  # For shift+click range selection
        self._dragging = False
        self._drag_edge: Optional[str] = None  # 'left', 'right', or 'move'
        self._drag_start_x = 0
        self._drag_start_pos = 0
        self._drag_original_start = 0  # Original start_ms before drag
        self._drag_original_end = 0  # Original end_ms before drag
        self._drag_subtitle: Optional[Subtitle] = None
        self._show_waveform = True

        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # Colors
        self._bg_color = QColor(40, 40, 45)
        self._waveform_color = QColor(80, 160, 80)
        self._playhead_color = QColor(255, 80, 80)
        self._subtitle_color = QColor(70, 130, 180, 180)
        self._subtitle_selected_color = QColor(100, 180, 220, 200)
        self._text_color = QColor(255, 255, 255)
        self._grid_color = QColor(60, 60, 65)

    def set_waveform(self, waveform_data: np.ndarray, duration_ms: int) -> None:
        """Set the waveform data to display."""
        self._waveform_data = waveform_data
        self._duration_ms = duration_ms
        self._fit_to_view()
        self.update()

    def set_duration(self, duration_ms: int) -> None:
        """Set the duration without waveform data."""
        self._duration_ms = duration_ms
        self._fit_to_view()
        self.update()

    def set_position(self, position_ms: int) -> None:
        """Set the playhead position."""
        self._position_ms = position_ms
        self._ensure_position_visible()
        self.update()

    def set_project(self, project: Project) -> None:
        """Set the project to display subtitles from."""
        self._project = project
        self._selected_subtitles.clear()
        self.update()

    def set_zoom(self, zoom: float) -> None:
        """Set zoom level (pixels per millisecond)."""
        old_zoom = self._zoom_level
        self._zoom_level = max(0.005, min(2.0, zoom))
        if old_zoom != self._zoom_level:
            self.zoom_changed.emit(self._zoom_level)
        self.update()

    def get_zoom(self) -> float:
        """Get current zoom level."""
        return self._zoom_level

    def zoom_in(self) -> None:
        """Zoom in."""
        self.set_zoom(self._zoom_level * 1.25)

    def zoom_out(self) -> None:
        """Zoom out."""
        self.set_zoom(self._zoom_level / 1.25)

    def _fit_to_view(self) -> None:
        """Fit timeline to view width."""
        if self._duration_ms > 0 and self.width() > 0:
            self._zoom_level = (self.width() - 20) / self._duration_ms
            self._scroll_offset = 0
            self.zoom_changed.emit(self._zoom_level)

    def fit_to_view(self) -> None:
        """Public method to fit timeline to view."""
        self._fit_to_view()
        self.update()

    def toggle_waveform(self, visible: bool) -> None:
        """Toggle waveform visibility."""
        self._show_waveform = visible
        self.update()

    def get_selected_subtitles(self) -> List[Subtitle]:
        """Get list of selected subtitles."""
        if not self._project:
            return []
        return [s for s in self._project.subtitles if s.id in self._selected_subtitles]

    def select_subtitle(self, subtitle: Subtitle) -> None:
        """Select a single subtitle programmatically."""
        self._selected_subtitles.clear()
        if subtitle and subtitle.id:
            self._selected_subtitles.add(subtitle.id)
            self._last_selected_index = self._get_subtitle_index(subtitle)
        self.update()

    def clear_selection(self) -> None:
        """Clear all selections."""
        self._selected_subtitles.clear()
        self._last_selected_index = -1
        self.update()

    def _get_subtitle_index(self, subtitle: Subtitle) -> int:
        """Get index of subtitle in project list."""
        if not self._project:
            return -1
        for i, s in enumerate(self._project.subtitles):
            if s.id == subtitle.id:
                return i
        return -1

    def _ensure_position_visible(self) -> None:
        """Ensure playhead is visible in the view."""
        playhead_x = self._ms_to_x(self._position_ms)
        view_width = self.width()

        if playhead_x < self._scroll_offset:
            self._scroll_offset = max(0, playhead_x - 50)
        elif playhead_x > self._scroll_offset + view_width - 50:
            self._scroll_offset = playhead_x - view_width + 50

    def _ms_to_x(self, ms: int) -> float:
        """Convert milliseconds to x coordinate."""
        return ms * self._zoom_level

    def _x_to_ms(self, x: float) -> int:
        """Convert x coordinate to milliseconds."""
        return int((x + self._scroll_offset) / self._zoom_level)

    def _get_subtitle_rect(self, subtitle: Subtitle) -> QRectF:
        """Get the rectangle for a subtitle block."""
        x1 = self._ms_to_x(subtitle.start_ms) - self._scroll_offset
        x2 = self._ms_to_x(subtitle.end_ms) - self._scroll_offset
        return QRectF(x1, 60, x2 - x1, 80)

    def _find_subtitle_at(self, x: float, y: float) -> Optional[Subtitle]:
        """Find subtitle at the given coordinates."""
        if not self._project:
            return None

        for subtitle in self._project.subtitles:
            rect = self._get_subtitle_rect(subtitle)
            if rect.contains(x, y):
                return subtitle
        return None

    def _get_edge_at(self, subtitle: Subtitle, x: float) -> Optional[str]:
        """Determine if x is near a subtitle edge."""
        rect = self._get_subtitle_rect(subtitle)
        edge_threshold = 8

        if abs(x - rect.left()) < edge_threshold:
            return 'left'
        elif abs(x - rect.right()) < edge_threshold:
            return 'right'
        elif rect.contains(x, rect.center().y()):
            return 'move'
        return None

    def _is_selected(self, subtitle: Subtitle) -> bool:
        """Check if subtitle is selected."""
        return subtitle.id in self._selected_subtitles

    def paintEvent(self, event) -> None:
        """Paint the timeline."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Background
        painter.fillRect(0, 0, width, height, self._bg_color)

        if self._duration_ms == 0:
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(self.rect(), Qt.AlignCenter, "Load a video to see the timeline")
            return

        # Draw time grid
        self._draw_grid(painter, width, height)

        # Draw waveform
        if self._show_waveform and self._waveform_data is not None:
            self._draw_waveform(painter, width)

        # Draw subtitle blocks
        if self._project:
            self._draw_subtitles(painter)

        # Draw playhead
        self._draw_playhead(painter, height)

    def _draw_grid(self, painter: QPainter, width: int, height: int) -> None:
        """Draw time grid lines."""
        painter.setPen(QPen(self._grid_color, 1))

        # Calculate grid interval based on zoom
        if self._zoom_level > 0.5:
            interval_ms = 500
        elif self._zoom_level > 0.1:
            interval_ms = 1000
        elif self._zoom_level > 0.05:
            interval_ms = 5000
        else:
            interval_ms = 10000

        start_ms = int(self._scroll_offset / self._zoom_level)
        start_ms = (start_ms // interval_ms) * interval_ms

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        end_ms = min(self._duration_ms, int((self._scroll_offset + width) / self._zoom_level) + interval_ms)

        for ms in range(start_ms, end_ms, interval_ms):
            x = self._ms_to_x(ms) - self._scroll_offset
            if 0 <= x <= width:
                painter.setPen(QPen(self._grid_color, 1))
                painter.drawLine(int(x), 0, int(x), height)

                # Time label
                s = ms // 1000
                m = s // 60
                label = f"{m}:{s % 60:02d}"
                painter.setPen(QColor(150, 150, 150))
                painter.drawText(int(x) + 2, 12, label)

    def _draw_waveform(self, painter: QPainter, width: int) -> None:
        """Draw the audio waveform."""
        if self._waveform_data is None or len(self._waveform_data) == 0:
            return

        painter.setPen(QPen(self._waveform_color, 1))

        waveform_height = 50
        center_y = 35

        samples_per_ms = len(self._waveform_data) / self._duration_ms if self._duration_ms > 0 else 1

        path = QPainterPath()
        first_point = True

        for x in range(width):
            ms = self._x_to_ms(x)
            if 0 <= ms < self._duration_ms:
                idx = int(ms * samples_per_ms)
                if 0 <= idx < len(self._waveform_data):
                    amplitude = abs(self._waveform_data[idx])
                    y = center_y - amplitude * waveform_height

                    if first_point:
                        path.moveTo(x, y)
                        first_point = False
                    else:
                        path.lineTo(x, y)

        painter.drawPath(path)

    def _draw_subtitles(self, painter: QPainter) -> None:
        """Draw subtitle blocks."""
        if not self._project:
            return

        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)

        for subtitle in self._project.subtitles:
            rect = self._get_subtitle_rect(subtitle)

            # Skip if not visible
            if rect.right() < 0 or rect.left() > self.width():
                continue

            # Draw block
            is_selected = self._is_selected(subtitle)
            color = self._subtitle_selected_color if is_selected else self._subtitle_color
            painter.fillRect(rect, QBrush(color))

            # Draw border
            border_color = QColor(255, 255, 255) if is_selected else QColor(100, 100, 100)
            painter.setPen(QPen(border_color, 2 if is_selected else 1))
            painter.drawRect(rect)

            # Draw text (truncated to fit)
            painter.setPen(self._text_color)
            text = subtitle.get_full_text()
            max_chars = max(5, int(rect.width() / 7))
            if len(text) > max_chars:
                text = text[:max_chars - 3] + "..."
            text_rect = rect.adjusted(4, 4, -4, -4)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, text)

    def _draw_playhead(self, painter: QPainter, height: int) -> None:
        """Draw the playhead."""
        x = self._ms_to_x(self._position_ms) - self._scroll_offset

        if 0 <= x <= self.width():
            painter.setPen(QPen(self._playhead_color, 2))
            painter.drawLine(int(x), 0, int(x), height)

            # Draw playhead triangle
            painter.setBrush(QBrush(self._playhead_color))
            triangle = QPainterPath()
            triangle.moveTo(x - 6, 0)
            triangle.lineTo(x + 6, 0)
            triangle.lineTo(x, 10)
            triangle.closeSubpath()
            painter.drawPath(triangle)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press with multi-selection support."""
        if event.button() == Qt.LeftButton:
            x, y = event.position().x(), event.position().y()
            modifiers = event.modifiers()

            subtitle = self._find_subtitle_at(x, y)

            if subtitle:
                subtitle_index = self._get_subtitle_index(subtitle)

                if modifiers & Qt.ControlModifier:
                    # Ctrl+click: Toggle selection
                    if subtitle.id in self._selected_subtitles:
                        self._selected_subtitles.remove(subtitle.id)
                    else:
                        self._selected_subtitles.add(subtitle.id)
                    self._last_selected_index = subtitle_index

                elif modifiers & Qt.ShiftModifier and self._last_selected_index >= 0:
                    # Shift+click: Range selection
                    start_idx = min(self._last_selected_index, subtitle_index)
                    end_idx = max(self._last_selected_index, subtitle_index)
                    for i in range(start_idx, end_idx + 1):
                        if i < len(self._project.subtitles):
                            self._selected_subtitles.add(self._project.subtitles[i].id)

                else:
                    # Normal click: Select single
                    self._selected_subtitles.clear()
                    self._selected_subtitles.add(subtitle.id)
                    self._last_selected_index = subtitle_index

                # Setup dragging
                self._drag_edge = self._get_edge_at(subtitle, x)
                if self._drag_edge:
                    self._dragging = True
                    self._drag_start_x = x
                    self._drag_start_pos = subtitle.start_ms
                    self._drag_original_start = subtitle.start_ms  # Store original for undo
                    self._drag_original_end = subtitle.end_ms  # Store original for undo
                    self._drag_subtitle = subtitle

                # Emit signals
                self.subtitle_selected.emit(subtitle)
                self.subtitles_selected.emit(self.get_selected_subtitles())

            else:
                # Click on empty area
                if not (modifiers & Qt.ControlModifier):
                    self._selected_subtitles.clear()
                    self.subtitles_selected.emit([])

                # Seek to position
                ms = self._x_to_ms(x)
                self.position_changed.emit(ms)

            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move."""
        x = event.position().x()

        if self._dragging and self._drag_subtitle:
            delta_x = x - self._drag_start_x
            delta_ms = int(delta_x / self._zoom_level)

            if self._drag_edge == 'left':
                new_start = max(0, self._drag_start_pos + delta_ms)
                new_start = min(new_start, self._drag_subtitle.end_ms - 100)
                self._drag_subtitle.start_ms = new_start
            elif self._drag_edge == 'right':
                original_duration = self._drag_subtitle.end_ms - self._drag_start_pos
                new_end = self._drag_start_pos + original_duration + delta_ms
                new_end = max(self._drag_subtitle.start_ms + 100, new_end)
                self._drag_subtitle.end_ms = new_end
            elif self._drag_edge == 'move':
                duration = self._drag_subtitle.end_ms - self._drag_subtitle.start_ms
                new_start = max(0, self._drag_start_pos + delta_ms)
                self._drag_subtitle.start_ms = new_start
                self._drag_subtitle.end_ms = new_start + duration

            self.update()
        else:
            # Update cursor based on hover
            subtitle = self._find_subtitle_at(x, event.position().y())
            if subtitle:
                edge = self._get_edge_at(subtitle, x)
                if edge in ('left', 'right'):
                    self.setCursor(Qt.SizeHorCursor)
                elif edge == 'move':
                    self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if self._dragging and self._drag_subtitle:
            # Only emit if position actually changed
            if (self._drag_subtitle.start_ms != self._drag_original_start or
                    self._drag_subtitle.end_ms != self._drag_original_end):
                self.subtitle_moved.emit(
                    self._drag_subtitle,
                    self._drag_original_start,
                    self._drag_original_end,
                    self._drag_subtitle.start_ms,
                    self._drag_subtitle.end_ms
                )
        self._dragging = False
        self._drag_edge = None
        self._drag_subtitle = None
        self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zoom/scroll."""
        delta = event.angleDelta().y()

        if event.modifiers() & Qt.ControlModifier:
            # Zoom centered on mouse position
            mouse_x = event.position().x()
            mouse_ms = self._x_to_ms(mouse_x)

            factor = 1.15 if delta > 0 else 1 / 1.15
            new_zoom = max(0.005, min(2.0, self._zoom_level * factor))

            # Adjust scroll to keep mouse position at same time
            self._zoom_level = new_zoom
            new_x = self._ms_to_x(mouse_ms)
            self._scroll_offset = max(0, new_x - mouse_x)

            self.zoom_changed.emit(self._zoom_level)
        else:
            # Horizontal scroll
            scroll_amount = -delta * 0.5
            max_scroll = max(0, self._ms_to_x(self._duration_ms) - self.width())
            self._scroll_offset = max(0, min(max_scroll, self._scroll_offset + scroll_amount))

        self.update()

    def keyPressEvent(self, event) -> None:
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_A and event.modifiers() & Qt.ControlModifier:
            # Ctrl+A: Select all
            if self._project:
                self._selected_subtitles = {s.id for s in self._project.subtitles}
                self.subtitles_selected.emit(self.get_selected_subtitles())
                self.update()
        elif event.key() == Qt.Key_Escape:
            # Escape: Clear selection
            self.clear_selection()
            self.subtitles_selected.emit([])
        else:
            super().keyPressEvent(event)


class TimelinePanel(QWidget):
    """Timeline panel containing waveform and controls."""

    # Signals
    position_changed = Signal(int)
    subtitle_selected = Signal(object)
    subtitles_selected = Signal(list)
    subtitle_timing_changed = Signal(object, int, int, int, int)  # subtitle, old_start, old_end, new_start, new_end

    def __init__(self, parent=None):
        super().__init__(parent)

        self._project: Optional[Project] = None
        self._audio_path: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Controls bar
        controls = QHBoxLayout()

        # Zoom controls
        controls.addWidget(QLabel("Zoom:"))

        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedWidth(30)
        self.btn_zoom_out.setToolTip("Zoom Out (Ctrl+Scroll)")
        self.btn_zoom_out.clicked.connect(self._on_zoom_out)
        controls.addWidget(self.btn_zoom_out)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(1, 200)
        self.zoom_slider.setValue(50)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.setToolTip("Zoom Level")
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        controls.addWidget(self.zoom_slider)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedWidth(30)
        self.btn_zoom_in.setToolTip("Zoom In (Ctrl+Scroll)")
        self.btn_zoom_in.clicked.connect(self._on_zoom_in)
        controls.addWidget(self.btn_zoom_in)

        self.btn_zoom_fit = QPushButton("Fit")
        self.btn_zoom_fit.setFixedWidth(40)
        self.btn_zoom_fit.setToolTip("Fit to View")
        self.btn_zoom_fit.clicked.connect(self._on_zoom_fit)
        controls.addWidget(self.btn_zoom_fit)

        controls.addSpacing(20)

        # Selection info
        self.selection_label = QLabel("")
        self.selection_label.setStyleSheet("color: #888;")
        controls.addWidget(self.selection_label)

        controls.addStretch()

        # Word-by-word mode toggle
        self.btn_word_mode = QPushButton("Word-by-Word")
        self.btn_word_mode.setCheckable(True)
        self.btn_word_mode.setToolTip("Show individual word timing blocks")
        controls.addWidget(self.btn_word_mode)

        layout.addLayout(controls)

        # Waveform widget
        self.waveform = WaveformWidget(self)
        self.waveform.position_changed.connect(self.position_changed)
        self.waveform.subtitle_selected.connect(self._on_subtitle_selected)
        self.waveform.subtitles_selected.connect(self._on_subtitles_selected)
        self.waveform.subtitle_moved.connect(self._on_subtitle_moved)
        self.waveform.zoom_changed.connect(self._on_waveform_zoom_changed)
        layout.addWidget(self.waveform, 1)

        # Horizontal scrollbar
        self.h_scrollbar = QScrollBar(Qt.Horizontal)
        self.h_scrollbar.valueChanged.connect(self._on_scroll)
        layout.addWidget(self.h_scrollbar)

    def set_project(self, project: Project) -> None:
        """Set the project."""
        self._project = project
        self.waveform.set_project(project)
        self._update_selection_label()

    def set_position(self, position_ms: int) -> None:
        """Set the playhead position."""
        self.waveform.set_position(position_ms)

    def set_duration(self, duration_ms: int) -> None:
        """Set the timeline duration."""
        self.waveform.set_duration(duration_ms)
        self._update_scrollbar()

    def load_audio(self, path: str) -> None:
        """Load audio and generate waveform."""
        self._audio_path = path

        # Load waveform in background
        QTimer.singleShot(100, lambda: self._load_waveform(path))

    def _load_waveform(self, path: str) -> None:
        """Load waveform data from audio file."""
        try:
            import librosa

            # Load audio (mono, downsampled for display)
            y, sr = librosa.load(path, sr=8000, mono=True)

            # Downsample for display
            hop = max(1, len(y) // 10000)
            waveform = y[::hop]

            # Normalize
            if np.max(np.abs(waveform)) > 0:
                waveform = waveform / np.max(np.abs(waveform))

            duration_ms = int(len(y) / sr * 1000)
            self.waveform.set_waveform(waveform, duration_ms)
            self._update_scrollbar()

        except Exception as e:
            print(f"Error loading waveform: {e}")

    def toggle_waveform(self, visible: bool) -> None:
        """Toggle waveform visibility."""
        self.waveform.toggle_waveform(visible)

    def update_subtitles(self) -> None:
        """Update subtitle display."""
        self.waveform.update()

    def update_subtitle(self, subtitle: Subtitle) -> None:
        """Update a specific subtitle."""
        self.waveform.update()

    def shift_all_subtitles(self, shift_ms: int) -> None:
        """Shift all subtitle timings."""
        if not self._project:
            return

        for subtitle in self._project.subtitles:
            subtitle.start_ms = max(0, subtitle.start_ms + shift_ms)
            subtitle.end_ms = max(subtitle.start_ms + 100, subtitle.end_ms + shift_ms)

            for word in subtitle.words:
                word.start_ms = max(0, word.start_ms + shift_ms)
                word.end_ms = max(word.start_ms + 50, word.end_ms + shift_ms)

        self.waveform.update()

    def get_selected_subtitles(self) -> List[Subtitle]:
        """Get list of selected subtitles."""
        return self.waveform.get_selected_subtitles()

    def _update_scrollbar(self) -> None:
        """Update horizontal scrollbar range."""
        if self.waveform._duration_ms > 0:
            total_width = int(self.waveform._ms_to_x(self.waveform._duration_ms))
            view_width = self.waveform.width()
            if total_width > view_width:
                self.h_scrollbar.setRange(0, total_width - view_width)
                self.h_scrollbar.setPageStep(view_width)
                self.h_scrollbar.setVisible(True)
            else:
                self.h_scrollbar.setVisible(False)

    def _update_selection_label(self) -> None:
        """Update selection info label."""
        selected = self.waveform.get_selected_subtitles()
        if len(selected) == 0:
            self.selection_label.setText("")
        elif len(selected) == 1:
            self.selection_label.setText("1 subtitle selected")
        else:
            self.selection_label.setText(f"{len(selected)} subtitles selected (Ctrl+click to add)")

    @Slot(int)
    def _on_zoom_slider_changed(self, value: int) -> None:
        """Handle zoom slider change."""
        # Map 1-200 to 0.005-1.0 (logarithmic scale for better control)
        zoom = 0.005 * (2.0 ** (value / 40.0))
        self.waveform.set_zoom(zoom)
        self._update_scrollbar()

    @Slot()
    def _on_zoom_in(self) -> None:
        """Handle zoom in button."""
        self.waveform.zoom_in()
        self._update_scrollbar()

    @Slot()
    def _on_zoom_out(self) -> None:
        """Handle zoom out button."""
        self.waveform.zoom_out()
        self._update_scrollbar()

    @Slot()
    def _on_zoom_fit(self) -> None:
        """Fit timeline to view."""
        self.waveform.fit_to_view()
        self._update_scrollbar()

    @Slot(float)
    def _on_waveform_zoom_changed(self, zoom: float) -> None:
        """Handle zoom change from waveform widget."""
        # Update slider to match (reverse of _on_zoom_slider_changed)
        import math
        value = int(40.0 * math.log2(zoom / 0.005))
        value = max(1, min(200, value))
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(value)
        self.zoom_slider.blockSignals(False)
        self._update_scrollbar()

    @Slot(int)
    def _on_scroll(self, value: int) -> None:
        """Handle scrollbar change."""
        self.waveform._scroll_offset = value
        self.waveform.update()

    @Slot(object)
    def _on_subtitle_selected(self, subtitle: Subtitle) -> None:
        """Handle single subtitle selection."""
        self.subtitle_selected.emit(subtitle)
        self._update_selection_label()

    @Slot(list)
    def _on_subtitles_selected(self, subtitles: list) -> None:
        """Handle multiple subtitle selection."""
        self.subtitles_selected.emit(subtitles)
        self._update_selection_label()

    @Slot(object, int, int, int, int)
    def _on_subtitle_moved(self, subtitle: Subtitle, old_start: int, old_end: int, new_start: int, new_end: int) -> None:
        """Handle subtitle moved on timeline."""
        # Forward the signal with all timing info for undo support
        self.subtitle_timing_changed.emit(subtitle, old_start, old_end, new_start, new_end)
