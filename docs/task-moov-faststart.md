# Task: Add `-movflags +faststart` to Video Export

## Why
All MP4 files exported by Caption Buddy have the `moov` atom at the **end** of the file.
Web browsers need `moov` at the **beginning** to start streaming before the full file is
downloaded. Without it, videos stall mid-play or refuse to start until the entire file is
buffered. This has been confirmed on the production training system — all 8 exported videos
show `moov` at the final bytes of the file.

## The Fix
Add `-movflags +faststart` to both ffmpeg export paths in:

**`src/mikescaptionbuddy/ui/dialogs/export_dialog.py`**

---

### Path 1 — Subprocess (captions burned in) — lines ~292–302

Current:
```python
cmd = [
    ffmpeg_path,
    '-y',
    '-i', input_path,
    '-vf', f"ass='{ass_path_escaped}',scale={width}:{height}",
    '-c:v', 'libx264',
    '-preset', preset,
    '-crf', '23',
    '-c:a', 'aac',
    self.output_path
]
```

Fixed (add `-movflags +faststart` before the output path):
```python
cmd = [
    ffmpeg_path,
    '-y',
    '-i', input_path,
    '-vf', f"ass='{ass_path_escaped}',scale={width}:{height}",
    '-c:v', 'libx264',
    '-preset', preset,
    '-crf', '23',
    '-c:a', 'aac',
    '-movflags', '+faststart',
    self.output_path
]
```

---

### Path 2 — ffmpeg-python (no captions / simple re-encode) — lines ~326–334

Current:
```python
stream = ffmpeg.output(
    stream,
    self.output_path,
    vcodec='libx264',
    acodec='aac',
    preset=preset,
    crf=23
)
```

Fixed (add `movflags='+faststart'`):
```python
stream = ffmpeg.output(
    stream,
    self.output_path,
    vcodec='libx264',
    acodec='aac',
    preset=preset,
    crf=23,
    movflags='+faststart'
)
```

---

## Also fix existing production videos

The 8 videos already uploaded to the production server still have `moov` at the back.
After fixing Caption Buddy, re-export each video and re-upload via the Admin → Media panel,
OR run the following on the Hetzner server (if ffmpeg is installed):

```bash
cd /home/deploy/ai-multi-tenant-training-system/uploads/videos
for f in *.mp4; do
    ffmpeg -i "$f" -movflags +faststart -codec copy "${f%.mp4}_fixed.mp4" && \
    mv "${f%.mp4}_fixed.mp4" "$f"
done
```

`-codec copy` means no re-encoding — it's fast (seconds per file) and lossless.

## Verification

After exporting a new video, confirm moov is at the front:
```python
import struct

def check_moov(path):
    with open(path, 'rb') as f:
        pos = 0
        while True:
            data = f.read(8)
            if len(data) < 8:
                break
            size = struct.unpack('>I', data[:4])[0]
            box_type = data[4:8].decode('latin1')
            print(f"  {box_type} at byte {pos}")
            if box_type == 'moov':
                print("  ✓ moov is FRONT" if pos < 1000 else "  ✗ moov is BACK")
                break
            if size == 0 or size > 10_000_000:
                break
            pos += size
            f.seek(pos)

check_moov('your_exported.mp4')
```

Expected output after fix: `moov at byte 8` (right after `ftyp`).
