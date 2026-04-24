# MikesCaptionBuddy (All-in-One Caption Studio) - Technical Specification
**Version:** 1.0 (LATEST)  
**Repository:** `mikemacmurray-afk/int-mike-caption-buddy`

---

## 1. Project Overview
MikesCaptionBuddy is a desktop application written in Python and PySide6 designed to streamline the workflow for creating high-impact, word-by-word animated captions for video content. It targets educators and content creators who want a professional "karaoke-style" captioning experience within a single, local application.

---

## 2. Core Features (V1.0)
- **Multi-Format Video/Audio Import:** Support for MP4, MKV, MOV, and local audio files (MP3, WAV).
- **Local Whisper Transcription:** High-accuracy speech-to-text using local models (`small`, `medium`, `large`).
- **Download Transcription:** Export formatted text files with automatic newline breaks after every full stop for script review.
- **Project Persistence:** Saves all work (timings, styles, video references) in `.captionstudio` (SQLite-based) project files.
- **Word-Level Styling:** Interactive GUI for applying colors, fonts, rotation angles, and boxes to individual words via right-click.
- **Visual Waveform Editing:** Draggable subtitle blocks on an audio waveform for precise timing.
- **Animated Preview:** Real-time playback with burned-in style previews (<100ms latency).
- **Export Options:** Styled ASS subtitles, plain SRT, or full video export with captions burned in via FFmpeg.

---

## 3. Technical Architecture

### 3.1 Technology Stack
- **Languages:** Python 3.10+
- **GUI Framework:** PySide6 (Qt6)
- **Video Engine:** `mpv` + `python-mpv`
- **Audio Analysis:** `librosa`, `numpy`, `soundfile`
- **Transcription Engine:** `openai-whisper`
- **Video Processing:** `FFmpeg` (via `ffmpeg-python`)
- **Subtitle Logic:** `libass`, `pysubs2`
- **Data Storage:** SQLite (built-in)

### 3.2 Directory Structure
```text
/src/mikescaptionbuddy
├── core/
│   ├── models.py          # Data classes (Project, Subtitle, Word, Style)
│   ├── project_manager.py # SQL logic and File I/O
│   ├── ass_generator.py   # Converts models to ASS format
│   └── settings.py        # App configuration persistence
├── ui/
│   ├── main_window.py     # Main layout and toolbar logic
│   ├── video_panel.py     # mpv-based player and caption overlay
│   ├── timeline_panel.py  # Waveform and subtitle blocks
│   ├── caption_panel.py   # Word-by-word editor and styling
│   └── dialogs/           # Transcription, Export, and Settings UI
├── resources/             # Icons and style presets
└── main.py                # App entry point
```

---

## 4. Design Specification

### 4.1 UI Layout
- **Top Left (Video Panel):** Active video preview with libass caption overlay.
- **Top Right (Caption Panel):** List of segments and word-by-word styling tools.
- **Bottom (Timeline Panel):** Interactive waveform visualization with zoom and drag handles.
- **Toolbar:** Immediate access to:
  - `Open Video`, `Open Project`, `Save Project`
  - `Undo/Redo`
  - `Transcribe (Whisper)`, `Download Transcription`
  - `Style Manager`, `Export Video`, `Export Subtitles`

### 4.2 Data Model Highlights
- **Project:** Contains `VideoInfo`, `List[Subtitle]`, and `List[Style]`.
- **Subtitle:** Tracks `start_ms`, `end_ms`, and a `List[Word]`.
- **Word:** Tracks text and individual `StyleOverride` (color, rotation, scale).
- **Style:** Global CSS-like definitions for fonts, shadows, and alignment.

---

## 5. Development Roadmap (Next Phase)
- [ ] **Batch Processing:** Ability to apply styles to multiple videos.
- [ ] **Advanced Animation Presets:** Bounce, Fade, and Zoom effects per word.
- [ ] **Direct Social Integration:** Preset dimensions for TikTok (9:16) vs YouTube (16:9).
- [ ] **Auto-Cleanup AI:** Tooling to automatically remove "um" and "uh" from captions.

---

## 6. Installation & Execution
1. Ensure `python 3.10+` and `ffmpeg` are in the system PATH.
2. Install dependencies: `pip install -r requirements.txt`.
3. Launch via root command: `Run-Caption-Buddy.cmd`.
