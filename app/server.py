#!/usr/bin/env python3
import cgi
import gzip
import json
import math
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DEFAULT_OUTPUT = Path.home() / "Downloads" / "ForMyDJ"
CACHE_DIR = Path.home() / "Library" / "Application Support" / "ForMyDJ"
ACTIVE_METADATA = CACHE_DIR / "metadata-active.jsonl"
MAX_ACTIVE_JOBS = 3
MAX_KEY_SECONDS = 300
KEY_SAMPLE_RATE = 11025

jobs_lock = threading.Lock()
jobs = {}
executor = ThreadPoolExecutor(max_workers=MAX_ACTIVE_JOBS)


def tool(name):
    for candidate in (
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/usr/bin/{name}",
        f"/bin/{name}",
    ):
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError(f"{name} was not found. Install it with Homebrew.")


FFMPEG = tool("ffmpeg")
FFPROBE = tool("ffprobe")
YTDLP = tool("yt-dlp")
GZIP = tool("gzip")


def run(cmd):
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"{cmd[0]} failed")
    return result


def update_job(job_id, **changes):
    with jobs_lock:
        jobs[job_id].update(changes)
        jobs[job_id]["updated_at"] = time.time()


def public_jobs():
    with jobs_lock:
        return sorted(jobs.values(), key=lambda item: item["created_at"], reverse=True)


def sanitize(value, fallback="Unknown"):
    value = re.sub(r'[\/\\?%*|"<>:]', "", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value or fallback


def unique_path(folder, stem, suffix):
    candidate = folder / f"{stem}.{suffix}"
    index = 2
    while candidate.exists():
        candidate = folder / f"{stem} {index}.{suffix}"
        index += 1
    return candidate


def parse_title_artist(name):
    for sep in (" - ", " – ", " — "):
        if sep in name:
            left, right = name.split(sep, 1)
            return left.strip(), right.strip()
    return name.strip(), None


def ffprobe(path):
    result = run([
        FFPROBE,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ])
    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    fmt = data.get("format", {})
    return {
        "duration": float(fmt["duration"]) if fmt.get("duration") else None,
        "codec": audio.get("codec_name"),
        "bitrate": int(audio.get("bit_rate") or fmt.get("bit_rate") or 0) or None,
        "channel_layout": audio.get("channel_layout"),
        "sample_rate": int(audio.get("sample_rate") or 0) or None,
    }


def metadata_from_info(info_path, audio_path, source_url=None):
    info = {}
    if info_path and Path(info_path).exists():
        info = json.loads(Path(info_path).read_text())

    probe = ffprobe(audio_path)
    filename_title, filename_artist = parse_title_artist(Path(audio_path).stem)
    codec = (probe.get("codec") or "").lower()
    lossy_codecs = {"mp3", "aac", "opus", "vorbis", "m4a"}

    artist = info.get("artist") or info.get("creator") or info.get("uploader") or filename_artist
    return {
        "title": info.get("title") or filename_title,
        "artist": artist,
        "album": info.get("album"),
        "genre": info.get("genre"),
        "mood": info.get("mood"),
        "uploader": info.get("uploader"),
        "upload_date": info.get("upload_date"),
        "source_url": info.get("webpage_url") or info.get("original_url") or source_url,
        "platform": info.get("extractor_key") or (urlparse(source_url).netloc if source_url else "Local"),
        "duration": probe.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "source_codec": probe.get("codec"),
        "source_bitrate": probe.get("bitrate"),
        "channel_layout": probe.get("channel_layout"),
        "sample_rate": probe.get("sample_rate"),
        "is_lossy": codec in lossy_codecs,
    }


def warnings_for(metadata, output_format):
    warnings = []
    if metadata.get("duration") and metadata["duration"] > 20 * 60:
        warnings.append("Track is over 20 minutes")
    if metadata.get("is_lossy") and output_format in {"wav", "aiff"}:
        warnings.append(f"{output_format.upper()} output is converted from a lossy source")
    if "mono" in (metadata.get("channel_layout") or "").lower():
        warnings.append("Source appears mono")
    if not metadata.get("title") or not metadata.get("artist"):
        warnings.append("Metadata is incomplete")
    bitrate = metadata.get("source_bitrate")
    if metadata.get("is_lossy") and bitrate and bitrate < 192000:
        warnings.append("Lossy source bitrate appears low")
    return warnings


def download_source(url, workdir):
    output_template = str(workdir / "source.%(ext)s")
    run([
        YTDLP,
        "--no-playlist",
        "--ignore-config",
        "-f", "ba/best",
        "--write-info-json",
        "--write-thumbnail",
        "-o", output_template,
        url,
    ])
    audio_candidates = [
        path for path in workdir.iterdir()
        if path.suffix.lower().lstrip(".") not in {"json", "jpg", "jpeg", "png", "webp", "part"}
    ]
    if not audio_candidates:
        raise RuntimeError("No downloadable audio file was produced.")
    info_path = next((path for path in workdir.iterdir() if path.name.endswith(".info.json")), None)
    return audio_candidates[0], info_path


def convert_audio(source_path, metadata, output_dir, output_format):
    artist = sanitize(metadata.get("artist") or metadata.get("uploader"), "Unknown Artist")
    title = sanitize(metadata.get("title") or Path(source_path).stem, "Unknown Title")
    artist_folder = Path(output_dir).expanduser() / artist
    artist_folder.mkdir(parents=True, exist_ok=True)
    output_path = unique_path(artist_folder, sanitize(f"{title} - {artist}"), output_format)

    args = [
        FFMPEG,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(source_path),
        "-vn",
        "-map_metadata", "0",
        "-ar", "44100",
        "-ac", "2",
        "-af", "silenceremove=start_periods=1:start_threshold=-90dB:stop_periods=1:stop_threshold=-90dB",
        "-metadata", f"title={title}",
        "-metadata", f"artist={artist}",
    ]

    if output_format == "wav":
        args += ["-sample_fmt", "s16", "-c:a", "pcm_s16le"]
    elif output_format == "aiff":
        args += ["-sample_fmt", "s16", "-c:a", "pcm_s16be", "-f", "aiff"]
    else:
        args += ["-c:a", "libmp3lame", "-b:a", "320k"]

    args.append(str(output_path))
    run(args)
    return output_path


def estimate_key(audio_path, workdir):
    raw_path = workdir / "keydetect.f32"
    run([
        FFMPEG,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(audio_path),
        "-t", str(MAX_KEY_SECONDS),
        "-ac", "1",
        "-ar", str(KEY_SAMPLE_RATE),
        "-f", "f32le",
        str(raw_path),
    ])
    data = raw_path.read_bytes()
    sample_count = len(data) // 4
    if sample_count < 4096:
        return None

    import array
    samples = array.array("f")
    samples.frombytes(data)
    if os.sys.byteorder != "little":
        samples.byteswap()

    frame_size = 4096
    hop = 4096
    chroma = [0.0] * 12
    for start in range(0, len(samples) - frame_size, hop):
        frame = samples[start:start + frame_size]
        rms = math.sqrt(sum(value * value for value in frame) / frame_size)
        if rms <= 0.01:
            continue
        for octave in range(2, 7):
            for note in range(12):
                midi = octave * 12 + note
                freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
                chroma[note] += goertzel(frame, freq)

    max_value = max(chroma) if chroma else 0
    if max_value <= 0:
        return None
    chroma = [value / max_value for value in chroma]
    return best_key(chroma)


def goertzel(frame, freq):
    omega = 2.0 * math.pi * freq / KEY_SAMPLE_RATE
    coeff = 2.0 * math.cos(omega)
    q0 = q1 = q2 = 0.0
    count = len(frame)
    for index, value in enumerate(frame):
        window = 0.5 - 0.5 * math.cos(2.0 * math.pi * index / (count - 1))
        q0 = coeff * q1 - q2 + value * window
        q2 = q1
        q1 = q0
    return math.sqrt(max(q1 * q1 + q2 * q2 - coeff * q1 * q2, 0.0))


def best_key(chroma):
    note_names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    major = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    minor = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
    best = (-999.0, "Unknown")
    for root in range(12):
        for label, profile in (("major", major), ("minor", minor)):
            rotated = [profile[(i - root) % 12] for i in range(12)]
            score = correlation(chroma, rotated)
            if score > best[0]:
                best = (score, f"{note_names[root]} {label}")
    return best[1]


def correlation(left, right):
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_power = sum((a - left_mean) ** 2 for a in left)
    right_power = sum((b - right_mean) ** 2 for b in right)
    return numerator / max(math.sqrt(left_power * right_power), 0.000001)


def append_metadata(report):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with ACTIVE_METADATA.open("a") as handle:
        handle.write(json.dumps(report, sort_keys=True) + "\n")
    with ACTIVE_METADATA.open() as handle:
        lines = sum(1 for _ in handle)
    if lines >= 50:
        archive = CACHE_DIR / f"metadata-{int(time.time())}.jsonl"
        ACTIVE_METADATA.rename(archive)
        with archive.open("rb") as source, gzip.open(f"{archive}.gz", "wb") as dest:
            shutil.copyfileobj(source, dest)
        archive.unlink(missing_ok=True)


def process_job(job_id):
    with jobs_lock:
        job = jobs[job_id]
        input_kind = job["input_kind"]
        input_value = job["input_value"]
        output_format = job["format"]
        output_dir = Path(job["output_dir"]).expanduser()

    workdir = Path(tempfile.mkdtemp(prefix=f"formydj-{job_id}-"))
    try:
        update_job(job_id, status="downloading", progress="Preparing source")
        if input_kind == "url":
            source_path, info_path = download_source(input_value, workdir)
            source_url = input_value
        else:
            source_path = Path(input_value)
            info_path = None
            source_url = None

        update_job(job_id, status="analyzing", progress="Reading metadata")
        metadata = metadata_from_info(info_path, source_path, source_url)
        update_job(
            job_id,
            title=metadata.get("title"),
            artist=metadata.get("artist") or metadata.get("uploader"),
            warnings=warnings_for(metadata, output_format),
        )

        key = None
        try:
            key = estimate_key(source_path, workdir)
        except Exception as exc:
            update_job(job_id, warnings=jobs[job_id].get("warnings", []) + [f"Key estimate failed: {exc}"])

        update_job(job_id, estimated_key=key, status="converting", progress=f"Writing {output_format.upper()}")
        output_path = convert_audio(source_path, metadata, output_dir, output_format)
        report = {
            "id": job_id,
            "created_at": job["created_at"],
            "input_kind": input_kind,
            "input_value": input_value,
            "output_path": str(output_path),
            "output_format": output_format,
            "metadata": metadata,
            "estimated_key": key,
            "warnings": jobs[job_id].get("warnings", []),
        }
        append_metadata(report)
        update_job(job_id, status="finished", progress="Done", output_path=str(output_path), report=report)
    except Exception as exc:
        update_job(job_id, status="failed", progress="Failed", error=str(exc))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def enqueue(input_kind, input_value, output_format, output_dir):
    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "created_at": time.time(),
            "created_at_display": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.time(),
            "input_kind": input_kind,
            "input_value": input_value,
            "format": output_format,
            "output_dir": output_dir,
            "status": "queued",
            "progress": "Waiting",
            "warnings": [],
        }
    executor.submit(process_job, job_id)
    return jobs[job_id]


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parsed = urlparse(path)
        if parsed.path == "/":
            return str(STATIC / "index.html")
        return str(STATIC / parsed.path.lstrip("/"))

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs":
            self.send_json({"jobs": public_jobs(), "default_output": str(DEFAULT_OUTPUT)})
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            link = (payload.get("link") or "").strip()
            output_format = (payload.get("format") or "wav").lower()
            output_dir = (payload.get("output_dir") or str(DEFAULT_OUTPUT)).strip()
            if not link:
                self.send_json({"error": "Missing link"}, 400)
                return
            self.send_json({"job": enqueue("url", link, output_format, output_dir)})
            return

        if parsed.path == "/api/upload":
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type"),
            })
            output_format = (form.getfirst("format") or "wav").lower()
            output_dir = (form.getfirst("output_dir") or str(DEFAULT_OUTPUT)).strip()
            file_item = form["file"] if "file" in form else None
            if file_item is None or not file_item.filename:
                self.send_json({"error": "Missing file"}, 400)
                return
            upload_dir = CACHE_DIR / "uploads" / uuid.uuid4().hex
            upload_dir.mkdir(parents=True, exist_ok=True)
            upload_path = upload_dir / sanitize(file_item.filename)
            with upload_path.open("wb") as handle:
                shutil.copyfileobj(file_item.file, handle)
            self.send_json({"job": enqueue("file", str(upload_path), output_format, output_dir)})
            return

        if parsed.path == "/api/cache/clear":
            shutil.rmtree(CACHE_DIR, ignore_errors=True)
            self.send_json({"ok": True})
            return

        self.send_json({"error": "Not found"}, 404)


def main():
    DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    url = "http://127.0.0.1:8765"
    print(f"ForMyDJ running at {url}")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
