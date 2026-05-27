"""
═══════════════════════════════════════════════
 Downloader API Server — Render.com
 ✦ Instagram / YouTube / Twitter / TikTok
═══════════════════════════════════════════════
"""

from flask import Flask, request, jsonify
import yt_dlp
import os

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY", "mySecretApiKey2024")
COOKIES_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")

def check_auth(req):
    return req.headers.get("X-API-Key") == API_KEY

def get_ydl_opts(extra={}):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "nocheckcertificate": True,
    }
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    opts.update(extra)
    return opts

def extract_best_url(info):
    """پیدا کردن بهترین لینک ویدیو از info"""
    # اول formats رو چک کن
    formats = info.get("formats") or []
    
    # بهترین فرمت ویدیویی
    video_formats = [f for f in formats if f.get("url") and f.get("vcodec") not in (None, "none", "") and f.get("acodec") not in (None, "none", "")]
    if video_formats:
        # بالاترین کیفیت
        best = max(video_formats, key=lambda f: f.get("height") or 0)
        return best["url"], "video"
    
    # فرمت‌های فقط ویدیو
    video_only = [f for f in formats if f.get("url") and f.get("vcodec") not in (None, "none", "")]
    if video_only:
        best = max(video_only, key=lambda f: f.get("height") or 0)
        return best["url"], "video"
    
    # url مستقیم
    if info.get("url"):
        vcodec = info.get("vcodec", "")
        is_video = vcodec and vcodec != "none"
        return info["url"], "video" if is_video else "image"
    
    # thumbnail به عنوان آخرین گزینه
    if info.get("thumbnail"):
        return info["thumbnail"], "image"
    
    return None, None

# ── YouTube ──
def download_youtube(url, quality="720"):
    opts = get_ydl_opts({
        "format": f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best",
    })
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        video_url = None
        if info.get("requested_formats"):
            video_url = info["requested_formats"][0].get("url")
        
        if not video_url:
            video_url, _ = extract_best_url(info)
        
        return {
            "url": video_url,
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "type": "video",
        }

def download_youtube_mp3(url):
    opts = get_ydl_opts({"format": "bestaudio/best"})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        audio_url = None
        formats = info.get("formats") or []
        audio_formats = [f for f in formats if f.get("url") and f.get("acodec") not in (None, "none", "") and f.get("vcodec") in (None, "none", "")]
        
        if audio_formats:
            best = max(audio_formats, key=lambda f: f.get("abr") or 0)
            audio_url = best["url"]
        elif info.get("url"):
            audio_url = info["url"]
        
        return {
            "url": audio_url,
            "title": info.get("title", ""),
            "type": "audio",
        }

# ── Instagram ──
def download_instagram(url):
    opts = get_ydl_opts({
        "format": "bestvideo+bestaudio/best",
    })
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        items = []
        
        entries = info.get("entries")
        
        if entries:
            # آلبوم / چند رسانه
            for entry in entries:
                if not entry:
                    continue
                media_url, media_type = extract_best_url(entry)
                if media_url:
                    items.append({
                        "url": media_url,
                        "type": media_type,
                        "thumbnail": entry.get("thumbnail", ""),
                    })
        else:
            # یه پست / ریلز
            media_url, media_type = extract_best_url(info)
            if media_url:
                items.append({
                    "url": media_url,
                    "type": media_type,
                    "thumbnail": info.get("thumbnail", ""),
                })
        
        return {
            "items": items,
            "caption": (info.get("description") or info.get("title") or "")[:500],
        }

# ── Twitter / X ──
def download_twitter(url):
    opts = get_ydl_opts({"format": "bestvideo+bestaudio/best"})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        items = []
        
        entries = info.get("entries")
        if entries:
            for entry in entries:
                if not entry:
                    continue
                media_url, media_type = extract_best_url(entry)
                if media_url:
                    items.append({"url": media_url, "type": media_type})
        else:
            media_url, media_type = extract_best_url(info)
            if media_url:
                items.append({"url": media_url, "type": media_type})
        
        return {
            "items": items,
            "caption": (info.get("description") or info.get("title") or "")[:500],
        }

# ── TikTok ──
def download_tiktok(url):
    opts = get_ydl_opts({"format": "bestvideo+bestaudio/best"})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        media_url, media_type = extract_best_url(info)
        return {
            "items": [{"url": media_url, "type": media_type or "video"}],
            "caption": (info.get("title") or "")[:500],
        }

# ══════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════

@app.route("/health")
def health():
    return jsonify({"status": "ok", "cookies": os.path.exists(COOKIES_FILE)})

@app.route("/youtube", methods=["POST"])
def youtube():
    if not check_auth(request): return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    quality = data.get("quality", "720")
    if not url: return jsonify({"error": "url required"}), 400
    try:
        result = download_youtube_mp3(url) if quality == "mp3" else download_youtube(url, quality)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/instagram", methods=["POST"])
def instagram():
    if not check_auth(request): return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    if not url: return jsonify({"error": "url required"}), 400
    try:
        result = download_instagram(url)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/twitter", methods=["POST"])
def twitter():
    if not check_auth(request): return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    if not url: return jsonify({"error": "url required"}), 400
    try:
        result = download_twitter(url)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/tiktok", methods=["POST"])
def tiktok():
    if not check_auth(request): return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    if not url: return jsonify({"error": "url required"}), 400
    try:
        result = download_tiktok(url)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
