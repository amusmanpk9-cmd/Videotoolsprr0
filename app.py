from pathlib import Path
from uuid import uuid4
import shutil
import subprocess
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
WORK = BASE / "work"
WORK.mkdir(exist_ok=True)

app = FastAPI(title="VideoTools Pro")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

MAX_UPLOAD = 500 * 1024 * 1024  # 500 MB starter limit
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mp3", ".wav", ".m4a"}


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def run_ffmpeg(args):
    if not ffmpeg_available():
        raise HTTPException(500, "FFmpeg is not installed on the server.")
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
            capture_output=True, text=True, timeout=900
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Processing took too long. Try a smaller video.")
    if result.returncode != 0:
        raise HTTPException(400, "Could not process this file. Check that it is a valid media file.")
    return result


async def save_upload(upload: UploadFile, folder: Path) -> Path:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Unsupported file type.")
    dest = folder / f"input{suffix}"
    size = 0
    with dest.open("wb") as out:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD:
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "File is larger than the 500 MB starter limit.")
            out.write(chunk)
    if size == 0:
        raise HTTPException(400, "The uploaded file is empty.")
    return dest


@app.get("/", response_class=HTMLResponse)
def home():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/api/status")
def status():
    return {"ok": True, "ffmpeg": ffmpeg_available()}


@app.post("/api/convert")
async def convert(file: UploadFile = File(...), output_format: str = Form("mp4")):
    fmt = output_format.lower()
    if fmt not in {"mp4", "mov", "webm", "avi", "mp3"}:
        raise HTTPException(400, "Choose MP4, MOV, WEBM, AVI, or MP3.")
    job = WORK / uuid4().hex
    job.mkdir()
    try:
        src = await save_upload(file, job)
        out = job / f"converted.{fmt}"
        if fmt == "mp3":
            args = ["-i", str(src), "-vn", "-codec:a", "libmp3lame", "-q:a", "2", str(out)]
        elif fmt == "webm":
            args = ["-i", str(src), "-c:v", "libvpx-vp9", "-c:a", "libopus", str(out)]
        elif fmt == "avi":
            args = ["-i", str(src), "-c:v", "mpeg4", "-q:v", "5", "-c:a", "mp3", str(out)]
        else:
            args = ["-i", str(src), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "23", "-c:a", "aac", "-movflags", "+faststart", str(out)]
        run_ffmpeg(args)
        return FileResponse(out, filename=out.name, media_type="application/octet-stream",
                            background=None)
    finally:
        # Keep output alive for FileResponse; production should use managed job storage and cleanup.
        pass


@app.post("/api/compress")
async def compress(file: UploadFile = File(...), quality: str = Form("balanced")):
    crf = {"high": "28", "balanced": "25", "best": "21"}.get(quality)
    if not crf:
        raise HTTPException(400, "Invalid quality option.")
    job = WORK / uuid4().hex
    job.mkdir()
    src = await save_upload(file, job)
    out = job / "compressed.mp4"
    run_ffmpeg(["-i", str(src), "-c:v", "libx264", "-preset", "veryfast",
                "-crf", crf, "-c:a", "aac", "-b:a", "128k", "-movflags",
                "+faststart", str(out)])
    return FileResponse(out, filename=out.name, media_type="application/octet-stream")


@app.post("/api/audio")
async def extract_audio(file: UploadFile = File(...)):
    job = WORK / uuid4().hex
    job.mkdir()
    src = await save_upload(file, job)
    out = job / "audio.mp3"
    run_ffmpeg(["-i", str(src), "-vn", "-codec:a", "libmp3lame", "-q:a", "2", str(out)])
    return FileResponse(out, filename=out.name, media_type="audio/mpeg")


@app.post("/api/trim")
async def trim_video(file: UploadFile = File(...), start: str = Form("0"), duration: str = Form("10")):
    try:
        start_value, duration_value = float(start), float(duration)
    except ValueError:
        raise HTTPException(400, "Start and duration must be numbers.")
    if start_value < 0 or duration_value <= 0 or duration_value > 3600:
        raise HTTPException(400, "Use a start of 0 or more and duration between 0 and 3600 seconds.")
    job = WORK / uuid4().hex
    job.mkdir()
    src = await save_upload(file, job)
    out = job / "trimmed.mp4"
    run_ffmpeg(["-ss", str(start_value), "-i", str(src), "-t", str(duration_value),
                "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", str(out)])
    return FileResponse(out, filename=out.name, media_type="application/octet-stream")


@app.post("/api/youtube-link")
def youtube_link(url: str = Form(...)):
    # Deliberately do not scrape or download YouTube media.
    if "youtube.com/" not in url and "youtu.be/" not in url:
        raise HTTPException(400, "Enter a valid YouTube watch or short link.")
    return {
        "message": (
            "YouTube links are recognized, but this starter does not download videos from YouTube. "
            "Use YouTube's official download/offline options, or an authorized provider/API that "
            "explicitly permits downloading. You can then upload the permitted video file here "
            "for conversion or compression."
        )
    }


@app.post("/api/social-link")
def social_link(url: str = Form(...), platform: str = Form(...)):
    # Recognize supported social-video URL domains without scraping or bypassing
    # platform restrictions. Actual importing must use an authorized provider/API.
    from urllib.parse import urlparse
    allowed = {
        "facebook": {"facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch"},
        "dailymotion": {"dailymotion.com", "www.dailymotion.com", "dai.ly"},
    }
    if platform not in allowed:
        raise HTTPException(400, "Choose Facebook or Dailymotion.")
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in allowed[platform]:
        raise HTTPException(400, f"Enter a valid {platform.title()} video link.")
    return {
        "message": (
            f"{platform.title()} link recognized. This starter does not scrape the platform, "
            "remove login requirements, or bypass download restrictions. For videos you own or "
            "are authorized to download, use the platform's official download/export feature "
            "or an authorized provider/API that supplies the media file. Then upload that file "
            "to VideoTools Pro to convert, compress, trim, or extract audio."
        )
    }
