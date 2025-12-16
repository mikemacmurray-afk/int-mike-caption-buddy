"""Video preview panel with playback controls."""

import os
import sys
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QFrame, QSizePolicy, QApplication, QComboBox
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QRect
from PySide6.QtGui import QColor, QPalette, QPainter, QFont, QPen, QBrush


class CaptionOverlay(QLabel):
    """Caption bar for displaying subtitles below video."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)

        self._v_align = "bottom"  # top, middle, bottom
        self._h_align = "center"  # left, center, right
        self._font_family = "Arial"
        self._font_size = 24
        self._primary_color = "#FFFFFF"
        self._outline_color = "#000000"

        self._update_style()

    def _update_style(self) -> None:
        """Update the label style."""
        # Set horizontal alignment
        if self._h_align == "left":
            align = "left"
        elif self._h_align == "right":
            align = "right"
        else:
            align = "center"

        self.setStyleSheet(f"""
            QLabel {{
                color: {self._primary_color};
                font-family: {self._font_family};
                font-size: {self._font_size}px;
                font-weight: bold;
                background-color: #1a1a1a;
                padding: 10px 20px;
                border-radius: 4px;
                qproperty-alignment: 'Align{align.title()} | AlignVCenter';
            }}
        """)

    def set_caption(self, text: str, style: dict = None) -> None:
        """Set the caption text and style."""
        if style:
            self._font_family = style.get('font_family', 'Arial')
            self._font_size = style.get('font_size', 32)
            self._primary_color = style.get('primary_color', '#FFFFFF')
            self._outline_color = style.get('outline_color', '#000000')
            self._update_style()

        self.setText(text)
        self.setVisible(bool(text))

    def set_alignment(self, v_align: str, h_align: str) -> None:
        """Set caption alignment."""
        self._v_align = v_align
        self._h_align = h_align
        self._update_style()

    def clear(self) -> None:
        """Clear the caption."""
        self.setText("")
        self.hide()


class VideoPanel(QWidget):
    """Video preview panel with mpv player and playback controls."""

    # Signals
    position_changed = Signal(int)  # position in ms
    duration_changed = Signal(int)  # duration in ms
    playback_state_changed = Signal(bool)  # playing

    def __init__(self, parent=None):
        super().__init__(parent)

        self._duration_ms = 0
        self._position_ms = 0
        self._is_playing = False
        self._video_path: Optional[str] = None
        self._audio_only = False
        self._mpv_player = None
        self._captions_visible = True
        self._mpv_initialized = False
        self._project = None
        self._v_align = "bottom"
        self._h_align = "center"

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self) -> None:
        """Setup the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Video container - use a simple QWidget for MPV embedding
        self.video_container = QWidget()
        self.video_container.setMinimumSize(400, 300)
        self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_container.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.video_container.setAttribute(Qt.WA_NativeWindow)
        self.video_container.setStyleSheet("background-color: #1e1e1e;")

        # Placeholder label (shown when no video)
        self.video_layout = QVBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(0, 0, 0, 0)
        self.placeholder_label = QLabel("No video loaded\n\nFile → Open Video to begin")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #888; font-size: 14px; background-color: #1e1e1e;")
        self.video_layout.addWidget(self.placeholder_label)

        layout.addWidget(self.video_container, 1)

        # Caption display bar (shows current caption text - below video)
        self.caption_overlay = CaptionOverlay()
        self.caption_overlay.setMinimumHeight(50)
        self.caption_overlay.setMaximumHeight(80)
        self.caption_overlay.hide()  # Hidden until there's a caption
        layout.addWidget(self.caption_overlay)

        # Alignment controls bar
        align_widget = QWidget()
        align_layout = QHBoxLayout(align_widget)
        align_layout.setContentsMargins(4, 2, 4, 2)

        align_layout.addWidget(QLabel("Caption Position:"))

        self.v_align_combo = QComboBox()
        self.v_align_combo.addItems(["Top", "Middle", "Bottom"])
        self.v_align_combo.setCurrentIndex(2)  # Default: Bottom
        self.v_align_combo.setToolTip("Vertical alignment")
        self.v_align_combo.currentTextChanged.connect(self._on_v_align_changed)
        align_layout.addWidget(self.v_align_combo)

        self.h_align_combo = QComboBox()
        self.h_align_combo.addItems(["Left", "Center", "Right"])
        self.h_align_combo.setCurrentIndex(1)  # Default: Center
        self.h_align_combo.setToolTip("Horizontal alignment")
        self.h_align_combo.currentTextChanged.connect(self._on_h_align_changed)
        align_layout.addWidget(self.h_align_combo)

        align_layout.addStretch()
        layout.addWidget(align_widget)

        # Controls container
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(4, 4, 4, 4)

        # Play/Pause button
        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(40)
        self.btn_play.setToolTip("Play/Pause (Space)")
        self.btn_play.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.btn_play)

        # Stop button
        self.btn_stop = QPushButton("⬛")
        self.btn_stop.setFixedWidth(40)
        self.btn_stop.setToolTip("Stop")
        self.btn_stop.clicked.connect(self.stop)
        controls_layout.addWidget(self.btn_stop)

        # Time label
        self.time_label = QLabel("00:00:00")
        self.time_label.setFixedWidth(70)
        controls_layout.addWidget(self.time_label)

        # Seek slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderPressed.connect(self._on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self._on_slider_released)
        self.seek_slider.sliderMoved.connect(self._on_slider_moved)
        controls_layout.addWidget(self.seek_slider, 1)

        # Duration label
        self.duration_label = QLabel("00:00:00")
        self.duration_label.setFixedWidth(70)
        controls_layout.addWidget(self.duration_label)

        # Volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        controls_layout.addWidget(self.volume_slider)

        # Caption toggle
        self.btn_captions = QPushButton("CC")
        self.btn_captions.setFixedWidth(40)
        self.btn_captions.setCheckable(True)
        self.btn_captions.setChecked(True)
        self.btn_captions.setToolTip("Toggle Captions")
        self.btn_captions.clicked.connect(self._on_captions_toggled)
        controls_layout.addWidget(self.btn_captions)

        layout.addWidget(controls_widget)

        # Initially disable controls
        self._set_controls_enabled(False)

    def _init_mpv(self) -> bool:
        """Initialize MPV player (called when needed)."""
        if self._mpv_initialized:
            return self._mpv_player is not None

        self._mpv_initialized = True

        try:
            import mpv
        except ImportError as e:
            print(f"Warning: python-mpv not installed: {e}")
            self._mpv_player = None
            return False

        # Ensure the widget has a valid window ID
        QApplication.processEvents()
        wid = int(self.video_container.winId())

        # Try multiple video output drivers in order of preference
        if sys.platform == 'win32':
            vo_drivers = ['gpu-next', 'gpu', 'd3d11', 'opengl', 'direct3d', None]
        else:
            vo_drivers = ['gpu', 'opengl', 'x11', None]

        last_error = None
        for vo in vo_drivers:
            try:
                mpv_opts = {
                    'wid': str(wid),
                    'hwdec': 'auto',
                    'keep_open': 'yes',
                    'idle': 'yes',
                    'osc': 'no',
                    'input_default_bindings': 'no',
                    'input_vo_keyboard': 'no',
                }
                if vo:
                    mpv_opts['vo'] = vo

                self._mpv_player = mpv.MPV(**mpv_opts)

                # Setup event handlers
                @self._mpv_player.property_observer('time-pos')
                def time_observer(name, value):
                    if value is not None:
                        self._position_ms = int(value * 1000)
                        self.position_changed.emit(self._position_ms)

                @self._mpv_player.property_observer('duration')
                def duration_observer(name, value):
                    if value is not None:
                        self._duration_ms = int(value * 1000)
                        self.duration_changed.emit(self._duration_ms)

                @self._mpv_player.property_observer('pause')
                def pause_observer(name, value):
                    self._is_playing = not value
                    self._update_play_button()

                print(f"MPV initialized successfully with vo={vo or 'default'}")
                return True

            except Exception as e:
                last_error = e
                print(f"MPV init failed with vo={vo}: {e}")
                if self._mpv_player:
                    try:
                        self._mpv_player.terminate()
                    except:
                        pass
                    self._mpv_player = None
                continue

        print(f"Warning: Could not initialize MPV with any video output: {last_error}")
        self._mpv_player = None
        return False

    def _setup_timer(self) -> None:
        """Setup update timer for UI sync."""
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_ui)
        self._update_timer.start(100)  # 10 fps update

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable playback controls."""
        self.btn_play.setEnabled(enabled)
        self.btn_stop.setEnabled(enabled)
        self.seek_slider.setEnabled(enabled)
        self.volume_slider.setEnabled(enabled)
        self.btn_captions.setEnabled(enabled)

    def _update_play_button(self) -> None:
        """Update play button text based on state."""
        self.btn_play.setText("⏸" if self._is_playing else "▶")

    def _update_ui(self) -> None:
        """Update UI elements."""
        if not self._video_path:
            return

        # Update time labels
        self.time_label.setText(self._format_time(self._position_ms))
        self.duration_label.setText(self._format_time(self._duration_ms))

        # Update slider (if not being dragged)
        if not self.seek_slider.isSliderDown() and self._duration_ms > 0:
            slider_pos = int((self._position_ms / self._duration_ms) * 1000)
            self.seek_slider.setValue(slider_pos)

    def _format_time(self, ms: int) -> str:
        """Format milliseconds as HH:MM:SS."""
        s = ms // 1000
        m = s // 60
        h = m // 60
        return f"{h:02d}:{m % 60:02d}:{s % 60:02d}"

    # Public methods

    def load_video(self, path: str, audio_only: bool = False) -> bool:
        """Load a video or audio file."""
        if not os.path.exists(path):
            print(f"Video file not found: {path}")
            return False

        self._video_path = path
        self._audio_only = audio_only

        # Initialize MPV if not done yet
        if not self._init_mpv():
            print("Failed to initialize MPV player")
            self.placeholder_label.setText(
                "Video playback unavailable\n\n"
                "Please ensure MPV is installed:\n"
                "1. Download MPV from https://mpv.io/installation/\n"
                "2. Add MPV to system PATH\n"
                "3. Install: pip install python-mpv\n"
                "4. Restart the application"
            )
            return False

        if self._mpv_player:
            try:
                # Hide placeholder
                self.placeholder_label.hide()

                # Load the video
                self._mpv_player.play(path)
                self._mpv_player.pause = True

                # Wait a moment for MPV to initialize the video
                QTimer.singleShot(200, self._on_video_loaded)

                self._set_controls_enabled(True)

                if audio_only:
                    self.placeholder_label.setText("Audio Only Mode")
                    self.placeholder_label.show()

                return True
            except Exception as e:
                print(f"Error loading video: {e}")
                self.placeholder_label.setText(f"Error loading video:\n{str(e)}")
                self.placeholder_label.show()
                return False

        return False

    def _on_video_loaded(self) -> None:
        """Called after video is loaded to ensure first frame shows."""
        if self._mpv_player and not self._audio_only:
            try:
                # Seek to start to show first frame
                self._mpv_player.seek(0, 'absolute')
            except:
                pass

    def play(self) -> None:
        """Start playback."""
        if self._mpv_player and self._video_path:
            self._mpv_player.pause = False
            self._is_playing = True
            self._update_play_button()
            self.playback_state_changed.emit(True)

    def pause(self) -> None:
        """Pause playback."""
        if self._mpv_player:
            self._mpv_player.pause = True
            self._is_playing = False
            self._update_play_button()
            self.playback_state_changed.emit(False)

    def toggle_playback(self) -> None:
        """Toggle play/pause."""
        if self._is_playing:
            self.pause()
        else:
            self.play()

    def stop(self) -> None:
        """Stop playback and seek to beginning."""
        if self._mpv_player:
            self._mpv_player.pause = True
            self._mpv_player.seek(0, 'absolute')
            self._is_playing = False
            self._update_play_button()
            self.playback_state_changed.emit(False)

    def seek(self, position_ms: int) -> None:
        """Seek to position in milliseconds."""
        if self._mpv_player and self._video_path:
            self._mpv_player.seek(position_ms / 1000, 'absolute')

    def get_position(self) -> int:
        """Get current position in milliseconds."""
        return self._position_ms

    def get_duration(self) -> int:
        """Get video duration in milliseconds."""
        return self._duration_ms

    def is_playing(self) -> bool:
        """Check if video is playing."""
        return self._is_playing

    def set_volume(self, volume: int) -> None:
        """Set volume (0-100)."""
        if self._mpv_player:
            self._mpv_player.volume = volume
        self.volume_slider.setValue(volume)

    def toggle_captions(self, visible: bool) -> None:
        """Toggle caption visibility."""
        self._captions_visible = visible
        self.btn_captions.setChecked(visible)
        if not visible:
            self.caption_overlay.clear()
        else:
            self.update_captions()

    def set_project(self, project) -> None:
        """Set the project for caption display."""
        self._project = project

    def update_captions(self) -> None:
        """Update caption display based on current position."""
        if not self._captions_visible or not self._project:
            self.caption_overlay.clear()
            return

        # Find subtitle at current position
        subtitle = self._project.get_subtitle_at_time(self._position_ms)

        if subtitle:
            # Get style
            style_dict = None
            if subtitle.style_id and self._project:
                style = self._project.get_style_by_id(subtitle.style_id)
                if style:
                    style_dict = {
                        'font_family': style.font_family,
                        'font_size': style.font_size,
                        'primary_color': style.primary_color,
                        'outline_color': style.outline_color,
                        'outline_width': style.outline_width,
                        'background_color': style.background_color,
                        'background_opacity': style.background_opacity,
                    }

            self.caption_overlay.set_caption(subtitle.get_full_text(), style_dict)
        else:
            self.caption_overlay.clear()

    def _on_v_align_changed(self, text: str) -> None:
        """Handle vertical alignment change."""
        self._v_align = text.lower()
        self.caption_overlay.set_alignment(self._v_align, self._h_align)

    def _on_h_align_changed(self, text: str) -> None:
        """Handle horizontal alignment change."""
        self._h_align = text.lower()
        self.caption_overlay.set_alignment(self._v_align, self._h_align)

    def toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        if self._mpv_player:
            self._mpv_player.fullscreen = not self._mpv_player.fullscreen

    def cleanup(self) -> None:
        """Cleanup resources."""
        self._update_timer.stop()
        if self._mpv_player:
            try:
                self._mpv_player.terminate()
            except:
                pass
            self._mpv_player = None

    # Slots

    @Slot()
    def _on_slider_pressed(self) -> None:
        """Handle slider press."""
        pass  # Pause updates while dragging

    @Slot()
    def _on_slider_released(self) -> None:
        """Handle slider release."""
        if self._duration_ms > 0:
            position = int((self.seek_slider.value() / 1000) * self._duration_ms)
            self.seek(position)

    @Slot(int)
    def _on_slider_moved(self, value: int) -> None:
        """Handle slider move during drag."""
        if self._duration_ms > 0:
            position = int((value / 1000) * self._duration_ms)
            self.time_label.setText(self._format_time(position))

    @Slot(int)
    def _on_volume_changed(self, value: int) -> None:
        """Handle volume slider change."""
        if self._mpv_player:
            self._mpv_player.volume = value

    @Slot()
    def _on_captions_toggled(self) -> None:
        """Handle captions toggle."""
        self._captions_visible = self.btn_captions.isChecked()
        if self._captions_visible:
            self.update_captions()
        else:
            self.caption_overlay.clear()

    def keyPressEvent(self, event) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key_Space:
            self.toggle_playback()
        elif event.key() == Qt.Key_Left:
            # Nudge back 100ms or 1s with shift
            nudge = 1000 if event.modifiers() & Qt.ShiftModifier else 100
            self.seek(max(0, self._position_ms - nudge))
        elif event.key() == Qt.Key_Right:
            # Nudge forward 100ms or 1s with shift
            nudge = 1000 if event.modifiers() & Qt.ShiftModifier else 100
            self.seek(min(self._duration_ms, self._position_ms + nudge))
        else:
            super().keyPressEvent(event)
