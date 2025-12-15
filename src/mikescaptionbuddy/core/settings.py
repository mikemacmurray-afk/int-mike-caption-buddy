"""Application settings management."""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class Settings:
    """Application settings."""

    # General
    auto_save_interval_seconds: int = 120  # 2 minutes
    show_startup_dialog: bool = True
    recent_files_limit: int = 10
    recent_files: List[str] = field(default_factory=list)

    # Transcription
    default_whisper_model: str = "medium"
    whisper_language: str = "en"

    # Export
    default_export_directory: str = ""
    default_video_resolution: str = "1080p"
    default_video_codec: str = "h264"
    default_quality_preset: str = "balanced"

    # Appearance
    theme: str = "system"  # "light", "dark", "system"
    editor_font_size: int = 12

    # Window state
    window_width: int = 1400
    window_height: int = 900
    window_maximized: bool = False

    # Internal
    _settings_path: Optional[str] = field(default=None, repr=False)

    @classmethod
    def get_settings_dir(cls) -> Path:
        """Get the settings directory path."""
        if os.name == 'nt':  # Windows
            base = os.environ.get('APPDATA', os.path.expanduser('~'))
        else:  # Linux/Mac
            base = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        return Path(base) / 'MikesCaptionBuddy'

    @classmethod
    def get_settings_path(cls) -> Path:
        """Get the settings file path."""
        return cls.get_settings_dir() / 'settings.json'

    @classmethod
    def load(cls) -> 'Settings':
        """Load settings from file."""
        settings_path = cls.get_settings_path()

        if settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Filter out internal fields
                valid_fields = {k for k in cls.__dataclass_fields__ if not k.startswith('_')}
                filtered_data = {k: v for k, v in data.items() if k in valid_fields}
                settings = cls(**filtered_data)
                settings._settings_path = str(settings_path)
                return settings
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"Warning: Could not load settings: {e}")

        # Return default settings
        settings = cls()
        settings._settings_path = str(settings_path)
        return settings

    def save(self) -> None:
        """Save settings to file."""
        settings_dir = self.get_settings_dir()
        settings_dir.mkdir(parents=True, exist_ok=True)

        settings_path = self.get_settings_path()
        data = asdict(self)
        # Remove internal fields
        data = {k: v for k, v in data.items() if not k.startswith('_')}

        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def add_recent_file(self, file_path: str) -> None:
        """Add a file to recent files list."""
        # Remove if already exists
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)

        # Add to front
        self.recent_files.insert(0, file_path)

        # Trim to limit
        self.recent_files = self.recent_files[:self.recent_files_limit]
        self.save()

    def remove_recent_file(self, file_path: str) -> None:
        """Remove a file from recent files list."""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
            self.save()

    def clear_recent_files(self) -> None:
        """Clear all recent files."""
        self.recent_files = []
        self.save()

    def get_export_directory(self) -> str:
        """Get the export directory, defaulting to user's Videos folder."""
        if self.default_export_directory and os.path.isdir(self.default_export_directory):
            return self.default_export_directory

        # Default to Videos folder
        if os.name == 'nt':
            videos = os.path.join(os.path.expanduser('~'), 'Videos')
        else:
            videos = os.path.join(os.path.expanduser('~'), 'Videos')

        if os.path.isdir(videos):
            return videos

        return os.path.expanduser('~')
