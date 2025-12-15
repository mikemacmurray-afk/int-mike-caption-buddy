"""Video preview panel with playback controls."""

import os
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QPalette


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

        self._setup_ui()
        self._setup_mpv()
        self._setup_timer()

    def _setup_ui(self) -> None:
        """Setup the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Video container
        self.video_container = QFrame()
        self.video_container.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.video_container.setMinimumSize(400, 300)
        self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Set black background for video area
        palette = self.video_container.palette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        self.video_container.setPalette(palette)
        self.video_container.setAutoFillBackground(True)

        # Placeholder label (shown when no video)
        video_layout = QVBoxLayout(self.video_container)
        self.placeholder_label = QLabel("No video loaded\n\nFile → Open Video to begin")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #888; font-size: 14px;")
        video_layout.addWidget(self.placeholder_label)

        layout.addWidget(self.video_container, 1)

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

    def _setup_mpv(self) -> None:
        """Setup MPV player."""
        try:
            import mpv

            # Create player with embedding
            self._mpv_player = mpv.MPV(
                wid=str(int(self.video_container.winId())),
                vo='gpu',
                hwdec='auto',
                keep_open='yes',
                idle='yes',
                osc='no',
                input_default_bindings='no',
                input_vo_keyboard='no',
            )

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

            self.placeholder_label.hide()

        except ImportError:
            print("Warning: python-mpv not installed. Video playback unavailable.")
            self._mpv_player = None
        except Exception as e:
            print(f"Warning: Could not initialize MPV: {e}")
            self._mpv_player = None

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
            return False

        self._video_path = path
        self._audio_only = audio_only

        if self._mpv_player:
            try:
                self._mpv_player.play(path)
                self._mpv_player.pause = True
                self._set_controls_enabled(True)

                if audio_only:
                    self.placeholder_label.setText("Audio Only Mode")
                    self.placeholder_label.show()

                return True
            except Exception as e:
                print(f"Error loading video: {e}")
                return False

        return False

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
        # TODO: Actually toggle ASS subtitle visibility in mpv

    def update_captions(self) -> None:
        """Update caption display."""
        # TODO: Refresh subtitle display
        pass

    def toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        if self._mpv_player:
            self._mpv_player.fullscreen = not self._mpv_player.fullscreen

    def cleanup(self) -> None:
        """Cleanup resources."""
        self._update_timer.stop()
        if self._mpv_player:
            self._mpv_player.terminate()
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
