import os
import sys
import glob
import json
import time
import shutil
import socket
import asyncio
import mimetypes
import subprocess
from datetime import datetime
from typing import Optional, List
from pathlib import Path

import uvicorn
import psutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

# --- Application Constants & Directories ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
CATEGORIES = {
    "videos": os.path.join(STORAGE_DIR, "videos"),
    "photos": os.path.join(STORAGE_DIR, "photos"),
    "audio": os.path.join(STORAGE_DIR, "audio"),
    "documents": os.path.join(STORAGE_DIR, "documents"),
    "files": os.path.join(STORAGE_DIR, "files"),
}
THUMBNAILS_DIR = os.path.join(STORAGE_DIR, "thumbnails")
STATIC_DIR = os.path.join(BASE_DIR, "static")
METADATA_FILE = os.path.join(STORAGE_DIR, "metadata.json")
CHANNELS_FILE = os.path.join(STORAGE_DIR, "channels.json")
HISTORY_FILE = os.path.join(STORAGE_DIR, "watch_history.json")
QUEUE_FILE = os.path.join(STORAGE_DIR, "playback_queue.json")

# Ensure all storage directories exist
for cat_path in CATEGORIES.values():
    os.makedirs(cat_path, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

def load_channels() -> list:
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_channels(channels: list):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=2, ensure_ascii=False)

def load_watch_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_watch_history(hist: dict):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)

def load_playback_queue() -> list:
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_playback_queue(q: list):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(q, f, indent=2, ensure_ascii=False)

# Extension mappings for automatic categorization
EXT_CATEGORIES = {
    # Videos
    ".mp4": "videos", ".webm": "videos", ".mkv": "videos", ".mov": "videos",
    ".avi": "videos", ".m4v": "videos", ".flv": "videos", ".wmv": "videos",
    # Photos
    ".jpg": "photos", ".jpeg": "photos", ".png": "photos", ".gif": "photos",
    ".webp": "photos", ".svg": "photos", ".bmp": "photos", ".heic": "photos",
    # Audio
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".flac": "audio",
    ".aac": "audio", ".ogg": "audio", ".opus": "audio", ".wma": "audio",
    # Documents
    ".pdf": "documents", ".doc": "documents", ".docx": "documents",
    ".xls": "documents", ".xlsx": "documents", ".ppt": "documents",
    ".pptx": "documents", ".txt": "documents", ".csv": "documents",
    ".md": "documents", ".json": "documents"
}

# --- In-Memory Tasks Registry ---
ACTIVE_TASKS = {}

# --- FastAPI Initialization ---
app = FastAPI(title="JARVIS Glass Media Server & Cloud Drive", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Metadata Utilities ---
def load_metadata() -> dict:
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_metadata(meta: dict):
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

def update_file_meta(category: str, filename: str, details: dict):
    meta = load_metadata()
    key = f"{category}/{filename}"
    if key not in meta:
        meta[key] = {}
    meta[key].update(details)
    save_metadata(meta)

def remove_file_meta(category: str, filename: str):
    meta = load_metadata()
    key = f"{category}/{filename}"
    if key in meta:
        del meta[key]
        save_metadata(meta)

# --- System & Network Utilities ---
def get_local_ip() -> str:
    """Detects the machine's primary Wi-Fi or local LAN IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_storage_stats():
    """Returns disk usage for the drive holding storage/."""
    try:
        usage = shutil.disk_usage(STORAGE_DIR)
        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        pct = (usage.used / usage.total) * 100 if usage.total > 0 else 0
        return {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "used_percent": round(pct, 1)
        }
    except Exception:
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "used_percent": 0}

def get_hardware_metrics():
    """Fetches real-time CPU, RAM, battery, and uptime metrics."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        
        battery_data = None
        try:
            battery = psutil.sensors_battery()
            if battery:
                battery_data = {
                    "percent": round(battery.percent, 1),
                    "power_plugged": battery.power_plugged
                }
        except Exception:
            battery_data = None

        uptime_seconds = int(time.time() - psutil.boot_time())
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        uptime_formatted = f"{hours}h {minutes}m"

        return {
            "cpu_percent": round(cpu, 1),
            "ram_percent": round(ram.percent, 1),
            "ram_used_gb": round(ram.used / (1024 ** 3), 2),
            "ram_total_gb": round(ram.total / (1024 ** 3), 2),
            "battery": battery_data,
            "uptime": uptime_formatted
        }
    except Exception as e:
        return {"cpu_percent": 0, "ram_percent": 0, "battery": None, "uptime": "--"}

def format_size(bytes_size: int) -> str:
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"

def categorize_file(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return EXT_CATEGORIES.get(ext, "files")

def generate_video_thumbnail(video_path: str, thumbnail_name: str) -> Optional[str]:
    """Generates a JPEG thumbnail using ffmpeg from 2 seconds into the video."""
    target_thumb = os.path.join(THUMBNAILS_DIR, thumbnail_name)
    if os.path.exists(target_thumb):
        return thumbnail_name
    try:
        cmd = [
            "ffmpeg", "-y", "-ss", "00:00:02",
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "3",
            target_thumb
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        if res.returncode == 0 and os.path.exists(target_thumb):
            return thumbnail_name
    except Exception as e:
        print(f"Thumbnail generation error: {e}")
    return None

# --- Partial Content / Range Streamer ---
def stream_file_with_range(request: Request, file_path: str, content_type: str):
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("Range")

    if not range_header:
        def full_iter():
            with open(file_path, "rb") as f:
                while chunk := f.read(1024 * 512):
                    yield chunk
        headers = {
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Type": content_type
        }
        return StreamingResponse(full_iter(), headers=headers)

    try:
        range_val = range_header.replace("bytes=", "").strip()
        parts = range_val.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
        end = min(end, file_size - 1)
        if start > end or start >= file_size:
            raise HTTPException(status_code=416, detail="Requested range not satisfiable")

        content_length = (end - start) + 1

        def range_iter(s_pos, e_pos):
            with open(file_path, "rb") as f:
                f.seek(s_pos)
                bytes_left = (e_pos - s_pos) + 1
                while bytes_left > 0:
                    read_size = min(1024 * 512, bytes_left)
                    data = f.read(read_size)
                    if not data:
                        break
                    bytes_left -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": content_type,
        }
        return StreamingResponse(range_iter(start, end), status_code=206, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=416, detail=str(e))

# --- API Endpoints ---

@app.get("/api/info")
async def get_system_info():
    """Returns local network details, hardware metrics, and storage stats."""
    local_ip = get_local_ip()
    stats = get_storage_stats()
    metrics = get_hardware_metrics()
    
    category_counts = {}
    total_files = 0
    for cat, cat_dir in CATEGORIES.items():
        count = len([f for f in os.listdir(cat_dir) if os.path.isfile(os.path.join(cat_dir, f))])
        category_counts[cat] = count
        total_files += count

    return {
        "hostname": socket.gethostname(),
        "local_ip": local_ip,
        "port": 8000,
        "access_url": f"http://{local_ip}:8000",
        "storage": stats,
        "metrics": metrics,
        "counts": category_counts,
        "total_files": total_files
    }

@app.get("/api/metrics")
async def get_live_metrics():
    """Fast polling endpoint for real-time CPU, RAM, and Battery."""
    return get_hardware_metrics()

# --- PC Remote Power Management ---
@app.post("/api/power/shutdown")
async def trigger_shutdown(delay: int = Form(30)):
    """
    Schedules Windows shutdown.
    Default delay is 30 seconds to allow cancellation if needed.
    Pass delay=0 for instant shutdown.
    """
    try:
        cmd = ["shutdown", "/s", "/t", str(delay), "/c", "JARVIS Remote Web Command: PC Shutting Down"]
        subprocess.run(cmd, check=True)
        return {
            "status": "success",
            "message": f"PC Shutdown initiated ({delay} seconds remaining).",
            "delay": delay
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate shutdown: {e}")

@app.post("/api/power/restart")
async def trigger_restart(delay: int = Form(10)):
    """Schedules PC Restart."""
    try:
        cmd = ["shutdown", "/r", "/t", str(delay), "/c", "JARVIS Remote Web Command: PC Restarting"]
        subprocess.run(cmd, check=True)
        return {
            "status": "success",
            "message": f"PC Restart initiated ({delay} seconds remaining).",
            "delay": delay
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate restart: {e}")

@app.post("/api/power/cancel")
async def cancel_power_action():
    """Cancels any pending Windows shutdown or restart timer."""
    try:
        subprocess.run(["shutdown", "/a"], check=True)
        return {"status": "success", "message": "Pending shutdown/restart was successfully canceled."}
    except Exception as e:
        return {"status": "info", "message": "No scheduled shutdown was active to cancel."}

@app.post("/api/power/lock")
async def lock_workstation():
    """Immediately locks the Windows desktop screen."""
    try:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return {"status": "success", "message": "PC Locked."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to lock workstation: {e}")

@app.post("/api/power/sleep")
async def trigger_sleep():
    """Puts Windows PC into Sleep / Standby."""
    try:
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return {"status": "success", "message": "PC entering sleep mode."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sleep PC: {e}")

# --- File Library Endpoints ---
@app.get("/api/files")
async def list_files(
    category: Optional[str] = None,
    q: Optional[str] = None,
    sort_by: Optional[str] = "date_desc"
):
    metadata = load_metadata()
    watch_history = load_watch_history()
    results = []

    target_cats = [category] if category and category in CATEGORIES else list(CATEGORIES.keys())

    for cat in target_cats:
        cat_dir = CATEGORIES[cat]
        if not os.path.exists(cat_dir):
            continue

        for filename in os.listdir(cat_dir):
            file_path = os.path.join(cat_dir, filename)
            if not os.path.isfile(file_path):
                continue

            stat = os.stat(file_path)
            file_size = stat.st_size
            mod_time = stat.st_mtime
            ext = os.path.splitext(filename)[1].lower()

            if cat == "videos" and ext not in [".mp4", ".webm", ".mkv", ".mov", ".avi", ".m4v", ".flv", ".wmv"]:
                continue
            if cat == "audio" and ext not in [".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".opus", ".wma"]:
                continue
            if cat == "photos" and ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".heic", ".heif"]:
                continue

            meta_key = f"{cat}/{filename}"
            meta_entry = metadata.get(meta_key, {})
            title = meta_entry.get("title", filename)

            if q:
                keyword = q.lower()
                if keyword not in filename.lower() and keyword not in title.lower():
                    continue

            thumb_url = None
            if cat == "videos":
                thumb_filename = f"{filename}.jpg"
                if os.path.exists(os.path.join(THUMBNAILS_DIR, thumb_filename)):
                    thumb_url = f"/api/thumbnails/{thumb_filename}"
                else:
                    yt_id = meta_entry.get("youtube_id")
                    if yt_id:
                        thumb_url = f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg"
                    elif meta_entry.get("thumbnail_url"):
                        thumb_url = meta_entry["thumbnail_url"]
            elif cat == "photos":
                thumb_url = f"/api/stream/{cat}/{filename}"

            results.append({
                "filename": filename,
                "title": title,
                "category": cat,
                "extension": ext,
                "size_bytes": file_size,
                "size_formatted": format_size(file_size),
                "modified_timestamp": mod_time,
                "modified_date": datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M"),
                "thumbnail_url": thumb_url,
                "stream_url": f"/api/stream/{cat}/{filename}",
                "download_url": f"/api/download/{cat}/{filename}",
                "youtube_id": meta_entry.get("youtube_id"),
                "uploader": meta_entry.get("uploader"),
                "duration": meta_entry.get("duration"),
                "watch_progress": watch_history.get(meta_key)
            })

    if sort_by == "date_asc":
        results.sort(key=lambda x: x["modified_timestamp"])
    elif sort_by == "name_asc":
        results.sort(key=lambda x: x["title"].lower())
    elif sort_by == "name_desc":
        results.sort(key=lambda x: x["title"].lower(), reverse=True)
    elif sort_by == "size_desc":
        results.sort(key=lambda x: x["size_bytes"], reverse=True)
    elif sort_by == "size_asc":
        results.sort(key=lambda x: x["size_bytes"])
    else:
        results.sort(key=lambda x: x["modified_timestamp"], reverse=True)

    return {"files": results, "total": len(results)}

# --- Watch History & Continue Watching Endpoints ---
@app.get("/api/history")
async def get_watch_history():
    """Returns watch history sorted by last watched timestamp descending."""
    hist = load_watch_history()
    items = list(hist.values())
    items.sort(key=lambda x: x.get("last_watched", 0), reverse=True)
    return {"history": items}

@app.post("/api/history/update")
async def update_watch_history(
    category: str = Form("videos"),
    filename: str = Form(...),
    position_seconds: float = Form(...),
    duration_seconds: float = Form(...)
):
    """Saves playback progress and timestamp for continue watching."""
    hist = load_watch_history()
    key = f"{category}/{filename}"
    percent = round((position_seconds / duration_seconds) * 100, 1) if duration_seconds > 0 else 0
    completed = percent >= 92.0

    metadata = load_metadata().get(key, {})
    title = metadata.get("title", filename)
    thumb_url = f"/api/thumbnails/{filename}.jpg" if os.path.exists(os.path.join(THUMBNAILS_DIR, f"{filename}.jpg")) else metadata.get("thumbnail_url")

    hist[key] = {
        "key": key,
        "category": category,
        "filename": filename,
        "title": title,
        "thumbnail_url": thumb_url,
        "stream_url": f"/api/stream/{category}/{filename}",
        "download_url": f"/api/download/{category}/{filename}",
        "position_seconds": round(position_seconds, 1),
        "duration_seconds": round(duration_seconds, 1),
        "percent": percent,
        "completed": completed,
        "last_watched": time.time(),
        "last_watched_str": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    save_watch_history(hist)
    return {"status": "success", "entry": hist[key]}

@app.delete("/api/history/{category}/{filename}")
async def remove_history_item(category: str, filename: str):
    hist = load_watch_history()
    key = f"{category}/{filename}"
    if key in hist:
        del hist[key]
        save_watch_history(hist)
    return {"status": "success", "message": f"Removed from continue watching"}

@app.delete("/api/history")
async def clear_all_history():
    save_watch_history({})
    return {"status": "success", "message": "Watch history cleared"}

# --- Playback Queue Endpoints ---
@app.get("/api/queue")
async def get_playback_queue():
    """Returns the list of queued videos for continuous playback."""
    return {"queue": load_playback_queue()}

@app.post("/api/queue/add")
async def add_to_playback_queue(category: str = Form("videos"), filename: str = Form(...)):
    q = load_playback_queue()
    key = f"{category}/{filename}"
    if any(item.get("key") == key for item in q):
        return {"status": "info", "message": "Video is already in queue", "queue": q}

    metadata = load_metadata().get(key, {})
    title = metadata.get("title", filename)
    thumb_url = f"/api/thumbnails/{filename}.jpg" if os.path.exists(os.path.join(THUMBNAILS_DIR, f"{filename}.jpg")) else metadata.get("thumbnail_url")

    q.append({
        "key": key,
        "category": category,
        "filename": filename,
        "title": title,
        "thumbnail_url": thumb_url,
        "stream_url": f"/api/stream/{category}/{filename}",
        "download_url": f"/api/download/{category}/{filename}",
        "added_at": datetime.now().strftime("%H:%M:%S")
    })
    save_playback_queue(q)
    return {"status": "success", "message": f"Added '{title}' to queue", "queue": q}

@app.post("/api/queue/remove")
async def remove_from_playback_queue(key: str = Form(...)):
    q = load_playback_queue()
    q = [item for item in q if item.get("key") != key]
    save_playback_queue(q)
    return {"status": "success", "queue": q}

@app.post("/api/queue/clear")
async def clear_playback_queue():
    save_playback_queue([])
    return {"status": "success", "message": "Queue cleared"}

@app.post("/api/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    uploaded_items = []

    for file in files:
        filename = file.filename
        if not filename:
            continue

        clean_name = os.path.basename(filename)
        category = categorize_file(clean_name)
        cat_dir = CATEGORIES[category]

        dest_path = os.path.join(cat_dir, clean_name)
        base, ext = os.path.splitext(clean_name)
        counter = 1
        while os.path.exists(dest_path):
            clean_name = f"{base}_{counter}{ext}"
            dest_path = os.path.join(cat_dir, clean_name)
            counter += 1

        with open(dest_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):
                out_file.write(chunk)

        if category == "videos":
            thumb_name = f"{clean_name}.jpg"
            background_tasks.add_task(generate_video_thumbnail, dest_path, thumb_name)

        update_file_meta(category, clean_name, {
            "title": base.replace("_", " ").replace("-", " "),
            "uploaded_at": datetime.now().isoformat(),
            "source": "upload"
        })

        stat = os.stat(dest_path)
        uploaded_items.append({
            "filename": clean_name,
            "category": category,
            "size": format_size(stat.st_size),
            "stream_url": f"/api/stream/{category}/{clean_name}",
            "download_url": f"/api/download/{category}/{clean_name}"
        })

    return {
        "status": "success",
        "message": f"Successfully uploaded {len(uploaded_items)} file(s).",
        "items": uploaded_items
    }

@app.delete("/api/files/{category}/{filename}")
async def delete_file(category: str, filename: str):
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")

    clean_name = os.path.basename(filename)
    file_path = os.path.join(CATEGORIES[category], clean_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        os.remove(file_path)
        thumb_path = os.path.join(THUMBNAILS_DIR, f"{clean_name}.jpg")
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        remove_file_meta(category, clean_name)
        return {"status": "success", "message": f"Deleted {clean_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@app.get("/api/stream/{category}/{filename}")
async def stream_media_file(category: str, filename: str, request: Request):
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")

    clean_name = os.path.basename(filename)
    file_path = os.path.join(CATEGORIES[category], clean_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Media file not found")

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    return stream_file_with_range(request, file_path, mime_type)

@app.get("/api/download/{category}/{filename}")
async def download_media_file(category: str, filename: str):
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")

    clean_name = os.path.basename(filename)
    file_path = os.path.join(CATEGORIES[category], clean_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    return FileResponse(
        file_path,
        media_type=mime_type,
        filename=clean_name,
        headers={"Content-Disposition": f'attachment; filename="{clean_name}"'}
    )

@app.get("/api/thumbnails/{thumbnail_name}")
async def get_thumbnail(thumbnail_name: str):
    clean_name = os.path.basename(thumbnail_name)
    thumb_path = os.path.join(THUMBNAILS_DIR, clean_name)
    if not os.path.exists(thumb_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(thumb_path, media_type="image/jpeg")

# --- YouTube Scraper & Downloader Background Engine ---

def run_yt_download_task(task_id: str, url: str, quality: str, limit: int):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            pct = (downloaded / total * 100) if total > 0 else 0
            speed = d.get('speed') or 0
            eta = d.get('eta') or 0
            
            ACTIVE_TASKS[task_id].update({
                "status": "downloading",
                "progress": round(pct, 1),
                "speed": format_size(int(speed)) + "/s" if speed else "...",
                "eta": f"{eta}s" if eta else "...",
            })
        elif d['status'] == 'finished':
            ACTIVE_TASKS[task_id].update({
                "status": "processing",
                "progress": 98.0,
                "message": "Finalizing media format..."
            })

    if task_id not in ACTIVE_TASKS:
        ACTIVE_TASKS[task_id] = {
            "task_id": task_id,
            "url": url,
            "quality": quality,
            "limit": limit,
            "status": "queued",
            "progress": 0.0,
            "speed": "0 KB/s",
            "eta": "...",
            "message": "Initializing...",
            "started_at": datetime.now().strftime("%H:%M:%S")
        }

    try:
        ACTIVE_TASKS[task_id]["status"] = "analyzing"
        ACTIVE_TASKS[task_id]["message"] = "Fetching video information from YouTube..."

        if quality == "audio":
            format_spec = "bestaudio/best"
            target_cat = "audio"
            ext_out = "mp3"
        elif quality == "1080":
            format_spec = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]/best"
            target_cat = "videos"
            ext_out = "mp4"
        elif quality == "720":
            format_spec = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best"
            target_cat = "videos"
            ext_out = "mp4"
        elif quality == "480":
            format_spec = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best"
            target_cat = "videos"
            ext_out = "mp4"
        else:
            format_spec = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            target_cat = "videos"
            ext_out = "mp4"

        ydl_opts = {
            'format': format_spec,
            'outtmpl': os.path.join(CATEGORIES[target_cat], '%(title).150s_%(id)s.%(ext)s'),
            'merge_output_format': ext_out,
            'writethumbnail': True,
            'progress_hooks': [progress_hook],
            'playlistend': limit if limit > 0 else 1,
            'ignoreerrors': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'quiet': True,
            'no_warnings': True,
        }

        if quality == "audio":
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            entries = info.get('entries', [info]) if info else []

            count_downloaded = 0
            for entry in entries:
                if not entry:
                    continue
                v_id = entry.get('id', '')
                title = entry.get('title', 'Unknown Title')
                duration = entry.get('duration')
                uploader = entry.get('uploader')
                thumb_url = entry.get('thumbnail')

                search_pat = os.path.join(CATEGORIES[target_cat], f"*{v_id}.*")
                matches = glob.glob(search_pat)
                media_files = [m for m in matches if not m.endswith(('.jpg', '.webp', '.png'))]

                if media_files:
                    saved_path = media_files[0]
                    saved_name = os.path.basename(saved_path)

                    thumb_matches = [m for m in matches if m.endswith(('.jpg', '.webp', '.png'))]
                    if thumb_matches:
                        dest_thumb = os.path.join(THUMBNAILS_DIR, f"{saved_name}.jpg")
                        try:
                            subprocess.run(["ffmpeg", "-y", "-i", thumb_matches[0], dest_thumb],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            os.remove(thumb_matches[0])
                        except Exception:
                            pass
                    elif target_cat == "videos":
                        generate_video_thumbnail(saved_path, f"{saved_name}.jpg")

                    update_file_meta(target_cat, saved_name, {
                        "title": title,
                        "youtube_id": v_id,
                        "uploader": uploader,
                        "duration": duration,
                        "thumbnail_url": thumb_url,
                        "source_url": url,
                        "downloaded_at": datetime.now().isoformat()
                    })
                    count_downloaded += 1

        ACTIVE_TASKS[task_id].update({
            "status": "completed",
            "progress": 100.0,
            "message": f"Successfully processed {count_downloaded} media file(s)!"
        })

    except Exception as e:
        ACTIVE_TASKS[task_id].update({
            "status": "error",
            "message": str(e)
        })

@app.post("/api/youtube/scrape")
async def trigger_youtube_scrape(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    quality: str = Form("720"),
    limit: int = Form(5)
):
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    task_id = f"yt_{int(time.time() * 1000)}"
    ACTIVE_TASKS[task_id] = {
        "task_id": task_id,
        "url": url,
        "quality": quality,
        "limit": limit,
        "status": "queued",
        "progress": 0.0,
        "speed": "0 KB/s",
        "eta": "...",
        "message": "Task queued...",
        "started_at": datetime.now().strftime("%H:%M:%S")
    }

    background_tasks.add_task(run_yt_download_task, task_id, url, quality, limit)
    return {
        "status": "success",
        "task_id": task_id,
        "message": "Download task started in background."
    }

@app.get("/api/youtube/tasks")
async def get_youtube_tasks():
    return {"tasks": list(ACTIVE_TASKS.values())}

# --- Dynamic Channel Management & Recent 4 Videos Sync ---
@app.get("/api/channels")
async def get_all_channels():
    """Returns saved channels from storage/channels.json."""
    return {"channels": load_channels()}

@app.post("/api/channels")
async def add_new_channel(url: str = Form(...), name: Optional[str] = Form(None)):
    """Adds a new channel. Auto-detects channel name if omitted."""
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Channel URL is required")

    channel_name = name.strip() if name and name.strip() else None
    if not channel_name:
        try:
            ydl_opts = {
                'extract_flat': True,
                'playlistend': 1,
                'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
                'quiet': True,
                'no_warnings': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                channel_name = info.get('channel') or info.get('uploader') or info.get('title')
        except Exception:
            channel_name = "Custom Channel"

    if not channel_name:
        channel_name = "Custom Channel"

    channels = load_channels()
    for ch in channels:
        if ch.get("url", "").rstrip("/").lower() == url.rstrip("/").lower():
            return {"status": "info", "message": f"Channel '{ch.get('name')}' is already added.", "channel": ch}

    new_id = f"ch_{int(time.time() * 1000)}"
    new_channel = {
        "id": new_id,
        "name": channel_name,
        "url": url,
        "added_at": datetime.now().isoformat()
    }
    channels.append(new_channel)
    save_channels(channels)
    return {"status": "success", "message": f"Added channel '{channel_name}'", "channel": new_channel}

@app.delete("/api/channels/{channel_id}")
async def delete_channel(channel_id: str):
    channels = load_channels()
    filtered = [ch for ch in channels if ch.get("id") != channel_id]
    if len(filtered) == len(channels):
        raise HTTPException(status_code=404, detail="Channel not found")
    save_channels(filtered)
    return {"status": "success", "message": "Channel removed"}

@app.post("/api/channels/sync")
async def sync_channel_videos(
    background_tasks: BackgroundTasks,
    channel_id: Optional[str] = Form(None),
    limit: int = Form(4),
    quality: str = Form("720")
):
    """
    Syncs the most recent 4 videos from a specific channel or all saved channels.
    """
    channels = load_channels()
    if channel_id:
        targets = [ch for ch in channels if ch.get("id") == channel_id]
        if not targets:
            raise HTTPException(status_code=404, detail="Channel not found")
    else:
        targets = channels

    if not targets:
        raise HTTPException(status_code=400, detail="No channels found to sync")

    dispatched = []
    for ch in targets:
        task_id = f"sync_{ch['id']}_{int(time.time() * 1000)}"
        ACTIVE_TASKS[task_id] = {
            "task_id": task_id,
            "url": ch["url"],
            "channel_name": ch["name"],
            "quality": quality,
            "limit": limit,
            "status": "queued",
            "progress": 0.0,
            "speed": "0 KB/s",
            "eta": "...",
            "message": f"Syncing recent {limit} videos from {ch['name']}...",
            "started_at": datetime.now().strftime("%H:%M:%S")
        }
        background_tasks.add_task(run_yt_download_task, task_id, ch["url"], quality, limit)
        dispatched.append({"channel": ch["name"], "task_id": task_id})

    return {
        "status": "success",
        "message": f"Sync initiated for {len(dispatched)} channel(s). Fetching top {limit} videos.",
        "tasks": dispatched
    }

# --- Front-End HTML Delivery ---
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Media Server UI is building... Refresh in a few seconds.</h1>"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    local_ip = get_local_ip()
    print("=" * 60)
    print("[*] JARVIS Glass Media Server & Cloud Drive Online")
    print(f"[*] Local Laptop URL:  http://localhost:8000")
    print(f"[*] Mobile Wi-Fi URL:  http://{local_ip}:8000")
    print("=" * 60)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
