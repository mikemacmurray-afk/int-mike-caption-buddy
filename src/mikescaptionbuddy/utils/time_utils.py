"""Time conversion utilities."""


def ms_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT time format (HH:MM:SS,mmm)."""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def ms_to_ass_time(ms: int) -> str:
    """Convert milliseconds to ASS time format (H:MM:SS.cc)."""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    centiseconds = (ms % 1000) // 10
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def srt_time_to_ms(time_str: str) -> int:
    """Convert SRT time format to milliseconds."""
    # Format: HH:MM:SS,mmm
    parts = time_str.replace(',', ':').split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2])
    millis = int(parts[3])
    return hours * 3600000 + minutes * 60000 + seconds * 1000 + millis


def format_duration(ms: int) -> str:
    """Format duration for display (M:SS or H:MM:SS)."""
    seconds = ms // 1000
    minutes = seconds // 60
    hours = minutes // 60

    if hours > 0:
        return f"{hours}:{minutes % 60:02d}:{seconds % 60:02d}"
    else:
        return f"{minutes}:{seconds % 60:02d}"
