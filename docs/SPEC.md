# ForMyDJ Spec

## Product Intent

ForMyDJ is an open-source desktop app for DJs, musicians, A&R scouts, producers, labels, and music curators who want a fast local workflow for authorized music intake.

The product promise is: **Listen to Music Globally**.

ForMyDJ should let a user open the app, paste an authorized SoundCloud, YouTube, or future supported music link, choose an output format, and download a clean local audio file without needing to understand command-line tools.

The product priorities are:

1. Audio quality clarity.
2. Clean organization.
3. Speed.
4. Cross-platform access.

ForMyDJ is not intended to bypass DRM, paywalls, account restrictions, or private content controls. This legal/use-positioning belongs in the GitHub README and docs, not as intrusive in-app warnings.

## Public Release Direction

- Open source project.
- Public GitHub repo remains the primary home.
- Distribution should be easy for normal users but does not require professional app-store style polish.
- No Apple notarization requirement.
- No Windows code-signing requirement.
- No hosted backend requirement.
- No telemetry requirement.
- No paid/proprietary edition planned.
- Releases are built manually by the maintainer.
- GitHub Releases can store downloadable builds, but the app and README should expose obvious download/update paths so users are not forced to understand the Releases page.

## Cross-Platform Direction

The long-term app should use one shared product/UI codebase with platform-specific packages:

- macOS: downloadable `.app` bundle or `.zip`.
- Windows: portable `.exe`/`.zip` first; installer optional later.
- Linux: AppImage or source-run support as best effort.

The preferred architecture direction is **Tauri plus bundled sidecar tools** because it keeps app size smaller than Electron, supports macOS/Windows/Linux packaging, and allows a web UI with native desktop access.

Each operating system may use the easiest package format for that platform, but the app should not become three separate product implementations unless there is a strong technical reason.

The current runnable implementation remains:

- Local Python server in `app/server.py`.
- Browser/WebKit UI in `app/static/`.
- macOS wrapper built by `scripts/build-macos-app.sh`.

The migration path should be incremental: keep the current app working while moving packaging/runtime toward the cross-platform direction.

## Bundled Tools

ForMyDJ should eventually bundle the tools needed to run:

- `ffmpeg`
- `ffprobe`
- `yt-dlp`

Reason: users should be able to download the app and use it without installing Homebrew, Python packages, or command-line dependencies manually.

The GitHub repo should explain why these tools are included:

- `yt-dlp` handles supported music/video source extraction.
- `ffmpeg` and `ffprobe` handle audio inspection, conversion, metadata, and encoding.
- Bundling avoids setup friction and makes behavior more consistent across operating systems.

Bundled tools should not be committed directly into source control. Release/build scripts should fetch pinned versions for each platform, verify checksums where practical, and include license notices.

Tool updates should be manual:

- User clicks an update button.
- App checks for available `yt-dlp`/tool updates.
- App shows what will be updated.
- User confirms.
- App updates the local bundled tool copy if possible.

The app should not silently update tools in the background.

## App Update Direction

The app should expose a clear update path:

- A visible "Check for Updates" or "Download Latest Version" action.
- It checks the latest GitHub release.
- It tells the user if their app is current or outdated.
- It downloads or opens the correct platform build.

Because the project does not require code signing/notarization, fully automatic self-replacement should be treated as optional and lower priority. The reliable open-source default is to download the newest build and guide the user to replace the old app.

## Locked Workflow Requirements

- Easy desktop workflow.
- One link submitted at a time.
- Multiple submitted links can process concurrently.
- Current processing policy: 3 active jobs with unlimited queued jobs.
- Local audio files can be dragged and dropped for metadata cleanup/conversion.
- Download starts immediately after submission.
- User chooses output format per job: WAV, AIFF, or MP3.
- MP3 output defaults to 320 kbps CBR.
- Prefer original platform-provided WAV/AIFF if exposed.
- Fall back to best available stream when original file is not exposed.
- WAV/AIFF output: 44.1 kHz, 16-bit, stereo.
- No loudness normalization.
- No EQ, compression, or creative processing.
- Trim only leading/trailing digital silence.
- Extract title, artist, album/release info when available, genre, mood, upload date, source platform, source URL, duration, cover art, and key if detected.
- If artist metadata is missing, use `Unknown Artist`. Do not fall back to uploader as artist.
- Exclude follower count, likes, plays, comments, and user comment metadata.
- Save output files directly in the selected output folder.
- Save filenames as `Song Title - Artist`.
- Do not create artist folders in the user's output folder.
- Clean unsafe filename characters.
- Embed metadata where supported.
- Download cover art when available.
- Keep completed files available offline.
- Delete temporary source files after successful conversion.
- Warn on likely quality issues without modifying extra audio characteristics.
- Warn on tracks over 20 minutes, but still allow download.
- Remember default output folder and output format between launches.
- Do not require a separate settings page unless the one-page UI becomes too crowded.

## Output Organization

User-facing downloads stay flat:

```text
Selected Output Folder/
  Song Title - Artist.wav
  Other Song - Unknown Artist.mp3
```

Artist organization should happen inside app metadata/history, not by adding extra folders to the user's downloads. The app can maintain an internal artist index so users can search or filter past downloads by artist.

Duplicates are allowed. If a duplicate filename exists, the app should create a unique filename such as:

```text
Song Title - Artist 2.wav
```

The app does not need to warn that a source URL was downloaded before.

## M3U Playlist Support

ForMyDJ should prioritize M3U over Rekordbox XML because M3U is simpler and broadly compatible with DJ/music software.

Requirements:

- Maintain one global playlist named `ForMyDJ Downloads.m3u`.
- Update the M3U automatically whenever a track finishes successfully.
- Store the M3U in the selected output folder unless a later design creates a better global location.
- Use file paths compatible with the current operating system.
- Keep output useful for Rekordbox, Serato, Traktor, VirtualDJ, Engine DJ, Ableton, and general music players.

Rekordbox XML is not a v1 requirement.

## Audio Truths

Converting MP3 or another lossy source to WAV/AIFF does not improve audio quality. It only creates a lossless container around audio that has already lost information. WAV/AIFF can still be useful for DJ playback compatibility, editing workflows, and avoiding further generation loss, but it will not restore detail removed by MP3, Opus, AAC, or a platform transcode.

Best quality behavior:

1. Download original WAV/AIFF if officially exposed.
2. Otherwise download the highest-quality available stream.
3. Warn when a WAV/AIFF output is sourced from lossy audio.
4. Avoid re-encoding unless the user-selected format requires it.

## Platform Handling

### SoundCloud

Use `yt-dlp` initially. It supports SoundCloud extraction and can obtain available audio streams and metadata for many public SoundCloud links. If a track has an official downloadable original file exposed by SoundCloud and accessible to the user, the app should prefer that original.

The app should not attempt to bypass SoundCloud Go+, paywalls, DRM, or account-gated access. Private/link-only access can be considered later only when it uses normal user-authorized access.

### YouTube

Use `yt-dlp` initially for YouTube videos, YouTube Music links, Shorts when accepted as regular videos, and unlisted videos when accessible.

YouTube does not usually expose original uploaded WAV/AIFF files. Most YouTube downloads will be best-available streamed audio converted to the selected output format. The app should warn when lossless output is created from a lossy YouTube stream.

### Future Sources

Future adapters can support Bandcamp, Dropbox, direct audio links, Audiomack, Instagram, TikTok, and other sources. Each source should declare whether it can provide original files or only streamed/transcoded audio.

## Key Detection

Key detection is an important feature because users may rely on it in Rekordbox and other DJ software.

Requirements:

- Include key detection.
- Treat detected key as strong app metadata, while still recognizing no automatic key detector is perfect.
- Embed detected key where supported by the output format and tagging library.
- Display detected key in the job row/history.
- Prefer an open-source engine rather than copying Rekordbox behavior.

Recommended efficient path:

1. Evaluate Essentia `KeyExtractor` for quality. It is a mature music analysis library with key extraction support, but its open license is AGPLv3 for non-commercial/open use, so the license impact must be accepted before bundling.
2. Evaluate `libkeyfinder`, used by Mixxx, for a DJ-oriented key detection path. It is GPLv3-or-later, so it also affects license compatibility.
3. Keep the current lightweight in-house detector only as a fallback or temporary bridge.

The project should document whichever key detection engine is selected, including license and binary/source availability.

## Reports And Error Handling

Success reports should not clutter the output folder by default.

Optimized report behavior:

- Store compact job metadata in app data.
- Maintain artist/source/history indexes for search and duplicate awareness.
- Only show report actions when an error happens.
- Provide a user-facing error popup after final failure.

On failure:

1. Retry automatically in the backend up to 3 times.
2. If the 4th attempt fails, stop retrying.
3. Show a clear popup explaining what failed and why, using the best human-readable reason available.
4. Offer:
   - `Open GitHub Issue`
   - `Copy Report`
   - `Dismiss`

`Open GitHub Issue` should open a browser with a prefilled GitHub issue when possible. Users without a GitHub account may not be able to submit the issue, so `Copy Report` is required as a fallback.

`Copy Report` copies a structured text report to the clipboard. The user can paste it into a GitHub issue, email, chat, or any support thread.

The report should include:

- App version
- Operating system
- Source URL or input filename
- Platform/extractor
- Output format
- Tool versions
- Error message
- Retry history
- Source codec/bitrate if known
- Output path if created
- Relevant warnings

No anonymous direct report submission is planned because that would require a hosted backend or embedded GitHub credentials.

## Quality Report Data

Each completed job may store compact internal report data:

- Source URL
- Platform
- Extracted title
- Extracted artist
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
- Detected key
- Warnings

Future UI can expose this data in an advanced detail panel if needed.

## UI Direction

The app should remain a one-page workflow:

- Link input
- Format selector
- Output folder selector
- Download action
- Tool update action
- App update action
- Drag/drop audio input
- Job queue
- History/artist search area
- Automatic M3U status

The UI should be nicer and easier to understand than a raw developer tool, but it does not need enterprise-level polish.

Claude Code will redesign the app's look and feel for the best UI/UX experience before the public polished release.

## Architecture Direction

Near term:

- Keep the current Python/WebKit app functional.
- Add automatic M3U writing.
- Add retry policy.
- Add better error popups/report actions.
- Add artist/history metadata.
- Add tool update buttons.
- Improve key detection engine.

Cross-platform migration:

- Move toward Tauri for shared UI and platform-specific builds.
- Bundle platform-specific sidecar binaries for `yt-dlp`, `ffmpeg`, and `ffprobe`.
- Keep release build scripts manual and reproducible.
- Include license notices for bundled tools and key detection dependencies.

Storage:

- Compact local metadata store under each OS app-data directory.
- Track jobs, artists, source URLs, output files, warnings, and errors.
- Do not require cloud sync.

GPU acceleration is not materially useful for this workflow. Audio download, demuxing, resampling, silence trim, key estimation, and WAV/AIFF encoding are CPU-bound but manageable. Battery life is best protected by avoiding unnecessary video downloads, avoiding needless re-encodes, limiting background analysis, and using efficient native process execution.

## Open Questions

1. Should Tauri migration happen before or after M3U/retry/history improvements land in the current app?
2. Should `ForMyDJ Downloads.m3u` use absolute paths or relative paths?
3. Should the app write detected key into ID3 `TKEY`, common comment-free metadata fields, or both where supported?
4. Which key notation should display by default: standard (`C# minor`), Camelot (`12A`), Open Key, or multiple?
5. Should tool updates use stable `yt-dlp` releases only, or offer stable/nightly choices?
6. Should Windows/Linux support start as "run from source" before portable builds exist?
