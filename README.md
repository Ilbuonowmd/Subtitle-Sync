# Subtitle Sync

A simple Python script for batch-processing subtitle files by **dragging and dropping files or folders** onto the script.

Instead of processing subtitles one by one, simply drop multiple subtitle files or entire folders onto the script. It will automatically find and process all supported subtitle files.

## Features

- **Simple drag-and-drop operation** — drop individual files or entire folders onto the script.
- **Batch processing** — process multiple subtitle files in one run.
- **Recursive folder scanning** — automatically finds supported files inside subfolders.
- **7 FPS conversion modes** — including an option to keep the original FPS.
- **Millisecond delay adjustment**.
- **Frame-based delay adjustment** in the "No FPS Change" mode (e.g. `-475@23.976`).
- **SUP subtitle synchronization** using SupMover.
- **SRT subtitle synchronization** directly through the script.
- Preserves the original folder structure in the output directory.
- Original subtitle files are never modified.

## Requirements

- Windows
- Python 3.9 or newer
- **[SupMover](https://github.com/MonoS/SupMover)** — required for processing `.sup` (PGS) subtitles.

### Dependency

This script uses **SupMover** to synchronize PGS subtitle files.

- GitHub: https://github.com/MonoS/SupMover
- Download: https://github.com/MonoS/SupMover/releases

Place `SupMover.exe` in the same directory as the script or make sure it is available in your system PATH.

SRT processing does not require SupMover.

## Usage

1. Place the script and its required files in the same directory:

   ```text
   Subtitle Sync/
   ├── Subtitle_sync.py
   ├── Subtitle_sync.bat
   └── SupMover.exe
   ```

2. Drag and drop one or more subtitle files or folders onto `Subtitle_sync.bat`.
3. Select the desired FPS conversion mode.
4. Enter the subtitle delay.
5. The script will automatically process all supported files.

## FPS Conversion Modes

| Mode | Conversion |
|---|---|
| 1 | No FPS change |
| 2 | 23.976 → 24 FPS |
| 3 | 23.976 → 25 FPS |
| 4 | 24 → 23.976 FPS |
| 5 | 24 → 25 FPS |
| 6 | 25 → 23.976 FPS |
| 7 | 25 → 24 FPS |

## Delay Input

Delay can be entered in milliseconds in all modes.

In **Mode 1 (No FPS Change)**, you can also enter the delay in frames using this format:

```text
<frames>@<FPS>
```

Examples:

```text
-475@23.976
250@24
-100@25
-475@24000/1001
```

The script converts frame-based delays into milliseconds using:

```text
Delay (ms) = Frames × 1000 / FPS
```

The result is rounded to the nearest millisecond.

- Negative values move subtitles earlier.
- Positive values move subtitles later.
- `0` means no delay.

Frame-based input is only available in Mode 1. Other modes accept milliseconds only.

## Output

Processed subtitles are saved in an `output` folder next to the script.

For example, dropping:

```text
Movie/
├── English.sup
├── English.srt
└── Extra/
    └── French.sup
```

Produces:

```text
output/
└── Movie/
    ├── English.sup
    ├── English.srt
    └── Extra/
        └── French.sup
```

The original directory structure is preserved.

## Processing Details

- **SUP (PGS):** Synchronization is handled by SupMover.
- **SRT:** Timestamps are adjusted directly by the script.

## Notes

- Supported formats: `.sup` and `.srt`.
- Subfolders are scanned recursively.
- Existing `output` folders and directories ending in `_synced` are excluded from scanning.
- Original files remain unchanged.
- Processing continues if an individual file encounters an error.

## License

No license specified.
