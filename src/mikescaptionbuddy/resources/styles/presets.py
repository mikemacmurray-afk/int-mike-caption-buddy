"""Preset caption styles."""

from ...core.models import Style, Alignment


def get_preset_styles():
    """Get a list of preset caption styles."""
    return [
        # 1. Default - Clean white with black outline
        Style(
            id=1,
            name="Default",
            font_family="Arial",
            font_size=48,
            primary_color="#FFFFFF",
            secondary_color="#FFFF00",
            outline_color="#000000",
            outline_width=2,
            shadow_offset_x=2,
            shadow_offset_y=2,
            alignment=Alignment.BOTTOM_CENTER
        ),

        # 2. Netflix Style - White with semi-transparent background
        Style(
            id=2,
            name="Netflix",
            font_family="Arial",
            font_size=42,
            primary_color="#FFFFFF",
            secondary_color="#FFFF00",
            outline_color="#000000",
            outline_width=0,
            background_color="#000000",
            background_opacity=0.75,
            shadow_offset_x=0,
            shadow_offset_y=0,
            alignment=Alignment.BOTTOM_CENTER
        ),

        # 3. YouTube Style - White with strong shadow
        Style(
            id=3,
            name="YouTube",
            font_family="Roboto",
            font_size=45,
            primary_color="#FFFFFF",
            secondary_color="#FFFF00",
            outline_color="#000000",
            outline_width=3,
            shadow_color="#000000",
            shadow_offset_x=3,
            shadow_offset_y=3,
            alignment=Alignment.BOTTOM_CENTER
        ),

        # 4. Vibrant Yellow - Eye-catching
        Style(
            id=4,
            name="Vibrant Yellow",
            font_family="Arial Black",
            font_size=50,
            bold=True,
            primary_color="#FFFF00",
            secondary_color="#FF6600",
            outline_color="#000000",
            outline_width=3,
            shadow_offset_x=2,
            shadow_offset_y=2,
            alignment=Alignment.BOTTOM_CENTER
        ),

        # 5. Neon Cyan - Modern tech look
        Style(
            id=5,
            name="Neon Cyan",
            font_family="Consolas",
            font_size=44,
            primary_color="#00FFFF",
            secondary_color="#FF00FF",
            outline_color="#000033",
            outline_width=2,
            shadow_color="#0066FF",
            shadow_offset_x=2,
            shadow_offset_y=2,
            alignment=Alignment.BOTTOM_CENTER
        ),

        # 6. Karaoke Gold - For music videos
        Style(
            id=6,
            name="Karaoke Gold",
            font_family="Georgia",
            font_size=52,
            bold=True,
            primary_color="#FFD700",
            secondary_color="#FFFFFF",
            outline_color="#8B4513",
            outline_width=3,
            shadow_color="#000000",
            shadow_offset_x=3,
            shadow_offset_y=3,
            alignment=Alignment.BOTTOM_CENTER
        ),

        # 7. Elegant Serif - Documentary style
        Style(
            id=7,
            name="Elegant Serif",
            font_family="Times New Roman",
            font_size=46,
            italic=True,
            primary_color="#FFFFFF",
            secondary_color="#CCCCCC",
            outline_color="#333333",
            outline_width=1,
            shadow_offset_x=1,
            shadow_offset_y=1,
            alignment=Alignment.BOTTOM_CENTER
        ),

        # 8. Bold Impact - High visibility
        Style(
            id=8,
            name="Bold Impact",
            font_family="Impact",
            font_size=54,
            primary_color="#FFFFFF",
            secondary_color="#FF0000",
            outline_color="#000000",
            outline_width=4,
            shadow_offset_x=0,
            shadow_offset_y=0,
            alignment=Alignment.BOTTOM_CENTER
        ),

        # 9. Soft Pastel - Gentle appearance
        Style(
            id=9,
            name="Soft Pastel",
            font_family="Segoe UI",
            font_size=44,
            primary_color="#FFB6C1",
            secondary_color="#98FB98",
            outline_color="#FFFFFF",
            outline_width=2,
            background_color="#000000",
            background_opacity=0.3,
            alignment=Alignment.BOTTOM_CENTER
        ),

        # 10. Dark Mode - For bright videos
        Style(
            id=10,
            name="Dark Mode",
            font_family="Arial",
            font_size=46,
            primary_color="#E0E0E0",
            secondary_color="#808080",
            outline_color="#1A1A1A",
            outline_width=2,
            background_color="#1A1A1A",
            background_opacity=0.8,
            alignment=Alignment.BOTTOM_CENTER
        ),
    ]


def apply_preset_styles(project):
    """Apply preset styles to a project."""
    presets = get_preset_styles()
    project.styles = presets
    project.default_style_id = 1
