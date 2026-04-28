# ForMyDJ

ForMyDJ is a local macOS app for turning authorized music links and audio files into clean, DJ-library-ready files.

Paste a SoundCloud or YouTube link, choose WAV, AIFF, or MP3, pick an output folder, and ForMyDJ downloads, converts, tags, warns about common quality issues, and saves the finished track locally. You can also drag in local audio files for conversion and metadata cleanup.

This project is for music you are authorized to access. It does not bypass DRM, paywalls, private accounts, or platform restrictions.

## What It Does

- Downloads one SoundCloud or YouTube link at a time with `yt-dlp`.
- Processes up to 3 active jobs while keeping an unlimited queue.
- Converts output to WAV, AIFF, or 320 kbps MP3 with `ffmpeg`.
- Standardizes WAV/AIFF output to 44.1 kHz, 16-bit, stereo.
- Trims leading and trailing digital silence.
- Preserves useful metadata and writes clean filenames as `Song Title - Artist`.
- Warns when lossless output is created from a lossy source.
- Warns about long tracks, mono audio, low-bitrate sources, and incomplete metadata.
- Estimates musical key locally as helpful metadata, not guaranteed truth.
- Stores compact processing metadata under `~/Library/Application Support/ForMyDJ`.

## Requirements

- macOS 12 or newer.
- Python 3.9 through 3.12.
- Xcode Command Line Tools, for building the desktop wrapper.
- Homebrew packages: `ffmpeg` and `yt-dlp`.

Install the system tools:

```bash
xcode-select --install
brew install ffmpeg yt-dlp
```

If you do not have Homebrew yet, install it from [brew.sh](https://brew.sh/) first.

## Install And Run

Clone the repo:

```bash
git clone https://github.com/vichi7/ForMyDJ.git
cd ForMyDJ
```

Build the double-clickable macOS app:

```bash
./scripts/build-macos-app.sh
```

Open it:

```bash
open dist/ForMyDJ.app
```

The app starts a local engine at `http://127.0.0.1:8765` inside its own window. Finished files are saved to the selected output folder.

## Browser Mode

You can also run the same local app in a browser without building the macOS wrapper:

```bash
./scripts/run-local.sh
```

Then open:

```text
http://127.0.0.1:8765
```

## How To Use

1. Choose an output folder.
2. Pick an output format: WAV, AIFF, or MP3.
3. Paste a SoundCloud or YouTube link and press Download.
4. Or drag local audio files into the drop zone.
5. Watch the queue for progress, warnings, errors, and finished file paths.

ForMyDJ saves completed audio directly in the selected folder. It keeps temporary working files out of the repo and removes temporary download files after conversion.

## Quality Notes

ForMyDJ can convert a lossy source such as YouTube Opus/AAC or MP3 into WAV or AIFF, but that does not restore lost audio detail. It only places the already-lossy audio into a lossless container. The app warns when this happens so you can decide whether the file is good enough for your DJ workflow.

The best available path is:

1. Use the original WAV/AIFF if the platform officially exposes it.
2. Otherwise use the best available audio stream.
3. Convert only when the chosen output format requires it.

## Project Structure

```text
app/
  server.py          Local Python download/conversion engine
  desktop.py         Python desktop helper
  static/            Browser UI used by both browser mode and the macOS wrapper
scripts/
  build-macos-app.sh Build the WebKit-based macOS app wrapper
  run-local.sh       Run the local browser app
Sources/ForMyDJ/     Experimental native SwiftUI implementation
docs/SPEC.md         Product and technical spec
```

The supported runnable app today is the local Python engine plus the WebKit/browser UI. The SwiftUI source is kept in the repo as an experimental native direction.

## Development

Run locally:

```bash
./scripts/run-local.sh
```

Check Python syntax:

```bash
python3 -m py_compile app/server.py app/desktop.py
```

Build the macOS wrapper:

```bash
./scripts/build-macos-app.sh
```

Generated files such as `dist/`, `.build/`, `DerivedData/`, `__pycache__/`, logs, and `.DS_Store` are ignored by Git.

## Contributing

Issues and pull requests are welcome. Useful contributions include:

- More reliable source adapters.
- Better metadata extraction and tagging.
- Clearer quality warnings.
- UI improvements that keep the workflow fast.
- Tests around filename cleanup, warning generation, metadata reports, and job behavior.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow.

## License

ForMyDJ is open source under the [MIT License](LICENSE).
