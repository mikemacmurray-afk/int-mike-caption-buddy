"""Style presets for MikesCaptionBuddy."""

from .presets import get_preset_styles, apply_preset_styles
from .persistence import (
    save_styles,
    load_styles,
    get_or_create_styles,
    get_styles_path
)

__all__ = [
    'get_preset_styles',
    'apply_preset_styles',
    'save_styles',
    'load_styles',
    'get_or_create_styles',
    'get_styles_path'
]
