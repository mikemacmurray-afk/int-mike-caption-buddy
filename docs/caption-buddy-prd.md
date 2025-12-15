# Product Requirements Document (PRD)
## Project: All-in-One Caption Studio
### Version: 1.0
### Author: Mike

---

## 1. Overview
The All-in-One Caption Studio is a desktop application designed to streamline the process of creating visually engaging captions for video projects. It integrates transcription, subtitle editing, styling, and final video export into a single workflow. The app targets content creators, educators, and video editors who want colourful, animated, word-by-word captions without juggling multiple tools.

---

## 2. Goals
- Provide a **single application** that handles transcription, editing, styling, and rendering.
- Support **automatic speech-to-text** using Whisper.
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

## 4. Key Features

### 4.1 Video Import
- Supported formats: MP4, MKV, AVI, MOV.
- Audio extraction via ffmpeg.
- Preview player with waveform and spectrogram.

### 4.2 Automatic Transcription
- Whisper integration (local Whisper.cpp or API).
- Language detection and multilingual support.
- Output formats: SRT, VTT, ASS.
- Configurable model selection (tiny, small, medium, large).

### 4.3 Subtitle Editing
- Timeline editor with drag-and-drop adjustments.
- Word-level segmentation (auto-split into words).
- Manual text editing with undo/redo.
- Batch operations (split, merge, shift timings).

### 4.4 Styling Engine
- **Global Styles Manager**:
  - Font selection.
  - Font size, bold/italic/underline.
  - Primary/secondary colours.
  - Outline and shadow controls.
  - Background box (opaque/transparent).
- **Inline Overrides**:
  - Apply colour, rotation, box, or font changes to specific words.
  - Syntax similar to ASS tags but GUI-driven.
- **Word-by-Word Effects**:
  - Karaoke highlighting (`\k` tags).
  - Animated colour transitions.
  - Rotations and scaling per word.

### 4.5 Interactive GUI
- Right-click context menu on words:
  - Set colour.
  - Change font.
  - Apply rotation angle.
  - Add box/outline.
- Live preview of captions over video.
- Drag handles for positioning captions on screen.

### 4.6 Export Options
- **Subtitle Files**:
  - SRT (plain text).
  - ASS (styled).
- **Final Video**:
  - Burned-in captions using libass + ffmpeg.
  - Export formats: MP4, MKV.
  - Resolution options (1080p, 4K).
- **Batch Export**:
  - Process multiple videos with consistent styles.

---

## 5. Non-Functional Requirements
- **Performance**: Real-time preview with minimal lag.
- **Cross-Platform**: Windows, macOS, Linux.
- **Scalability**: Handle long videos (2+ hours).
- **Usability**: Intuitive GUI for non-technical users.
- **Extensibility**: Plugin system for custom effects.

---

## 6. Technical Architecture
- **Frontend**: Electron or Qt for cross-platform GUI.
- **Backend**:
  - Whisper.cpp for transcription.
  - libass for subtitle rendering.
  - ffmpeg for video/audio processing.
- **Data Storage**:
  - Local project files (.captionstudio).
  - Cache for Whisper models.
- **Modules**:
  - Import Module.
  - Transcription Module.
  - Editing Module.
  - Styling Module.
  - Export Module.

---

## 7. User Workflow
1. **Open Video**: Import MP4/MKV/AVI.
2. **Transcribe**: Whisper auto-generates captions.
3. **Edit**: Adjust timings, split into words.
4. **Style**: Select words → right-click → apply colour, font, angle, box.
5. **Preview**: Watch live playback with styled captions.
6. **Export**: Save as ASS/SRT or burn into final MP4.

---

## 8. Future Enhancements
- Cloud transcription for faster processing.
- AI-powered style suggestions (auto colour themes).
- Animated caption presets (bounce, fade, zoom).
- Collaboration features (multi-user editing).
- Mobile companion app for quick reviews.

---

## 9. Risks & Mitigations
- **Performance bottlenecks**: Use GPU acceleration for Whisper and rendering.
- **Format compatibility**: Default to MP4 + ASS to ensure broad support.
- **User learning curve**: Provide tutorials and preset styles.

---

## 10. Success Metrics
- Time saved compared to using multiple apps.
- User satisfaction (ease of styling captions).
- Adoption by content creators and educators.
- Quality of exported captions (accuracy + visual appeal).

---

## 11. UI Specification

### 11.1 Overall Layout
- **Main Window** divided into three panels:
  1. **Video Preview Panel** (top-left)
     - Displays imported video with captions overlay.
     - Playback controls: Play, Pause, Stop, Seek, Volume.
     - Toggle options: Show/Hide captions, Preview styles.
  2. **Timeline & Waveform Panel** (bottom)
     - Shows audio waveform and subtitle blocks.
     - Drag-and-drop to adjust timings.
     - Zoom in/out for precision editing.
  3. **Caption Editor Panel** (top-right)
     - Text editor for selected subtitle line.
     - Style dropdown to apply global styles.
     - Inline styling toolbar for word-level overrides.

---

### 11.2 Menus
- **File**
  - Open Video
  - Import Audio
  - Save Project (.captionstudio)
  - Export Subtitles (SRT, ASS, VTT)
  - Export Video (MP4, MKV)
- **Edit**
  - Undo/Redo
  - Split/Merge subtitles
  - Batch shift timings
- **View**
  - Toggle waveform/spectrogram
  - Show styles panel
  - Fullscreen preview
- **Tools**
  - Transcribe (Whisper)
  - Batch process
  - Style presets manager
- **Help**
  - Tutorials
  - Keyboard shortcuts
  - About

---

### 11.3 Right-Click Context Menu (Word-Level)
When user selects a word in the Caption Editor:
- **Set Colour** → Colour picker dialog.
- **Set Font** → Font selector.
- **Set Size** → Numeric input or slider.
- **Set Angle** → Rotation input (degrees).
- **Add Box/Outline** → Toggle + colour/width options.
- **Apply Karaoke Highlight** → Duration input (centiseconds).
- **Reset Style** → Remove overrides.

---

### 11.4 Styles Manager
- **Global Styles List**:
  - Add, Edit, Delete styles.
  - Preview sample text with applied style.
- **Style Properties**:
  - Font family, size, bold/italic/underline.
  - Primary colour, secondary colour.
  - Outline colour, width.
  - Shadow colour, offset.
  - Background box (opaque/transparent).
  - Alignment (top, bottom, center).
- **Presets**:
  - 20+ fancy styles included (colourful, boxed, rotated, karaoke).

---

### 11.5 Timeline Editor
- **Waveform Display**:
  - Shows audio peaks for precise timing.
  - Click to set start/end markers.
- **Subtitle Blocks**:
  - Drag to adjust timing.
  - Resize to extend/shrink duration.
  - Colour-coded by style applied.
- **Word-by-Word Mode**:
  - Each word appears as a mini-block.
  - Drag to adjust karaoke timing.

---

### 11.6 Export Dialog
- **Subtitle Export**:
  - Format: SRT, ASS, VTT.
  - Options: Include styles, plain text only.
- **Video Export**:
  - Resolution: 720p, 1080p, 4K.
  - Burn-in captions (yes/no).
  - Codec options: H.264, H.265.
  - Audio passthrough or re-encode.
- **Batch Export**:
  - Apply same style to multiple videos.
  - Queue processing.

---

### 11.7 Keyboard Shortcuts
- Space → Play/Pause.
- Ctrl+Z → Undo.
- Ctrl+Y → Redo.
- Ctrl+S → Save project.
- Ctrl+E → Export.
- Arrow keys → Nudge subtitle timings.
- Ctrl+Shift+C → Open colour picker for selected word.

---

### 11.8 Accessibility
- High-contrast mode for UI.
- Screen reader support for menus.
- Keyboard-only navigation.
- Adjustable font sizes in editor.

---

## 12. User Journey Storyboard

### 12.1 Scenario: Creating Colourful Word-by-Word Captions

---

### Step 1: Launch & Import
- **Screen:** Welcome Dashboard
- **Action:** User clicks "Open Video" → selects MP4 file.
- **UI Elements:**
  - File menu with "Open Video".
  - Video Preview Panel shows first frame.
  - Timeline Panel loads waveform.

---

### Step 2: Auto-Transcription
- **Screen:** Video Preview + Timeline
- **Action:** User clicks "Tools → Transcribe (Whisper)".
- **UI Elements:**
  - Model selection dialog (tiny, small, medium, large).
  - Progress bar showing transcription status.
  - Captions auto-populate in Timeline and Caption Editor.

---

### Step 3: Edit Captions
- **Screen:** Timeline Editor
- **Action:** User adjusts timings by dragging subtitle blocks.
- **UI Elements:**
  - Waveform with draggable subtitle blocks.
  - Zoom slider for precision.
  - Caption Editor Panel shows text for selected block.

---

### Step 4: Style Captions
- **Screen:** Caption Editor + Styles Manager
- **Action:** User selects a word → right-click → "Set Colour".
- **UI Elements:**
  - Context menu: Colour, Font, Size, Angle, Box, Karaoke.
  - Colour picker dialog.
  - Live preview in Video Panel.
- **Example:** User sets "Hello" to red, "World" to cyan with rotation.

---

### Step 5: Apply Word-by-Word Animation
- **Screen:** Caption Editor
- **Action:** User enables "Word-by-Word Mode".
- **UI Elements:**
  - Each word appears as mini-block in Timeline.
  - User sets karaoke durations (e.g., 0.3s per word).
  - Secondary colour highlights active word during playback.

---

### Step 6: Preview
- **Screen:** Video Preview Panel
- **Action:** User clicks Play.
- **UI Elements:**
  - Captions overlay with applied colours, boxes, rotations.
  - Karaoke highlight animates word-by-word.
  - Toggle: Show/hide captions.

---

### Step 7: Export
- **Screen:** Export Dialog
- **Action:** User chooses "Export Video with Burned-in Captions".
- **UI Elements:**
  - Format options: MP4, MKV.
  - Resolution options: 720p, 1080p, 4K.
  - Subtitle export options: SRT, ASS.
- **Result:** Final video file with colourful, animated captions.

---

### Step 8: Completion
- **Screen:** Success Dialog
- **Action:** User sees "Export Complete" message.
- **UI Elements:**
  - Button: "Open Folder".
  - Button: "Play Video".
  - Option: "Create New Project".

---

## 12.2 Alternate Journeys
- **Audio-only import:** User opens MP3 → Whisper transcribes → captions styled → exported with dummy video background.
- **Batch processing:** User imports multiple videos → applies same style preset → exports all in queue.
- **Manual transcription:** User types captions manually in Caption Editor → applies styles → exports.

---
