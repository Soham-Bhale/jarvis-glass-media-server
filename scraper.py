import os
import glob
import subprocess
from datetime import datetime
import yt_dlp
from app import CATEGORIES, THUMBNAILS_DIR, update_file_meta, generate_video_thumbnail, load_channels

def scrape_youtube_channels(limit_per_channel=4, quality="720"):
    try:
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    channels = load_channels()
    if not channels:
        channels = [
            {"name": "THE CHANAKYA DIALOGUES HINDI", "url": "https://www.youtube.com/@THECHANAKYADIALOGUESHINDI/videos"},
            {"name": "Adda247 Skills", "url": "https://www.youtube.com/@adda247-skills/videos"}
        ]

    print("=" * 60)
    print(f"[*] JARVIS Batch YouTube Scraper Started ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"[*] Target: {len(channels)} channels | Limit: {limit_per_channel} videos/channel | Quality: {quality}p")
    print("=" * 60)

    format_spec = f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}]/best"
    
    ydl_opts = {
        'format': format_spec,
        'outtmpl': os.path.join(CATEGORIES['videos'], '%(title).120s_%(id)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'writethumbnail': True,
        'playlistend': limit_per_channel,
        'ignoreerrors': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'quiet': False
    }

    total_added = 0
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for ch in channels:
            print(f"\n[*] Scraping channel: {ch['name']} ({ch['url']})...")
            try:
                info = ydl.extract_info(ch['url'], download=True)
                entries = info.get('entries', [info]) if info else []
                
                for entry in entries:
                    if not entry:
                        continue
                    v_id = entry.get('id', '')
                    title = entry.get('title', 'Unknown Title')
                    
                    # Locate video and thumbnail
                    search_pat = os.path.join(CATEGORIES['videos'], f"*{v_id}.*")
                    matches = glob.glob(search_pat)
                    media_files = [m for m in matches if not m.endswith(('.jpg', '.webp', '.png'))]
                    
                    if media_files:
                        video_file = media_files[0]
                        filename = os.path.basename(video_file)
                        
                        thumb_matches = [m for m in matches if m.endswith(('.jpg', '.webp', '.png'))]
                        if thumb_matches:
                            dest_thumb = os.path.join(THUMBNAILS_DIR, f"{filename}.jpg")
                            try:
                                subprocess.run(["ffmpeg", "-y", "-i", thumb_matches[0], dest_thumb],
                                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                os.remove(thumb_matches[0])
                            except Exception:
                                pass
                        else:
                            generate_video_thumbnail(video_file, f"{filename}.jpg")

                        update_file_meta("videos", filename, {
                            "title": title,
                            "youtube_id": v_id,
                            "uploader": ch['name'],
                            "duration": entry.get('duration'),
                            "source_url": f"https://youtube.com/watch?v={v_id}",
                            "downloaded_at": datetime.now().isoformat()
                        })
                        total_added += 1
                        print(f"  [+] Saved video: {title}")

            except Exception as e:
                print(f"  [!] Error scraping {ch['name']}: {e}")

    print("\n" + "=" * 60)
    print(f"✅ Scraping Complete! Added {total_added} videos to media library.")
    print("=" * 60)

if __name__ == "__main__":
    scrape_youtube_channels(limit_per_channel=2, quality="720")
