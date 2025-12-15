"""Data models for MikesCaptionBuddy."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import json


class Alignment(Enum):
    """Subtitle alignment options."""
    BOTTOM_LEFT = 1
    BOTTOM_CENTER = 2
    BOTTOM_RIGHT = 3
    MIDDLE_LEFT = 4
    MIDDLE_CENTER = 5
    MIDDLE_RIGHT = 6
    TOP_LEFT = 7
    TOP_CENTER = 8
    TOP_RIGHT = 9


@dataclass
class StyleOverride:
    """Per-word style overrides."""
    color: Optional[str] = None  # Hex color e.g. "#FF0000"
    font_family: Optional[str] = None
    font_size: Optional[int] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    outline_color: Optional[str] = None
    outline_width: Optional[int] = None
    background_color: Optional[str] = None
    background_opacity: Optional[float] = None
    rotation: Optional[float] = None  # Degrees
    scale_x: Optional[float] = None
    scale_y: Optional[float] = None
    karaoke_duration: Optional[int] = None  # Centiseconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StyleOverride':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'StyleOverride':
        """Create from JSON string."""
        if not json_str:
            return cls()
        return cls.from_dict(json.loads(json_str))


@dataclass
class Word:
    """Represents a single word in a subtitle."""
    id: Optional[int] = None
    subtitle_id: Optional[int] = None
    word_index: int = 0
    text: str = ""
    start_ms: int = 0
    end_ms: int = 0
    style_override: StyleOverride = field(default_factory=StyleOverride)

    def duration_ms(self) -> int:
        """Get word duration in milliseconds."""
        return self.end_ms - self.start_ms

    def has_override(self) -> bool:
        """Check if word has any style overrides."""
        return bool(self.style_override.to_dict())


@dataclass
class Style:
    """Represents a caption style."""
    id: Optional[int] = None
    name: str = "Default"
    font_family: str = "Arial"
    font_size: int = 48
    bold: bool = False
    italic: bool = False
    underline: bool = False
    primary_color: str = "#FFFFFF"  # White
    secondary_color: str = "#FFFF00"  # Yellow (for karaoke)
    outline_color: str = "#000000"  # Black
    outline_width: int = 2
    shadow_color: str = "#000000"
    shadow_offset_x: int = 2
    shadow_offset_y: int = 2
    background_color: str = "#000000"
    background_opacity: float = 0.0  # 0 = transparent
    alignment: Alignment = Alignment.BOTTOM_CENTER

    def to_ass_style(self) -> str:
        """Convert to ASS style line."""
        # Convert hex colors to ASS format (BGR with alpha)
        def hex_to_ass(hex_color: str, alpha: int = 0) -> str:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"

        bg_alpha = int((1 - self.background_opacity) * 255)

        return (
            f"Style: {self.name},"
            f"{self.font_family},{self.font_size},"
            f"{hex_to_ass(self.primary_color)},"
            f"{hex_to_ass(self.secondary_color)},"
            f"{hex_to_ass(self.outline_color)},"
            f"{hex_to_ass(self.background_color, bg_alpha)},"
            f"{-1 if self.bold else 0},{-1 if self.italic else 0},"
            f"{-1 if self.underline else 0},0,"  # underline, strikeout
            f"100,100,0,0,"  # scaleX, scaleY, spacing, angle
            f"1,{self.outline_width},{self.shadow_offset_x},"  # border style, outline, shadow
            f"{self.alignment.value},10,10,10,1"  # alignment, margins, encoding
        )


@dataclass
class Subtitle:
    """Represents a subtitle entry."""
    id: Optional[int] = None
    start_ms: int = 0
    end_ms: int = 0
    text: str = ""
    style_id: Optional[int] = None
    position_x: float = 0.5  # 0-1, center = 0.5
    position_y: float = 0.9  # 0-1, bottom = 0.9
    words: List[Word] = field(default_factory=list)

    def duration_ms(self) -> int:
        """Get subtitle duration in milliseconds."""
        return self.end_ms - self.start_ms

    def split_into_words(self) -> None:
        """Split text into individual words with timing."""
        if not self.text.strip():
            self.words = []
            return

        word_texts = self.text.split()
        if not word_texts:
            self.words = []
            return

        duration = self.duration_ms()
        word_duration = duration // len(word_texts)

        self.words = []
        current_time = self.start_ms

        for i, word_text in enumerate(word_texts):
            word = Word(
                subtitle_id=self.id,
                word_index=i,
                text=word_text,
                start_ms=current_time,
                end_ms=current_time + word_duration if i < len(word_texts) - 1 else self.end_ms
            )
            self.words.append(word)
            current_time += word_duration

    def get_full_text(self) -> str:
        """Get full text from words or text field."""
        if self.words:
            return " ".join(w.text for w in self.words)
        return self.text

    def to_srt_entry(self, index: int) -> str:
        """Convert to SRT format entry."""
        def ms_to_srt_time(ms: int) -> str:
            hours = ms // 3600000
            minutes = (ms % 3600000) // 60000
            seconds = (ms % 60000) // 1000
            millis = ms % 1000
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

        return (
            f"{index}\n"
            f"{ms_to_srt_time(self.start_ms)} --> {ms_to_srt_time(self.end_ms)}\n"
            f"{self.get_full_text()}\n"
        )


@dataclass
class VideoInfo:
    """Video file metadata."""
    filename: str = ""
    duration_ms: int = 0
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    has_audio: bool = True


@dataclass
class Project:
    """Represents a caption project."""
    id: Optional[int] = None
    name: str = "Untitled Project"
    video_path: Optional[str] = None
    video_info: VideoInfo = field(default_factory=VideoInfo)
    subtitles: List[Subtitle] = field(default_factory=list)
    styles: List[Style] = field(default_factory=list)
    default_style_id: Optional[int] = None
    modified: bool = False

    def __post_init__(self):
        """Initialize default style if none exists."""
        if not self.styles:
            default_style = Style(id=1, name="Default")
            self.styles.append(default_style)
            self.default_style_id = 1

    def get_style_by_id(self, style_id: int) -> Optional[Style]:
        """Get style by ID."""
        for style in self.styles:
            if style.id == style_id:
                return style
        return None

    def get_style_by_name(self, name: str) -> Optional[Style]:
        """Get style by name."""
        for style in self.styles:
            if style.name == name:
                return style
        return None

    def get_default_style(self) -> Style:
        """Get the default style."""
        if self.default_style_id:
            style = self.get_style_by_id(self.default_style_id)
            if style:
                return style
        if self.styles:
            return self.styles[0]
        return Style()

    def add_subtitle(self, subtitle: Subtitle) -> None:
        """Add a subtitle to the project."""
        if subtitle.id is None:
            subtitle.id = max((s.id or 0 for s in self.subtitles), default=0) + 1
        if subtitle.style_id is None:
            subtitle.style_id = self.default_style_id
        self.subtitles.append(subtitle)
        self.subtitles.sort(key=lambda s: s.start_ms)
        self.modified = True

    def remove_subtitle(self, subtitle_id: int) -> bool:
        """Remove a subtitle by ID."""
        for i, sub in enumerate(self.subtitles):
            if sub.id == subtitle_id:
                del self.subtitles[i]
                self.modified = True
                return True
        return False

    def get_subtitle_at_time(self, time_ms: int) -> Optional[Subtitle]:
        """Get subtitle at a specific time."""
        for sub in self.subtitles:
            if sub.start_ms <= time_ms <= sub.end_ms:
                return sub
        return None

    def export_to_srt(self) -> str:
        """Export subtitles to SRT format."""
        lines = []
        for i, sub in enumerate(self.subtitles, 1):
            lines.append(sub.to_srt_entry(i))
        return "\n".join(lines)
