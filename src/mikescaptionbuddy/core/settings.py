"""Application settings management."""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class StylePreset:
    """A saved style preset."""
    slot: int = 0  # 1-10
    name: str = ""
    font_family: str = "Arial"
    font_size: int = 48
    bold: bool = False
    italic: bool = False
    underline: bool = False
    primary_color: str = "#FFFFFF"
    secondary_color: str = "#FFFF00"
    outline_color: str = "#000000"
    outline_width: int = 2
    shadow_color: str = "#000000"
    shadow_offset_x: int = 2
    shadow_offset_y: int = 2
    background_color: str = "#000000"
    background_opacity: float = 0.0
    alignment: int = 2  # BOTTOM_CENTER

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'StylePreset':
        """Create from dictionary."""
        valid_fields = {k for k in cls.__dataclass_fields__}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


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

    # Style presets (up to 10 saved styles)
    style_presets: List[dict] = field(default_factory=list)

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

    def get_style_presets(self) -> List['StylePreset']:
        """Get all saved style presets."""
        presets = []
        for data in self.style_presets:
            presets.append(StylePreset.from_dict(data))
        return presets

    def get_style_preset(self, slot: int) -> Optional['StylePreset']:
        """Get a style preset by slot number (1-10)."""
        for data in self.style_presets:
            if data.get('slot') == slot:
                return StylePreset.from_dict(data)
        return None

    def save_style_preset(self, preset: 'StylePreset') -> None:
        """Save a style preset to a slot (1-10). Max 10 presets."""
        if preset.slot < 1 or preset.slot > 10:
            raise ValueError("Preset slot must be between 1 and 10")

        # Remove existing preset in this slot
        self.style_presets = [p for p in self.style_presets if p.get('slot') != preset.slot]

        # Add new preset
        self.style_presets.append(preset.to_dict())

        # Sort by slot number
        self.style_presets.sort(key=lambda p: p.get('slot', 0))

        self.save()

    def delete_style_preset(self, slot: int) -> None:
        """Delete a style preset from a slot."""
        self.style_presets = [p for p in self.style_presets if p.get('slot') != slot]
        self.save()

    def get_next_available_preset_slot(self) -> int:
        """Get the next available preset slot (1-10), or 0 if all are used."""
        used_slots = {p.get('slot') for p in self.style_presets}
        for slot in range(1, 11):
            if slot not in used_slots:
                return slot
        return 0
