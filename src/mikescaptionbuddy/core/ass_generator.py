"""ASS (Advanced SubStation Alpha) subtitle generator."""

import tempfile
import os
from typing import Optional

from .models import Project, Style, Subtitle, Alignment


class ASSGenerator:
    """Generates ASS subtitle files from project data."""

    def __init__(self, video_width: int = 1920, video_height: int = 1080):
        self._video_width = video_width
        self._video_height = video_height
        self._temp_dir = tempfile.gettempdir()

    def set_resolution(self, width: int, height: int) -> None:
        """Set the video resolution for ASS script."""
        self._video_width = width
        self._video_height = height

    def _hex_to_ass_color(self, hex_color: str, alpha: int = 0) -> str:
        """Convert hex color (#RRGGBB) to ASS format (&HAABBGGRR)."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        else:
            r, g, b = 255, 255, 255
        return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"

    def _ms_to_ass_time(self, ms: int) -> str:
        """Convert milliseconds to ASS time format (H:MM:SS.CC)."""
        total_seconds = ms / 1000
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        centiseconds = int((total_seconds * 100) % 100)
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    def _generate_style_line(self, style: Style) -> str:
        """Generate ASS style line from Style object."""
        # Calculate background alpha (0 = opaque, 255 = transparent)
        bg_alpha = int((1 - style.background_opacity) * 255)

        # Bold/Italic flags: -1 = true, 0 = false
        bold = -1 if style.bold else 0
        italic = -1 if style.italic else 0
        underline = -1 if style.underline else 0

        # Build style line
        # Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,
        #         Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle,
        #         BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        return (
            f"Style: {style.name},{style.font_family},{style.font_size},"
            f"{self._hex_to_ass_color(style.primary_color)},"
            f"{self._hex_to_ass_color(style.secondary_color)},"
            f"{self._hex_to_ass_color(style.outline_color)},"
            f"{self._hex_to_ass_color(style.background_color, bg_alpha)},"
            f"{bold},{italic},{underline},0,"  # bold, italic, underline, strikeout
            f"100,100,0,{style.rotation},"  # scaleX, scaleY, spacing, angle
            f"1,{style.outline_width},{max(style.shadow_offset_x, style.shadow_offset_y)},"  # borderstyle, outline, shadow
            f"{style.alignment.value},10,10,10,1"  # alignment, marginL, marginR, marginV, encoding
        )

    def _generate_dialogue_line(self, subtitle: Subtitle, style_name: str) -> str:
        """Generate ASS dialogue line from Subtitle object."""
        start = self._ms_to_ass_time(subtitle.start_ms)
        end = self._ms_to_ass_time(subtitle.end_ms)
        text = subtitle.get_full_text()

        # Handle word-level styling with ASS override tags
        if subtitle.words:
            styled_text = self._apply_word_overrides(subtitle)
        else:
            styled_text = text

        # Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        return f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{styled_text}"

    def _apply_word_overrides(self, subtitle: Subtitle) -> str:
        """Apply word-level style overrides using ASS override tags."""
        parts = []

        for word in subtitle.words:
            override = word.style_override
            tags = []

            # Check for style overrides
            if override.color:
                tags.append(f"\\c{self._hex_to_ass_color(override.color)}")
            if override.font_family:
                tags.append(f"\\fn{override.font_family}")
            if override.font_size:
                tags.append(f"\\fs{override.font_size}")
            if override.bold is not None:
                tags.append(f"\\b{1 if override.bold else 0}")
            if override.italic is not None:
                tags.append(f"\\i{1 if override.italic else 0}")
            if override.underline is not None:
                tags.append(f"\\u{1 if override.underline else 0}")
            if override.outline_color:
                tags.append(f"\\3c{self._hex_to_ass_color(override.outline_color)}")
            if override.outline_width:
                tags.append(f"\\bord{override.outline_width}")
            if override.rotation:
                tags.append(f"\\frz{override.rotation}")
            if override.karaoke_duration:
                # Karaoke effect: \k = fill, \kf = fill smooth, \ko = outline
                tags.append(f"\\k{override.karaoke_duration}")

            if tags:
                # Apply tags and then reset after word
                parts.append(f"{{{''.join(tags)}}}{word.text}{{\\r}}")
            else:
                parts.append(word.text)

        return " ".join(parts)

    def generate_ass(self, project: Project) -> str:
        """Generate complete ASS file content from project."""
        lines = []

        # Script Info section
        lines.append("[Script Info]")
        lines.append(f"Title: {project.name}")
        lines.append("ScriptType: v4.00+")
        lines.append(f"PlayResX: {self._video_width}")
        lines.append(f"PlayResY: {self._video_height}")
        lines.append("WrapStyle: 0")
        lines.append("ScaledBorderAndShadow: yes")
        lines.append("")

        # V4+ Styles section
        lines.append("[V4+ Styles]")
        lines.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                    "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                    "Alignment, MarginL, MarginR, MarginV, Encoding")

        # Add all project styles
        for style in project.styles:
            lines.append(self._generate_style_line(style))

        lines.append("")

        # Events section
        lines.append("[Events]")
        lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

        # Add all subtitles with their assigned styles
        for subtitle in project.subtitles:
            # Get style for this subtitle
            style = None
            style_name = "Default"
            if subtitle.style_id:
                style = project.get_style_by_id(subtitle.style_id)
                if style:
                    style_name = style.name

            # Generate dialogue lines based on style options
            dialogue_lines = self._generate_dialogue_lines(subtitle, style, style_name)
            lines.extend(dialogue_lines)

        return "\n".join(lines)

    def _generate_dialogue_lines(self, subtitle: Subtitle, style: Optional[Style], style_name: str) -> list:
        """Generate dialogue lines for a subtitle, handling word-by-word and karaoke options."""
        lines = []

        # Check style options
        word_by_word = style.word_by_word if style else False
        split_to_words = style.split_to_words if style else False
        karaoke_style = style.karaoke_style if style else "none"

        # Ensure we have words if split_to_words is enabled
        if (split_to_words or word_by_word or karaoke_style != "none") and not subtitle.words:
            subtitle.split_into_words()

        if word_by_word and subtitle.words:
            # Word-by-word display: each word is a separate dialogue line
            for word in subtitle.words:
                start = self._ms_to_ass_time(word.start_ms)
                end = self._ms_to_ass_time(word.end_ms)
                text = word.text

                # Apply word-level style overrides if any
                if word.has_override():
                    text = self._apply_single_word_override(word)

                line = f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}"
                lines.append(line)

        elif karaoke_style != "none" and subtitle.words:
            # Karaoke display: all words in one line with karaoke timing tags
            start = self._ms_to_ass_time(subtitle.start_ms)
            end = self._ms_to_ass_time(subtitle.end_ms)
            text = self._apply_karaoke_effect(subtitle, style)
            line = f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}"
            lines.append(line)

        else:
            # Standard display
            lines.append(self._generate_dialogue_line(subtitle, style_name))

        return lines

    def _apply_karaoke_effect(self, subtitle: Subtitle, style: Optional[Style]) -> str:
        """Apply karaoke timing effects to subtitle words.

        All karaoke modes now highlight the CURRENT word in karaoke color.
        - highlight: instant color change, stays highlighted after spoken
        - fill: gradual color change, stays highlighted after spoken
        - outline: affects outline color
        - wbw: only current word highlighted, others in primary color
        """
        if not subtitle.words:
            return subtitle.get_full_text()

        karaoke_style = style.karaoke_style if style else "none"
        karaoke_color = style.karaoke_color if style else "#FFFF00"
        primary_color = style.primary_color if style else "#FFFFFF"

        # Convert colors to ASS format
        karaoke_ass = self._hex_to_ass_color(karaoke_color)
        primary_ass = self._hex_to_ass_color(primary_color)

        subtitle_start = subtitle.start_ms
        parts = []

        for word in subtitle.words:
            # Calculate timing relative to subtitle start (in milliseconds)
            word_start_rel = word.start_ms - subtitle_start
            word_end_rel = word.end_ms - subtitle_start

            if karaoke_style == "wbw":
                # WBW: Only current word highlighted, returns to primary after
                if word_start_rel > 0:
                    tags = (
                        f"\\c{primary_ass}"
                        f"\\t({word_start_rel},{word_start_rel},\\c{karaoke_ass})"
                        f"\\t({word_end_rel},{word_end_rel},\\c{primary_ass})"
                    )
                else:
                    tags = (
                        f"\\c{karaoke_ass}"
                        f"\\t({word_end_rel},{word_end_rel},\\c{primary_ass})"
                    )

            elif karaoke_style == "highlight":
                # Highlight: Instant change to karaoke color, stays highlighted
                if word_start_rel > 0:
                    tags = (
                        f"\\c{primary_ass}"
                        f"\\t({word_start_rel},{word_start_rel},\\c{karaoke_ass})"
                    )
                else:
                    # First word starts highlighted
                    tags = f"\\c{karaoke_ass}"

            elif karaoke_style == "fill":
                # Fill: Gradual fill to karaoke color over word duration, stays highlighted
                if word_start_rel > 0:
                    tags = (
                        f"\\c{primary_ass}"
                        f"\\t({word_start_rel},{word_end_rel},\\c{karaoke_ass})"
                    )
                else:
                    # First word fills from start
                    tags = (
                        f"\\c{primary_ass}"
                        f"\\t(0,{word_end_rel},\\c{karaoke_ass})"
                    )

            elif karaoke_style == "outline":
                # Outline: Change outline color instead of primary
                if word_start_rel > 0:
                    tags = (
                        f"\\3c{self._hex_to_ass_color(style.outline_color) if style else primary_ass}"
                        f"\\t({word_start_rel},{word_start_rel},\\3c{karaoke_ass})"
                    )
                else:
                    tags = f"\\3c{karaoke_ass}"

            else:
                # Default: no karaoke effect
                tags = ""

            if tags:
                parts.append(f"{{{tags}}}{word.text}")
            else:
                parts.append(word.text)

        return " ".join(parts)

    def _apply_single_word_override(self, word) -> str:
        """Apply style override to a single word."""
        override = word.style_override
        tags = []

        if override.color:
            tags.append(f"\\c{self._hex_to_ass_color(override.color)}")
        if override.font_family:
            tags.append(f"\\fn{override.font_family}")
        if override.font_size:
            tags.append(f"\\fs{override.font_size}")
        if override.bold is not None:
            tags.append(f"\\b{1 if override.bold else 0}")
        if override.italic is not None:
            tags.append(f"\\i{1 if override.italic else 0}")
        if override.underline is not None:
            tags.append(f"\\u{1 if override.underline else 0}")
        if override.outline_color:
            tags.append(f"\\3c{self._hex_to_ass_color(override.outline_color)}")
        if override.outline_width:
            tags.append(f"\\bord{override.outline_width}")
        if override.rotation:
            tags.append(f"\\frz{override.rotation}")

        if tags:
            return f"{{{''.join(tags)}}}{word.text}"
        return word.text

    def save_temp_ass(self, project: Project) -> str:
        """Save ASS content to a temporary file and return the path."""
        content = self.generate_ass(project)

        # Create temp file with .ass extension
        temp_path = os.path.join(self._temp_dir, "mikescaptionbuddy_preview.ass")

        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return temp_path

    def save_ass(self, project: Project, output_path: str) -> str:
        """Save ASS content to specified file path."""
        content = self.generate_ass(project)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return output_path
