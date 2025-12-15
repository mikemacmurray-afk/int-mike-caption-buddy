# MikesCaptionBuddy - Installation Guide

## System Requirements

- **Operating System**: Windows 11 (Windows 10 also supported)
- **Python**: 3.10 or higher
- **RAM**: 8GB minimum (16GB recommended for large Whisper models)
- **Storage**: 5GB free space (for Whisper models and project files)

---

## Prerequisites

### 1. Python

If not already installed:

1. Download from: https://www.python.org/downloads/
2. Run installer
3. **Important**: Check "Add Python to PATH" during installation
4. Verify installation:
   ```powershell
   python --version
   ```

### 2. FFmpeg (Required)

FFmpeg is required for video/audio processing and export.

#### Option A: Using winget (Recommended)
```powershell
winget install FFmpeg
```

#### Option B: Using Chocolatey
```powershell
choco install ffmpeg
```

#### Option C: Manual Installation
1. Download from: https://www.gyan.dev/ffmpeg/builds/
2. Get the **"ffmpeg-release-essentials.zip"** file
3. Extract to `C:\ffmpeg`
4. Add to PATH:
   - Open **System Properties** → **Environment Variables**
   - Under **System variables**, find **Path**
   - Click **Edit** → **New**
   - Add: `C:\ffmpeg\bin`
   - Click **OK** to save

#### Verify FFmpeg
```powershell
ffmpeg -version
```

### 3. MPV Player (Required)

MPV is required for video playback in the application.

#### Option A: Using winget
```powershell
winget install mpv
```

#### Option B: Using Chocolatey
```powershell
choco install mpv
```

#### Option C: Manual Installation
1. Download from: https://sourceforge.net/projects/mpv-player-windows/files/
2. Extract to `C:\mpv`
3. Add `C:\mpv` to your PATH (same process as FFmpeg above)

#### Verify MPV
```powershell
mpv --version
```

### 4. Whisper (Required for Transcription)

If not already installed:

```powershell
pip install openai-whisper
```

Download models (first transcription will auto-download, or pre-download):
```powershell
# Small model (~244MB) - Fast
python -c "import whisper; whisper.load_model('small')"

# Medium model (~769MB) - Balanced
python -c "import whisper; whisper.load_model('medium')"

# Large model (~1.5GB) - Most accurate
python -c "import whisper; whisper.load_model('large')"
```

---

## Installation Steps

### Step 1: Navigate to Project Directory

```powershell
cd C:\path\to\AIJourney
```

### Step 2: Create Virtual Environment (Recommended)

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\activate
```

> **Note**: You'll need to activate the virtual environment each time you open a new terminal.

### Step 3: Install Python Dependencies

```powershell
pip install -r requirements.txt
```

If you encounter errors, install packages individually:

```powershell
pip install PySide6>=6.5.0
pip install python-mpv>=1.0.0
pip install librosa>=0.10.0
pip install numpy>=1.24.0
pip install soundfile>=0.12.0
pip install ffmpeg-python>=0.2.0
pip install pysubs2>=1.6.0
pip install openai-whisper
```

### Step 4: Run the Application

```powershell
python run.py
```

---

## Quick Start Guide

1. **Launch**: Run `python run.py`
2. **Open Video**: File → Open Video (or click "Open Video" on startup)
3. **Transcribe**: Tools → Transcribe (Whisper) → Select model → Start
4. **Edit**: Click subtitles in timeline to edit text and timing
5. **Style**: Right-click on words to change colors, fonts, effects
6. **Preview**: Press Space to play/pause and see captions live
7. **Export**: File → Export Video to create final MP4 with burned-in captions

---

## Troubleshooting

### "python-mpv" Installation Fails

```powershell
pip install python-mpv --no-cache-dir
```

If still failing, ensure MPV is installed and in PATH.

### "mpv not found" Error at Runtime

Ensure mpv.exe location is in your PATH:
```powershell
# Temporary fix for current session
$env:PATH += ";C:\mpv"

# Or set permanently via System Properties → Environment Variables
```

### "ffmpeg not found" Error

```powershell
# Check if ffmpeg is accessible
where ffmpeg

# If not found, add to PATH:
$env:PATH += ";C:\ffmpeg\bin"
```

### PySide6 DLL Load Errors

```powershell
pip uninstall PySide6
pip install PySide6 --force-reinstall
```

### Whisper "CUDA out of memory" Error

Use a smaller model:
- Change from `large` to `medium` or `small` in transcription settings

Or force CPU mode (slower but works):
```powershell
set CUDA_VISIBLE_DEVICES=-1
python run.py
```

### Video Won't Play (Black Screen)

1. Ensure video file is not corrupted
2. Try a different video format (MP4 with H.264 works best)
3. Check MPV installation:
   ```powershell
   mpv --version
   mpv your_video.mp4
   ```

### Waveform Not Loading

Install audio dependencies:
```powershell
pip install librosa soundfile --force-reinstall
```

### Application Crashes on Startup

Check for missing dependencies:
```powershell
python -c "import PySide6; print('PySide6 OK')"
python -c "import mpv; print('mpv OK')"
python -c "import librosa; print('librosa OK')"
python -c "import ffmpeg; print('ffmpeg-python OK')"
python -c "import whisper; print('whisper OK')"
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Play/Pause |
| `Ctrl+O` | Open Video |
| `Ctrl+S` | Save Project |
| `Ctrl+E` | Export Video |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+T` | Transcribe |
| `Left/Right` | Nudge timing ±100ms |
| `Shift+Left/Right` | Nudge timing ±1s |
| `F11` | Fullscreen Preview |
| `Ctrl+Shift+C` | Color picker for selected word |

---

## File Locations

| Item | Location |
|------|----------|
| Settings | `%APPDATA%\MikesCaptionBuddy\settings.json` |
| Whisper Models | `%USERPROFILE%\.cache\whisper\` |
| Project Files | User-specified (`.captionstudio` extension) |

---

## Updating

To update the application:

```powershell
cd C:\path\to\AIJourney
git pull origin main

# Reactivate virtual environment if using one
.\venv\Scripts\activate

# Update dependencies
pip install -r requirements.txt --upgrade
```

---

## Uninstalling

1. Delete the project folder
2. Remove virtual environment (if created)
3. Optionally remove settings:
   ```powershell
   rmdir /s "%APPDATA%\MikesCaptionBuddy"
   ```

---

## Support

For issues or feature requests, check the project documentation or create an issue in the repository.

---

## Version

- **MikesCaptionBuddy**: 1.0.0
- **Last Updated**: December 2024
