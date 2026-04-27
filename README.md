# ForMyDJ

ForMyDJ is a local-first macOS DJ/A&R utility for downloading authorized music links from SoundCloud, YouTube, and future music sources into clean DJ-library files.

The first version prioritizes audio handling over UI polish:

- Paste one link at a time.
- Drag and drop local audio files.
- Start downloading immediately.
- Allow unlimited jobs to process in parallel.
- Prefer the original uploaded WAV/AIFF when a platform exposes it.
- Fall back to the best available audio stream and convert to the selected output format.
- Export WAV, AIFF, or MP3.
- Use 320 kbps CBR for MP3 output.
- Standardize output to 44.1 kHz, 16-bit stereo for WAV/AIFF.
- Trim leading/trailing digital silence only.
- Preserve and extract useful metadata.
- Save files as `Song Title - Artist` inside artist folders.
- Keep converted files available offline after a successful download.
- Delete temporary source files after conversion.

This project is intended for private/local use with music the user is authorized to access. It should not bypass DRM, paywalls, or platform restrictions.

## Local Tooling

The current Mac already has:

- `ffmpeg` 8.0.1
- `yt-dlp` 2026.03.17
- GitHub CLI authenticated as `vichi7`

## First Build Target

The first practical build should be a macOS-first local app with a minimal music-library interface:

1. Link input
2. Local audio drag/drop import
3. Output format selector: WAV, AIFF, MP3
4. Destination folder picker
5. Job queue with progress and retry status
6. Finished-file action: reveal in Finder
7. Alerts for low-quality source, lossy-to-lossless conversion, clipping, mono audio, missing metadata, failed download, or duration over 20 minutes

See [docs/SPEC.md](docs/SPEC.md) for the product and technical spec.

## Run The Local App

The desktop version runs without third-party Python packages.

Build the double-clickable macOS app:

```bash
scripts/build-macos-app.sh
```

Then open:

```text
dist/ForMyDJ.app
```

The desktop app opens a ForMyDJ window with the embedded local UI. It starts the local audio engine internally, so you do not need to run a terminal command after opening the app.

The browser version is still available for drag/drop testing:

```bash
scripts/run-local.sh
```

Then open:

```text
http://127.0.0.1:8765
```

The app uses 3 active processing workers with an unlimited queue. It saves finished audio files to the selected output folder and stores compact job metadata under `~/Library/Application Support/ForMyDJ`.

## Current Implementation Note

The repo includes a native SwiftUI app source under `Sources/ForMyDJ`, but this Mac's current Command Line Tools installation has a Swift compiler/SDK mismatch, so the Swift app cannot be verified locally until Xcode or matching Command Line Tools are installed.

The working implementation is currently the local Python server in `app/server.py` with the UI in `app/static/`.
