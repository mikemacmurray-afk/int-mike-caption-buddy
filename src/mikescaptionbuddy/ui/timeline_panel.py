"""Timeline panel with waveform and subtitle blocks."""

import os
from typing import Optional, List
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QSlider, QLabel, QPushButton, QSizePolicy
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
    subtitle_selected = Signal(object)  # selected subtitle
    subtitle_moved = Signal(object, int, int)  # subtitle, new_start, new_end

    def __init__(self, parent=None):
        super().__init__(parent)

        self._waveform_data: Optional[np.ndarray] = None
        self._duration_ms = 0
        self._position_ms = 0
        self._zoom_level = 1.0  # pixels per millisecond
        self._scroll_offset = 0
        self._project: Optional[Project] = None
        self._selected_subtitle: Optional[Subtitle] = None
        self._dragging = False
        self._drag_edge: Optional[str] = None  # 'left', 'right', or 'move'
        self._drag_start_x = 0
        self._drag_start_pos = 0
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
        self._calculate_zoom()
        self.update()

    def set_duration(self, duration_ms: int) -> None:
        """Set the duration without waveform data."""
        self._duration_ms = duration_ms
        self._calculate_zoom()
        self.update()

    def set_position(self, position_ms: int) -> None:
        """Set the playhead position."""
        self._position_ms = position_ms
        self._ensure_position_visible()
        self.update()

    def set_project(self, project: Project) -> None:
        """Set the project to display subtitles from."""
        self._project = project
        self.update()

    def set_zoom(self, zoom: float) -> None:
        """Set zoom level (pixels per millisecond)."""
        self._zoom_level = max(0.01, min(1.0, zoom))
        self.update()

    def toggle_waveform(self, visible: bool) -> None:
        """Toggle waveform visibility."""
        self._show_waveform = visible
        self.update()

    def _calculate_zoom(self) -> None:
        """Calculate appropriate zoom level."""
        if self._duration_ms > 0:
            # Default: fit 30 seconds in view
            self._zoom_level = self.width() / min(30000, self._duration_ms)

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
        interval_ms = 1000  # 1 second default
        if self._zoom_level < 0.05:
            interval_ms = 10000  # 10 seconds
        elif self._zoom_level < 0.1:
            interval_ms = 5000  # 5 seconds

        start_ms = int(self._scroll_offset / self._zoom_level)
        start_ms = (start_ms // interval_ms) * interval_ms

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        for ms in range(start_ms, self._duration_ms, interval_ms):
            x = self._ms_to_x(ms) - self._scroll_offset
            if 0 <= x <= width:
                painter.drawLine(int(x), 0, int(x), height)

                # Time label
                s = ms // 1000
                m = s // 60
                label = f"{m}:{s % 60:02d}"
                painter.setPen(QColor(150, 150, 150))
                painter.drawText(int(x) + 2, 12, label)
                painter.setPen(QPen(self._grid_color, 1))

    def _draw_waveform(self, painter: QPainter, width: int) -> None:
        """Draw the audio waveform."""
        if self._waveform_data is None or len(self._waveform_data) == 0:
            return

        painter.setPen(QPen(self._waveform_color, 1))

        waveform_height = 50
        center_y = 35

        # Calculate visible range
        start_idx = int((self._scroll_offset / self._zoom_level) / self._duration_ms * len(self._waveform_data))
        samples_per_pixel = max(1, len(self._waveform_data) // int(self._duration_ms * self._zoom_level))

        path = QPainterPath()
        first_point = True

        for x in range(width):
            idx = start_idx + int(x * samples_per_pixel / self._zoom_level)
            if 0 <= idx < len(self._waveform_data):
                # Get max amplitude in this pixel's range
                end_idx = min(idx + samples_per_pixel, len(self._waveform_data))
                if end_idx > idx:
                    amplitude = np.max(np.abs(self._waveform_data[idx:end_idx]))
                    y = center_y - amplitude * waveform_height

                    if first_point:
                        path.moveTo(x, y)
                        first_point = False
                    else:
                        path.lineTo(x, y)

        # Draw mirrored waveform
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
            is_selected = subtitle == self._selected_subtitle
            color = self._subtitle_selected_color if is_selected else self._subtitle_color
            painter.fillRect(rect, QBrush(color))

            # Draw border
            border_color = QColor(255, 255, 255) if is_selected else QColor(100, 100, 100)
            painter.setPen(QPen(border_color, 2 if is_selected else 1))
            painter.drawRect(rect)

            # Draw text (truncated to fit)
            painter.setPen(self._text_color)
            text = subtitle.get_full_text()
            if len(text) > 30:
                text = text[:27] + "..."
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
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            x, y = event.position().x(), event.position().y()

            # Check for subtitle interaction
            subtitle = self._find_subtitle_at(x, y)
            if subtitle:
                self._selected_subtitle = subtitle
                self._drag_edge = self._get_edge_at(subtitle, x)
                if self._drag_edge:
                    self._dragging = True
                    self._drag_start_x = x
                    self._drag_start_pos = subtitle.start_ms
                self.subtitle_selected.emit(subtitle)
            else:
                # Click on timeline - seek
                self._selected_subtitle = None
                ms = self._x_to_ms(x)
                self.position_changed.emit(ms)

            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move."""
        x = event.position().x()

        if self._dragging and self._selected_subtitle:
            delta_x = x - self._drag_start_x
            delta_ms = int(delta_x / self._zoom_level)

            if self._drag_edge == 'left':
                new_start = max(0, self._drag_start_pos + delta_ms)
                new_start = min(new_start, self._selected_subtitle.end_ms - 100)
                self._selected_subtitle.start_ms = new_start
            elif self._drag_edge == 'right':
                original_end = self._selected_subtitle.end_ms
                new_end = self._drag_start_pos + (original_end - self._selected_subtitle.start_ms) + delta_ms
                new_end = max(self._selected_subtitle.start_ms + 100, new_end)
                self._selected_subtitle.end_ms = new_end
            elif self._drag_edge == 'move':
                delta_ms = int(delta_x / self._zoom_level)
                duration = self._selected_subtitle.end_ms - self._selected_subtitle.start_ms
                new_start = max(0, self._drag_start_pos + delta_ms)
                self._selected_subtitle.start_ms = new_start
                self._selected_subtitle.end_ms = new_start + duration

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
        if self._dragging and self._selected_subtitle:
            self.subtitle_moved.emit(
                self._selected_subtitle,
                self._selected_subtitle.start_ms,
                self._selected_subtitle.end_ms
            )
        self._dragging = False
        self._drag_edge = None
        self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zoom/scroll."""
        if event.modifiers() & Qt.ControlModifier:
            # Zoom
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9
            self._zoom_level = max(0.01, min(1.0, self._zoom_level * factor))
        else:
            # Scroll
            delta = event.angleDelta().y()
            self._scroll_offset = max(0, self._scroll_offset - delta)

        self.update()


class TimelinePanel(QWidget):
    """Timeline panel containing waveform and controls."""

    # Signals
    position_changed = Signal(int)
    subtitle_selected = Signal(object)

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

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(1, 100)
        self.zoom_slider.setValue(50)
        self.zoom_slider.setFixedWidth(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        controls.addWidget(self.zoom_slider)

        self.btn_zoom_fit = QPushButton("Fit")
        self.btn_zoom_fit.setFixedWidth(40)
        self.btn_zoom_fit.clicked.connect(self._on_zoom_fit)
        controls.addWidget(self.btn_zoom_fit)

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
        self.waveform.subtitle_selected.connect(self.subtitle_selected)
        self.waveform.subtitle_moved.connect(self._on_subtitle_moved)
        layout.addWidget(self.waveform, 1)

    def set_project(self, project: Project) -> None:
        """Set the project."""
        self._project = project
        self.waveform.set_project(project)

    def set_position(self, position_ms: int) -> None:
        """Set the playhead position."""
        self.waveform.set_position(position_ms)

    def set_duration(self, duration_ms: int) -> None:
        """Set the timeline duration."""
        self.waveform.set_duration(duration_ms)

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

            # Downsample for display (keep ~1000 samples per second)
            hop = max(1, len(y) // (sr * 10))
            waveform = y[::hop]

            # Normalize
            if np.max(np.abs(waveform)) > 0:
                waveform = waveform / np.max(np.abs(waveform))

            duration_ms = int(len(y) / sr * 1000)
            self.waveform.set_waveform(waveform, duration_ms)

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

    @Slot(int)
    def _on_zoom_changed(self, value: int) -> None:
        """Handle zoom slider change."""
        # Map 1-100 to 0.01-1.0
        zoom = value / 100.0
        self.waveform.set_zoom(zoom)

    @Slot()
    def _on_zoom_fit(self) -> None:
        """Fit timeline to view."""
        self.zoom_slider.setValue(50)

    @Slot(object, int, int)
    def _on_subtitle_moved(self, subtitle: Subtitle, new_start: int, new_end: int) -> None:
        """Handle subtitle moved on timeline."""
        # This will be handled by the main window for undo support
        pass
