# Product Requirements Document (PRD)
## Project: MikesCaptionBuddy (All-in-One Caption Studio)
### Version: 1.0
### Author: Mike
### Last Updated: December 2024

---

## 1. Overview
MikesCaptionBuddy is a desktop application designed to streamline the process of creating visually engaging captions for video projects. It integrates transcription, subtitle editing, styling, and final video export into a single workflow. The app targets content creators, educators, and video editors who want colourful, animated, word-by-word captions without juggling multiple tools.

---

## 2. Goals
- Provide a **single application** that handles transcription, editing, styling, and rendering.
- Support **automatic speech-to-text** using local Whisper installation.
- Enable **interactive styling** (colour, font, angle, boxes) at the word level.
- Allow **animated word-by-word karaoke effects**.
- Export **final videos** with captions burned in or as separate subtitle files.

---

## 3. Target Users
- **Content Creators**: YouTubers, streamers, podcasters.
- **Educators**: Teachers creating engaging learning videos.
- **Video Editors**: Professionals needing fast caption workflows.
- **Accessibility Advocates**: Ensuring captions are clear and visually distinct.

---

## 4. Platform & Environment

### 4.1 Target Platform
- **Operating System**: Windows 11 (primary target)
- **Deployment**: Local single-user installation
- **Language**: English UI only

### 4.2 Prerequisites
- Python 3.10+ (pre-installed)
- Local Whisper installation with models (small, medium, large)
- ffmpeg installed and available in PATH

---

## 5. Technical Architecture

### 5.1 Technology Stack
| Component | Technology | Purpose |
|-----------|------------|---------|
| GUI Framework | PySide6 (Qt6) | Cross-platform desktop UI |
| Video Playback | mpv + python-mpv | High-performance video player |
| Audio Waveform | librosa + numpy | Waveform visualization |
| Transcription | Local Whisper | Speech-to-text |
| Subtitle Rendering | libass via ffmpeg | Styled caption rendering |
| Video Export | ffmpeg-python | Video encoding with burned-in captions |
| Project Storage | SQLite | Project files with embedded video |

### 5.2 Project File Format (.captionstudio)
- SQLite database containing:
  - Full video file (embedded blob)
  - Subtitle data (text, timings, styles)
  - Project metadata
  - Undo history (session only)

### 5.3 Module Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    Main Application                      │
├──────────┬──────────┬──────────┬──────────┬────────────┤
│  Import  │ Transcr. │  Editor  │  Styling │   Export   │
│  Module  │  Module  │  Module  │  Module  │   Module   │
├──────────┴──────────┴──────────┴──────────┴────────────┤
│                    Core Services                         │
│  (Project Manager, Undo/Redo, Auto-Save, Settings)      │
├─────────────────────────────────────────────────────────┤
│                  External Dependencies                   │
│      (ffmpeg, Whisper, mpv, libass, librosa)            │
└─────────────────────────────────────────────────────────┘
```

---

## 6. MVP Scope (Version 1.0)

### 6.1 Included Features

#### Video Import
- Supported formats: MP4, MKV, MOV
- Audio extraction via ffmpeg
- Preview player with waveform display

#### Automatic Transcription
- Local Whisper integration
- Runtime model selection (small, medium, large)
- Output formats: SRT, ASS

#### Subtitle Editing
- Timeline editor with drag-and-drop adjustments
- Word-level segmentation (auto-split into words)
- Manual text editing with undo/redo (10 levels, session-only)
- Basic operations: split, merge, shift timings

#### Styling Engine
- **Global Styles Manager**:
  - System font selection
  - Font size, bold/italic/underline
  - Primary/secondary colours
  - Outline and shadow controls
  - Background box (opaque/transparent)
- **Inline Overrides**:
  - Apply colour, rotation, box, or font changes to specific words
  - GUI-driven (no manual ASS tag editing)
- **Word-by-Word Effects**:
  - Karaoke highlighting
  - Animated colour transitions
- **Presets**: 5-10 starter styles included

#### Interactive GUI
- Right-click context menu on words
- Live preview of captions over video (<100ms latency)
- Drag handles for positioning captions on screen

#### Export Options
- **Subtitle Files**: SRT (plain text), ASS (styled)
- **Final Video**: MP4 with burned-in captions (1080p)
- Codec: H.264

#### System Features
- Auto-save every 2 minutes
- Brief startup overview dialog
- Help system with detailed documentation
- Modern settings/preferences dialog

### 6.2 Performance Requirements
- **Preview Latency**: <100ms for 1080p video
- **Video Length**: Support videos up to 2+ hours
- **Undo/Redo**: 10 levels (styling + timing changes)
- **History**: Session-only (not persisted)

---

## 7. Key Features (Detailed)

### 7.1 Video Import
- Supported formats: MP4, MKV, MOV (AVI in future version)
- Audio extraction via ffmpeg
- Preview player with waveform display

### 7.2 Automatic Transcription
- Local Whisper integration (pre-installed on system)
- Runtime model selection dialog:
  - Small (~244M parameters) - fastest
  - Medium (~769M parameters) - balanced
  - Large (~1.5B parameters) - most accurate
- Language: English (auto-detected)
- Output formats: SRT, ASS

### 7.3 Subtitle Editing
- Timeline editor with drag-and-drop adjustments
- Word-level segmentation (auto-split into words)
- Manual text editing with undo/redo
- Operations: split, merge, shift timings

### 7.4 Styling Engine
- **Global Styles Manager**:
  - System font selection
  - Font size, bold/italic/underline
  - Primary/secondary colours
  - Outline and shadow controls
  - Background box (opaque/transparent)
- **Inline Overrides**:
  - Apply colour, rotation, box, or font changes to specific words
- **Word-by-Word Effects**:
  - Karaoke highlighting (`\k` tags)
  - Animated colour transitions
  - Rotations and scaling per word

### 7.5 Interactive GUI
- Right-click context menu on words:
  - Set colour
  - Change font
  - Apply rotation angle
  - Add box/outline
- Live preview of captions over video
- Drag handles for positioning captions on screen

### 7.6 Export Options
- **Subtitle Files**:
  - SRT (plain text)
  - ASS (styled)
- **Final Video**:
  - Burned-in captions using libass + ffmpeg
  - Format: MP4
  - Resolution: 1080p
  - Codec: H.264

---

## 8. User Workflow
1. **Launch**: See brief overview dialog (dismissible, with "Don't show again")
2. **Open Video**: Import MP4/MKV/MOV
3. **Transcribe**: Select Whisper model → auto-generate captions
4. **Edit**: Adjust timings, split into words
5. **Style**: Select words → right-click → apply colour, font, angle, box
6. **Preview**: Watch live playback with styled captions
7. **Export**: Save as ASS/SRT or burn into final MP4

---

## 9. UI Specification

### 9.1 Overall Layout
- **Main Window** divided into three panels:
  1. **Video Preview Panel** (top-left)
     - Displays imported video with captions overlay
     - Playback controls: Play, Pause, Stop, Seek, Volume
     - Toggle options: Show/Hide captions, Preview styles
  2. **Timeline & Waveform Panel** (bottom)
     - Shows audio waveform and subtitle blocks
     - Drag-and-drop to adjust timings
     - Zoom in/out for precision editing
  3. **Caption Editor Panel** (top-right)
     - Text editor for selected subtitle line
     - Style dropdown to apply global styles
     - Inline styling toolbar for word-level overrides

### 9.2 Startup Dialog
- Brief overview of main features
- Quick-start buttons: "Open Video", "Open Recent", "Help"
- Checkbox: "Don't show this again"
- Link to full documentation

### 9.3 Menus
- **File**
  - Open Video
  - Import Audio
  - Open Recent → (submenu)
  - Save Project (.captionstudio)
  - Export Subtitles (SRT, ASS)
  - Export Video (MP4)
  - Exit
- **Edit**
  - Undo (Ctrl+Z)
  - Redo (Ctrl+Y)
  - Split Subtitle
  - Merge Subtitles
  - Shift Timings...
- **View**
  - Toggle Waveform
  - Show Styles Panel
  - Fullscreen Preview
- **Tools**
  - Transcribe (Whisper)...
  - Style Presets Manager
  - Settings...
- **Help**
  - Getting Started
  - Keyboard Shortcuts
  - About MikesCaptionBuddy

### 9.4 Right-Click Context Menu (Word-Level)
When user selects a word in the Caption Editor:
- **Set Colour** → Colour picker dialog
- **Set Font** → Font selector (system fonts)
- **Set Size** → Numeric input or slider
- **Set Angle** → Rotation input (degrees)
- **Add Box/Outline** → Toggle + colour/width options
- **Apply Karaoke Highlight** → Duration input (centiseconds)
- **Reset Style** → Remove overrides

### 9.5 Styles Manager
- **Global Styles List**:
  - Add, Edit, Delete styles
  - Preview sample text with applied style
- **Style Properties**:
  - Font family (system fonts), size, bold/italic/underline
  - Primary colour, secondary colour
  - Outline colour, width
  - Shadow colour, offset
  - Background box (opaque/transparent)
  - Alignment (top, bottom, center)
- **Presets**: 5-10 starter styles included

### 9.6 Timeline Editor
- **Waveform Display**:
  - Shows audio peaks for precise timing
  - Click to set playhead position
- **Subtitle Blocks**:
  - Drag to adjust timing
  - Resize to extend/shrink duration
  - Colour-coded by style applied
- **Word-by-Word Mode**:
  - Each word appears as a mini-block
  - Drag to adjust karaoke timing

### 9.7 Settings Dialog
Modern tabbed layout:
- **General**:
  - Auto-save interval (default: 2 minutes)
  - Show startup dialog
  - Recent files limit
- **Transcription**:
  - Default Whisper model
  - Whisper executable path
- **Export**:
  - Default export directory
  - Default video codec settings
- **Appearance**:
  - UI theme (light/dark/system)
  - Editor font size

### 9.8 Export Dialog
- **Subtitle Export**:
  - Format: SRT, ASS
  - Options: Include styles (ASS only), plain text only
- **Video Export**:
  - Resolution: 1080p (720p option)
  - Burn-in captions: Yes/No
  - Codec: H.264
  - Quality preset: Fast, Balanced, Quality
  - Audio: Passthrough or re-encode

### 9.9 Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| Space | Play/Pause |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+S | Save project |
| Ctrl+E | Export dialog |
| Ctrl+O | Open video |
| Left/Right | Nudge subtitle timings (±100ms) |
| Shift+Left/Right | Nudge subtitle timings (±1s) |
| Ctrl+Shift+C | Open colour picker for selected word |
| F11 | Fullscreen preview |
| Escape | Exit fullscreen / Cancel dialog |

### 9.10 Audio-Only Import
- When user imports audio file (MP3, WAV):
  - Transcription proceeds normally
  - Video preview shows solid colour background (dark grey)
  - Export creates video with solid background + captions

---

## 10. User Journey Storyboard

### 10.1 Scenario: Creating Colourful Word-by-Word Captions

#### Step 1: Launch & Import
- **Screen**: Startup Dialog
- **Action**: User clicks "Open Video" → selects MP4 file
- **UI Elements**:
  - Startup dialog with overview
  - File browser
  - Video Preview Panel shows first frame
  - Timeline Panel loads waveform

#### Step 2: Auto-Transcription
- **Screen**: Video Preview + Timeline
- **Action**: User clicks "Tools → Transcribe (Whisper)"
- **UI Elements**:
  - Model selection dialog (small, medium, large)
  - Progress bar showing transcription status
  - Captions auto-populate in Timeline and Caption Editor

#### Step 3: Edit Captions
- **Screen**: Timeline Editor
- **Action**: User adjusts timings by dragging subtitle blocks
- **UI Elements**:
  - Waveform with draggable subtitle blocks
  - Zoom slider for precision
  - Caption Editor Panel shows text for selected block

#### Step 4: Style Captions
- **Screen**: Caption Editor + Styles Manager
- **Action**: User selects a word → right-click → "Set Colour"
- **UI Elements**:
  - Context menu: Colour, Font, Size, Angle, Box, Karaoke
  - Colour picker dialog
  - Live preview in Video Panel
- **Example**: User sets "Hello" to red, "World" to cyan with rotation

#### Step 5: Apply Word-by-Word Animation
- **Screen**: Caption Editor
- **Action**: User enables "Word-by-Word Mode"
- **UI Elements**:
  - Each word appears as mini-block in Timeline
  - User sets karaoke durations (e.g., 0.3s per word)
  - Secondary colour highlights active word during playback

#### Step 6: Preview
- **Screen**: Video Preview Panel
- **Action**: User clicks Play
- **UI Elements**:
  - Captions overlay with applied colours, boxes, rotations
  - Karaoke highlight animates word-by-word
  - Toggle: Show/hide captions

#### Step 7: Export
- **Screen**: Export Dialog
- **Action**: User chooses "Export Video with Burned-in Captions"
- **UI Elements**:
  - Format: MP4
  - Resolution: 1080p
  - Subtitle export options: SRT, ASS
- **Result**: Final video file with colourful, animated captions

#### Step 8: Completion
- **Screen**: Success Dialog
- **Action**: User sees "Export Complete" message
- **UI Elements**:
  - Button: "Open Folder"
  - Button: "Play Video"
  - Button: "Close"

### 10.2 Alternate Journeys
- **Audio-only import**: User opens MP3 → Whisper transcribes → captions styled → exported with solid background
- **Manual transcription**: User types captions manually in Caption Editor → applies styles → exports

---

## 11. Non-Functional Requirements
- **Performance**: Real-time preview with <100ms latency at 1080p
- **Platform**: Windows 11 (local execution)
- **Scalability**: Handle long videos (2+ hours)
- **Usability**: Intuitive GUI for non-technical users
- **Reliability**: Auto-save every 2 minutes

---

## 12. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Performance bottlenecks | Use GPU acceleration for Whisper; proxy preview if needed |
| Large project files | SQLite with efficient blob storage; warn user of file size |
| Whisper model loading time | Show progress indicator; cache model in memory |
| ffmpeg encoding slow | Show progress bar; use hardware acceleration if available |

---

## 13. Success Metrics
- Time saved compared to using multiple apps
- User satisfaction (ease of styling captions)
- Quality of exported captions (accuracy + visual appeal)
- Application stability (crash-free sessions)

---

## 14. Version Roadmap

### Version 1.0 (MVP) - Current
Core caption creation workflow with essential features.

### Version 1.1 - Enhanced Export
- [ ] AVI format import support
- [ ] VTT subtitle export
- [ ] 4K video export (2160p)
- [ ] H.265 codec option
- [ ] MKV export format

### Version 1.2 - Batch Processing
- [ ] Batch video import
- [ ] Apply style preset to multiple videos
- [ ] Queue-based export processing
- [ ] Batch export progress tracking

### Version 1.3 - Advanced Visualization
- [ ] Spectrogram view (toggle with waveform)
- [ ] Enhanced timeline zoom controls
- [ ] Minimap navigation for long videos

### Version 1.4 - Style Library
- [ ] 20+ preset styles (colourful, boxed, rotated, karaoke)
- [ ] Import/export style presets
- [ ] Style categories and search
- [ ] Community style sharing (local file exchange)

### Version 1.5 - Plugin System
- [ ] Plugin architecture for custom effects
- [ ] Python-based plugin API
- [ ] Built-in plugin manager
- [ ] Sample plugins (custom animations, filters)

### Version 2.0 - Advanced Features
- [ ] Cloud transcription option (faster processing)
- [ ] AI-powered style suggestions
- [ ] Animated caption presets (bounce, fade, zoom)
- [ ] Multi-language UI support
- [ ] Persistent undo history (across sessions)

### Future Considerations
- Cross-platform support (macOS, Linux)
- Collaboration features (multi-user editing)
- Mobile companion app for quick reviews
- Real-time collaboration via cloud sync

---

## Appendix A: File Format Specification

### .captionstudio File Structure (SQLite)

```sql
-- Project metadata
CREATE TABLE project (
    id INTEGER PRIMARY KEY,
    name TEXT,
    created_at DATETIME,
    modified_at DATETIME,
    version TEXT
);

-- Embedded video file
CREATE TABLE video (
    id INTEGER PRIMARY KEY,
    filename TEXT,
    data BLOB,
    duration_ms INTEGER,
    width INTEGER,
    height INTEGER,
    fps REAL
);

-- Subtitle entries
CREATE TABLE subtitles (
    id INTEGER PRIMARY KEY,
    start_ms INTEGER,
    end_ms INTEGER,
    text TEXT,
    style_id INTEGER,
    position_x REAL,
    position_y REAL,
    FOREIGN KEY (style_id) REFERENCES styles(id)
);

-- Word-level data
CREATE TABLE words (
    id INTEGER PRIMARY KEY,
    subtitle_id INTEGER,
    word_index INTEGER,
    text TEXT,
    start_ms INTEGER,
    end_ms INTEGER,
    style_override TEXT,  -- JSON for inline style overrides
    FOREIGN KEY (subtitle_id) REFERENCES subtitles(id)
);

-- Style definitions
CREATE TABLE styles (
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
    alignment TEXT
);

-- Application settings (per-project overrides)
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

---

## Appendix B: Dependencies

### Python Packages
```
PySide6>=6.5.0          # Qt6 GUI framework
python-mpv>=1.0.0       # Video playback
librosa>=0.10.0         # Audio analysis
numpy>=1.24.0           # Numerical operations
ffmpeg-python>=0.2.0    # Video export
openai-whisper>=latest  # Transcription (or local whisper)
```

### System Dependencies
- ffmpeg (with libass support)
- mpv
- Whisper models (small, medium, large)

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| ASS | Advanced SubStation Alpha - subtitle format supporting rich styling |
| SRT | SubRip Text - simple subtitle format with basic timing |
| Karaoke | Word-by-word highlighting synchronized with speech |
| libass | Library for rendering ASS subtitles |
| Whisper | OpenAI's speech recognition model |
| Waveform | Visual representation of audio amplitude over time |

---
