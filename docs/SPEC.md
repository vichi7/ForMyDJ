# ForMyDJ Spec

## Product Intent

ForMyDJ is a personal DJ and A&R music intake tool. It should make it fast to take an authorized SoundCloud or YouTube link, produce a clean local audio file, inspect basic quality warnings, and move the file into a DJ-friendly folder structure.

The first version is not a full review dashboard. It is a downloader/converter with reliable audio handling.

## Locked Requirements

- Runs locally on macOS.
- Easy desktop workflow.
- One link submitted at a time.
- Multiple submitted links can process concurrently.
- Download starts immediately after submission.
- User chooses output format per job: WAV, AIFF, or MP3.
- Prefer original platform-provided WAV/AIFF if exposed.
- Fall back to best available stream when original file is not exposed.
- WAV/AIFF output: 44.1 kHz, 16-bit, stereo.
- No loudness normalization.
- No EQ, compression, or creative processing.
- Trim only leading/trailing digital silence.
- Warn about likely quality issues without modifying extra audio characteristics.
- Extract title, artist/uploader, album/release info when available, genre, mood, upload date, source platform, source URL, duration, cover art, and key if detected.
- Exclude follower count, likes, plays, and comments.
- Save as `Song Title - Artist`.
- Group output files by artist folder.
- Clean unsafe filename characters.
- Embed metadata where supported.
- Save source URL and technical report as sidecar metadata.
- Download cover art.
- Keep completed files available offline.
- Delete temporary source files after successful conversion.
- Show visual failure notifications.
- Retry failed jobs in the background.
- Reject or warn on tracks over 20 minutes.
- Reveal completed file in Finder.
- Prioritize Finder and Rekordbox-friendly file organization.

## Audio Truths

Converting MP3 or another lossy source to WAV/AIFF does not improve audio quality. It only creates a lossless container around audio that has already lost information. WAV/AIFF can still be useful for DJ playback compatibility, editing workflows, and avoiding further generation loss, but it will not restore detail removed by MP3, Opus, AAC, or a platform transcode.

Best quality behavior should be:

1. Download original WAV/AIFF if officially exposed.
2. Otherwise download the highest-quality available stream.
3. Warn when a WAV/AIFF output is sourced from lossy audio.
4. Avoid re-encoding unless the user-selected format requires it.

## Platform Handling

### SoundCloud

Use `yt-dlp` initially. It supports SoundCloud extraction and can obtain available audio streams and metadata for many public SoundCloud links. If a track has an official downloadable original file exposed by SoundCloud and accessible to the user, the app should prefer that original.

The app should not attempt to bypass SoundCloud Go+, paywalls, DRM, or account-gated access. Private/link-only access can be considered later only when it uses normal user-authorized access.

### YouTube

Use `yt-dlp` initially for YouTube videos, YouTube Music links, playlists only if added later, Shorts only if explicitly accepted as regular videos, and unlisted videos when accessible.

YouTube does not usually expose original uploaded WAV/AIFF files. Most YouTube downloads will be best-available streamed audio converted to the selected output format. The app should warn when lossless output is created from a lossy YouTube stream.

### Future Sources

Future adapters can support Bandcamp, Dropbox, direct audio links, Audiomack, Instagram, TikTok, and other sources. Each source should declare whether it can provide original files or only streamed/transcoded audio.

## Quality Report

Each job should produce a small report:

- Source URL
- Platform
- Extracted title
- Extracted artist/uploader
- Output filename
- Output format
- Source codec
- Source bitrate when available
- Output sample rate
- Output bit depth
- Channel layout
- Duration
- Leading/trailing silence trimmed
- Whether output is original file or converted fallback
- Whether source appears lossy
- Warnings

## Key Detection

Musical key detection is useful, but should be treated as analysis metadata, not guaranteed truth. It can be added after the downloader/converter path is reliable.

Potential implementation options:

- Use an audio analysis library such as Essentia if available.
- Call an external key-detection tool if it is stable on macOS.
- Defer to Rekordbox for key detection in the earliest version.

## Architecture Direction

Recommended first implementation:

- Native macOS shell: SwiftUI app.
- Downloader engine: `yt-dlp`.
- Audio engine: `ffmpeg` and `ffprobe`.
- Job queue: local app-managed queue.
- Storage: local SQLite database for job history and metadata.
- Files: user-selected output directory with artist subfolders.

GPU acceleration is not materially useful for this workflow. Audio download, demuxing, resampling, silence trim, and WAV/AIFF encoding are CPU-bound but lightweight compared with video processing. Battery life is best protected by avoiding unnecessary video downloads, avoiding needless re-encodes, limiting background analysis, and using efficient native macOS process execution.

## Failure Behavior

If a job fails:

- Show the job as failed in the UI.
- Keep the source URL visible.
- Show the best human-readable reason available.
- Retry automatically a limited number of times.
- Do not save broken partial output as a finished track.
- Clean temporary files.

## Open Questions

1. Should MP3 output use 320 kbps CBR, high-quality VBR, or a selectable bitrate?
2. Should the app process unlimited jobs concurrently, or use a small default such as 2-3 active jobs to protect battery and avoid platform throttling?
3. Should tracks over 20 minutes be blocked, or downloaded with a warning and manual confirmation?
4. Should key detection be built into version one, or should version one rely on Rekordbox for key/BPM analysis?
5. Should waveform preview be part of version one, or come after the core download/conversion path is proven?
6. Should the first app be pure SwiftUI, or a local web UI wrapped in a lightweight macOS shell?

