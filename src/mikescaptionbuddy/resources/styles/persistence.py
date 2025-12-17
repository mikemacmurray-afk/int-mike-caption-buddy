"""Persistent style presets storage."""

import json
import os
from pathlib import Path
from typing import List, Optional

from ...core.models import Style, Alignment


def get_styles_dir() -> Path:
    """Get the styles storage directory path."""
    if os.name == 'nt':  # Windows
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:  # Linux/Mac
        base = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    return Path(base) / 'MikesCaptionBuddy' / 'styles'


def get_styles_path() -> Path:
    """Get the styles file path."""
    return get_styles_dir() / 'project_styles.json'


def style_to_dict(style: Style) -> dict:
    """Convert a Style object to a dictionary."""
    return {
        'id': style.id,
        'name': style.name,
        'font_family': style.font_family,
        'font_size': style.font_size,
        'bold': style.bold,
        'italic': style.italic,
        'underline': style.underline,
        'primary_color': style.primary_color,
        'secondary_color': style.secondary_color,
        'outline_color': style.outline_color,
        'outline_width': style.outline_width,
        'shadow_color': style.shadow_color,
        'shadow_offset_x': style.shadow_offset_x,
        'shadow_offset_y': style.shadow_offset_y,
        'background_color': style.background_color,
        'background_opacity': style.background_opacity,
        'alignment': style.alignment.value,
        'split_to_words': style.split_to_words,
        'word_by_word': style.word_by_word,
        'karaoke_style': style.karaoke_style,
        'karaoke_color': style.karaoke_color,
        'rotation': style.rotation,
    }


def dict_to_style(data: dict) -> Style:
    """Convert a dictionary to a Style object."""
    alignment_value = data.get('alignment', 2)
    if isinstance(alignment_value, int):
        alignment = Alignment(alignment_value)
    else:
        alignment = Alignment.BOTTOM_CENTER

    return Style(
        id=data.get('id'),
        name=data.get('name', 'Unnamed'),
        font_family=data.get('font_family', 'Arial'),
        font_size=data.get('font_size', 48),
        bold=data.get('bold', False),
        italic=data.get('italic', False),
        underline=data.get('underline', False),
        primary_color=data.get('primary_color', '#FFFFFF'),
        secondary_color=data.get('secondary_color', '#FFFF00'),
        outline_color=data.get('outline_color', '#000000'),
        outline_width=data.get('outline_width', 2),
        shadow_color=data.get('shadow_color', '#000000'),
        shadow_offset_x=data.get('shadow_offset_x', 2),
        shadow_offset_y=data.get('shadow_offset_y', 2),
        background_color=data.get('background_color', '#000000'),
        background_opacity=data.get('background_opacity', 0.0),
        alignment=alignment,
        split_to_words=data.get('split_to_words', False),
        word_by_word=data.get('word_by_word', False),
        karaoke_style=data.get('karaoke_style', 'none'),
        karaoke_color=data.get('karaoke_color', '#FFFF00'),
        rotation=data.get('rotation', 0.0),
    )


def save_styles(styles: List[Style]) -> None:
    """Save styles to persistent storage."""
    styles_dir = get_styles_dir()
    styles_dir.mkdir(parents=True, exist_ok=True)

    styles_path = get_styles_path()
    data = {
        'version': 1,
        'styles': [style_to_dict(style) for style in styles]
    }

    with open(styles_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def load_styles() -> Optional[List[Style]]:
    """Load styles from persistent storage. Returns None if no saved styles exist."""
    styles_path = get_styles_path()

    if not styles_path.exists():
        return None

    try:
        with open(styles_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        styles = []
        for style_data in data.get('styles', []):
            styles.append(dict_to_style(style_data))

        if styles:
            return styles

    except (json.JSONDecodeError, TypeError, KeyError):
        pass  # Return None if loading fails

    return None


def get_or_create_styles() -> List[Style]:
    """Get saved styles or create default styles if none exist."""
    styles = load_styles()
    if styles:
        return styles

    # Return default styles from presets
    from .presets import get_preset_styles
    return get_preset_styles()
