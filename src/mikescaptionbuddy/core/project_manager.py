"""Project management with SQLite storage."""

import sqlite3
import os
import json
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

from PySide6.QtCore import QObject, Signal, QTimer

from .models import Project, Subtitle, Word, Style, StyleOverride, VideoInfo, Alignment
from ..resources.styles import get_or_create_styles


class ProjectManager(QObject):
    """Manages project persistence and auto-save."""

    # Signals
    project_loaded = Signal(object)  # Project
    project_saved = Signal(str)  # path
    project_modified = Signal()
    auto_save_triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_project: Optional[Project] = None
        self._current_path: Optional[str] = None
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._on_auto_save)
        self._auto_save_interval = 120000  # 2 minutes in ms

    @property
    def current_project(self) -> Optional[Project]:
        """Get the current project."""
        return self._current_project

    @property
    def current_path(self) -> Optional[str]:
        """Get the current project file path."""
        return self._current_path

    def set_auto_save_interval(self, seconds: int) -> None:
        """Set auto-save interval in seconds."""
        self._auto_save_interval = seconds * 1000
        if self._auto_save_timer.isActive():
            self._auto_save_timer.start(self._auto_save_interval)

    def start_auto_save(self) -> None:
        """Start auto-save timer."""
        if self._auto_save_interval > 0:
            self._auto_save_timer.start(self._auto_save_interval)

    def stop_auto_save(self) -> None:
        """Stop auto-save timer."""
        self._auto_save_timer.stop()

    def new_project(self, name: str = "Untitled Project") -> Project:
        """Create a new project with saved or default styles."""
        self.stop_auto_save()

        # Create project with saved styles (or default presets if none saved)
        saved_styles = get_or_create_styles()
        self._current_project = Project(name=name, styles=saved_styles)

        # Set default style to first style
        if saved_styles:
            self._current_project.default_style_id = saved_styles[0].id

        self._current_path = None
        self.project_loaded.emit(self._current_project)
        return self._current_project

    def load_project(self, path: str) -> Optional[Project]:
        """Load a project from a .captionstudio file."""
        if not os.path.exists(path):
            return None

        try:
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Load project metadata
            cursor.execute("SELECT * FROM project LIMIT 1")
            proj_row = cursor.fetchone()
            if not proj_row:
                conn.close()
                return None

            project = Project(
                id=proj_row['id'],
                name=proj_row['name']
            )

            # Load video info
            cursor.execute("SELECT * FROM video LIMIT 1")
            video_row = cursor.fetchone()
            if video_row:
                project.video_info = VideoInfo(
                    filename=video_row['filename'],
                    duration_ms=video_row['duration_ms'],
                    width=video_row['width'],
                    height=video_row['height'],
                    fps=video_row['fps']
                )
                # Note: video data blob is loaded separately when needed

            # Load styles
            cursor.execute("SELECT * FROM styles")
            for style_row in cursor.fetchall():
                style = Style(
                    id=style_row['id'],
                    name=style_row['name'],
                    font_family=style_row['font_family'],
                    font_size=style_row['font_size'],
                    bold=bool(style_row['bold']),
                    italic=bool(style_row['italic']),
                    underline=bool(style_row['underline']),
                    primary_color=style_row['primary_color'],
                    secondary_color=style_row['secondary_color'],
                    outline_color=style_row['outline_color'],
                    outline_width=style_row['outline_width'],
                    shadow_color=style_row['shadow_color'],
                    shadow_offset_x=style_row['shadow_offset_x'],
                    shadow_offset_y=style_row['shadow_offset_y'],
                    background_color=style_row['background_color'],
                    background_opacity=style_row['background_opacity'],
                    alignment=Alignment(int(style_row['alignment']))
                )
                project.styles.append(style)

            # Load default style id from settings
            cursor.execute("SELECT value FROM settings WHERE key = 'default_style_id'")
            default_row = cursor.fetchone()
            if default_row:
                project.default_style_id = int(default_row['value'])

            # Load subtitles
            cursor.execute("SELECT * FROM subtitles ORDER BY start_ms")
            for sub_row in cursor.fetchall():
                subtitle = Subtitle(
                    id=sub_row['id'],
                    start_ms=sub_row['start_ms'],
                    end_ms=sub_row['end_ms'],
                    text=sub_row['text'],
                    style_id=sub_row['style_id'],
                    position_x=sub_row['position_x'],
                    position_y=sub_row['position_y']
                )

                # Load words for this subtitle
                cursor.execute(
                    "SELECT * FROM words WHERE subtitle_id = ? ORDER BY word_index",
                    (subtitle.id,)
                )
                for word_row in cursor.fetchall():
                    word = Word(
                        id=word_row['id'],
                        subtitle_id=word_row['subtitle_id'],
                        word_index=word_row['word_index'],
                        text=word_row['text'],
                        start_ms=word_row['start_ms'],
                        end_ms=word_row['end_ms'],
                        style_override=StyleOverride.from_json(word_row['style_override'] or '{}')
                    )
                    subtitle.words.append(word)

                project.subtitles.append(subtitle)

            conn.close()

            self._current_project = project
            self._current_path = path
            project.modified = False
            self.project_loaded.emit(project)
            self.start_auto_save()

            return project

        except sqlite3.Error as e:
            print(f"Error loading project: {e}")
            return None

    def save_project(self, path: Optional[str] = None) -> bool:
        """Save the current project to a .captionstudio file."""
        if not self._current_project:
            return False

        path = path or self._current_path
        if not path:
            return False

        try:
            # Ensure .captionstudio extension
            if not path.endswith('.captionstudio'):
                path += '.captionstudio'

            conn = sqlite3.connect(path)
            cursor = conn.cursor()

            # Create tables
            self._create_tables(cursor)

            # Clear existing data
            cursor.execute("DELETE FROM words")
            cursor.execute("DELETE FROM subtitles")
            cursor.execute("DELETE FROM styles")
            cursor.execute("DELETE FROM video")
            cursor.execute("DELETE FROM project")
            cursor.execute("DELETE FROM settings")

            # Save project metadata
            cursor.execute(
                "INSERT INTO project (id, name, created_at, modified_at, version) VALUES (?, ?, ?, ?, ?)",
                (1, self._current_project.name, datetime.now().isoformat(),
                 datetime.now().isoformat(), "1.0")
            )

            # Save video info (without blob for now - video path reference)
            vi = self._current_project.video_info
            cursor.execute(
                "INSERT INTO video (id, filename, duration_ms, width, height, fps) VALUES (?, ?, ?, ?, ?, ?)",
                (1, vi.filename, vi.duration_ms, vi.width, vi.height, vi.fps)
            )

            # Save styles
            for style in self._current_project.styles:
                cursor.execute(
                    """INSERT INTO styles (id, name, font_family, font_size, bold, italic, underline,
                       primary_color, secondary_color, outline_color, outline_width,
                       shadow_color, shadow_offset_x, shadow_offset_y, background_color,
                       background_opacity, alignment) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (style.id, style.name, style.font_family, style.font_size,
                     int(style.bold), int(style.italic), int(style.underline),
                     style.primary_color, style.secondary_color, style.outline_color,
                     style.outline_width, style.shadow_color, style.shadow_offset_x,
                     style.shadow_offset_y, style.background_color, style.background_opacity,
                     style.alignment.value)
                )

            # Save default style setting
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                ('default_style_id', str(self._current_project.default_style_id or 1))
            )

            # Save video path setting
            if self._current_project.video_path:
                cursor.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?)",
                    ('video_path', self._current_project.video_path)
                )

            # Save subtitles and words
            for subtitle in self._current_project.subtitles:
                cursor.execute(
                    """INSERT INTO subtitles (id, start_ms, end_ms, text, style_id, position_x, position_y)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (subtitle.id, subtitle.start_ms, subtitle.end_ms, subtitle.text,
                     subtitle.style_id, subtitle.position_x, subtitle.position_y)
                )

                for word in subtitle.words:
                    cursor.execute(
                        """INSERT INTO words (id, subtitle_id, word_index, text, start_ms, end_ms, style_override)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (word.id, subtitle.id, word.word_index, word.text,
                         word.start_ms, word.end_ms, word.style_override.to_json())
                    )

            conn.commit()
            conn.close()

            self._current_path = path
            self._current_project.modified = False
            self.project_saved.emit(path)
            return True

        except sqlite3.Error as e:
            print(f"Error saving project: {e}")
            return False

    def _create_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create database tables."""
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS project (
                id INTEGER PRIMARY KEY,
                name TEXT,
                created_at TEXT,
                modified_at TEXT,
                version TEXT
            );

            CREATE TABLE IF NOT EXISTS video (
                id INTEGER PRIMARY KEY,
                filename TEXT,
                data BLOB,
                duration_ms INTEGER,
                width INTEGER,
                height INTEGER,
                fps REAL
            );

            CREATE TABLE IF NOT EXISTS subtitles (
                id INTEGER PRIMARY KEY,
                start_ms INTEGER,
                end_ms INTEGER,
                text TEXT,
                style_id INTEGER,
                position_x REAL,
                position_y REAL
            );

            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY,
                subtitle_id INTEGER,
                word_index INTEGER,
                text TEXT,
                start_ms INTEGER,
                end_ms INTEGER,
                style_override TEXT
            );

            CREATE TABLE IF NOT EXISTS styles (
                id INTEGER PRIMARY KEY,
                name TEXT,
                font_family TEXT,
                font_size INTEGER,
                bold INTEGER,
                italic INTEGER,
                underline INTEGER,
                primary_color TEXT,
                secondary_color TEXT,
                outline_color TEXT,
                outline_width INTEGER,
                shadow_color TEXT,
                shadow_offset_x INTEGER,
                shadow_offset_y INTEGER,
                background_color TEXT,
                background_opacity REAL,
                alignment INTEGER
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)

    def _on_auto_save(self) -> None:
        """Handle auto-save timer."""
        if self._current_project and self._current_project.modified and self._current_path:
            self.save_project()
            self.auto_save_triggered.emit()

    def mark_modified(self) -> None:
        """Mark the current project as modified."""
        if self._current_project:
            self._current_project.modified = True
            self.project_modified.emit()

    def is_modified(self) -> bool:
        """Check if the current project is modified."""
        return self._current_project.modified if self._current_project else False

    def close_project(self) -> None:
        """Close the current project."""
        self.stop_auto_save()
        self._current_project = None
        self._current_path = None

    def get_video_data(self, path: str) -> Optional[bytes]:
        """Load embedded video data from project file."""
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM video WHERE id = 1")
            row = cursor.fetchone()
            conn.close()
            return row[0] if row and row[0] else None
        except sqlite3.Error:
            return None

    def embed_video(self, video_path: str) -> bool:
        """Embed video file into the current project file."""
        if not self._current_path or not os.path.exists(video_path):
            return False

        try:
            with open(video_path, 'rb') as f:
                video_data = f.read()

            conn = sqlite3.connect(self._current_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE video SET data = ? WHERE id = 1", (video_data,))
            conn.commit()
            conn.close()
            return True

        except (IOError, sqlite3.Error) as e:
            print(f"Error embedding video: {e}")
            return False
