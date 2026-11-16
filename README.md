# VideoTools Pro — starter website

A mobile-friendly video tools starter project with:
- Video upload and conversion using FFmpeg
- Video compression
- Extract audio to MP3
- Trim video by start time and duration
- A YouTube-link information panel for authorized/official workflows

## Important YouTube limitation
This project does **not** scrape YouTube or bypass download restrictions, DRM, or access controls.
A normal YouTube watch URL is not a direct media-file URL. Use YouTube's official download/offline
features, or only integrate a source/API that explicitly authorizes downloading and provides the
media file to your service. You can still use this website to process videos you own or are
authorized to download after obtaining the file through an allowed method.

## Requirements
- Python 3.10+
- FFmpeg installed and available on your PATH
- Internet hosting that supports a Python backend and FFmpeg (a static-only host is not enough)

## Run on a computer
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```
Open http://127.0.0.1:8000

## Run from an Android phone
For learning/testing, you can use a cloud coding environment that supports Python and background
processes. Upload this ZIP, install requirements, ensure FFmpeg is available, then run:
`uvicorn app:app --host 0.0.0.0 --port 8000`

## Production notes
Before publishing for real users, add authentication, rate limits, virus/malware scanning,
per-user storage quotas, HTTPS, job queues, automatic file deletion, and a proper privacy policy.
Large video processing needs a server with enough CPU, RAM, and disk space.


## Social video links
The interface also recognizes Facebook and Dailymotion URLs. It does not extract media from those sites or bypass login, privacy, DRM, or download restrictions. Use official export/download tools or an authorized provider/API for videos you have permission to download, then upload the resulting file for processing.
