# 💎 JARVIS Glass Media Server & Personal Cloud Drive

An offline-first, local **Media Streaming Hub, YouTube Channel Scraper, and Personal Cloud Drive** engineered with an **Apple Liquid Glass (visionOS / macOS)** design language and remote PC power controls.

Turn any Windows laptop or desktop into a private media server and Wi-Fi drive accessible from any iPhone, Android, tablet, or browser on your local network.

---

## ✨ Features

- **Liquid Glass UI / UX**:
  - Translucent glassmorphism panels (`backdrop-filter: blur(28px) saturate(190%)`).
  - Specular light borders, floating glass dock navigation, and ambient glowing mesh orbs.
  - Apple Dark Titanium & Apple Light Frost theme switcher with persistent local storage.

- **HTTP 206 Range Video Streaming**:
  - Full support for chunked partial-content range streaming.
  - Smooth seek and scrub navigation on iOS Safari, Android Chrome, and desktop browsers.
  - In-browser video player with picture-in-picture, fullscreen, playback speed controls, and direct download button.

- **YouTube Scraper & Downloader**:
  - Download individual videos, playlists, or entire channels in **1080p FHD, 720p HD, 480p, or MP3 Audio**.
  - **Dynamic Channel Tracker**: Add and track custom channels (e.g. *The Chanakya Dialogues*, *Adda247 Skills*).
  - 1-Click **"Sync Recent 4 Videos"** for instant background downloading.
  - Real-time progress cards with transfer speeds (MB/s), ETA, and status indicators.

- **Personal Cloud Drive**:
  - Drag-and-drop file uploader on desktop + native mobile file/camera picker.
  - Automatic categorization into **Videos, Music, Photos, Documents, and Archives**.
  - Instant mobile connection via on-screen QR Code.

- **Remote PC Power & Control Center**:
  - 1-Click **Safe Shutdown** (30s countdown with live cancel button).
  - 1-Click **Instant Shutdown** (0s delay).
  - **Restart PC**, **Sleep / Standby**, **Lock Screen**, and **Cancel Pending Shutdown**.
  - Real-time hardware performance monitor: CPU load, RAM usage, Battery status, and Uptime.

- **Floating Glass Audio Player**:
  - Background audio player docked at the bottom of the screen with play/pause, scrub bar, and track metadata.

---

## 🚀 1-Click Quick Start (Windows)

Simply double-click **`start.bat`**.

It will start the server on port `8000` and automatically open your default browser to:
```
http://localhost:8000
```

### 📱 Connecting from Mobile / Other Devices
1. Ensure your phone is connected to the same Wi-Fi network as your laptop.
2. Open the browser on your phone and visit:
   ```
   http://<YOUR-LAPTOP-IP>:8000
   ```
   *(Or simply scan the on-screen QR code shown in the "Upload & Mobile" tab!)*

---

## 🛠️ Manual Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/minimoso/jarvis-glass-media-server.git
   cd jarvis-glass-media-server
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure FFmpeg is installed**:
   FFmpeg is required for merging high-quality video formats and generating thumbnails.
   - Windows (winget): `winget install Gyan.FFmpeg`
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`

4. **Run the server**:
   ```bash
   python app.py
   ```

---

## 📂 Project Structure

```
jarvis-glass-media-server/
├── app.py                 # FastAPI backend, range streaming, and power management
├── scraper.py             # Batch YouTube channel scraping utility
├── start.bat              # 1-Click Windows desktop launcher
├── run_media_server.bat   # Direct server batch runner
├── requirements.txt       # Python dependencies
├── static/
│   └── index.html         # Apple Glass Single-Page Application (HTML/CSS/JS)
└── storage/
    ├── videos/            # Downloaded and uploaded videos
    ├── photos/            # Photos and gallery files
    ├── audio/             # Music and audio rips
    ├── documents/         # PDF, Word, and text documents
    ├── files/             # Zip archives and other file formats
    ├── thumbnails/        # Video thumbnail cache
    ├── channels.json      # Tracked YouTube channel subscriptions
    └── metadata.json      # Media metadata registry
```

---

## 📄 License
MIT License. Free to use, modify, and distribute.
