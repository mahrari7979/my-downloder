"""
Downloader API Server — Render.com
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

def best_video_url(info):
    """پیدا کردن بهترین URL ویدیو"""
    formats = info.get("formats") or []
    
    # فرمت‌هایی که هم ویدیو هم صدا دارن
    combined = [f for f in formats 
                if f.get("url") 
                and f.get("vcodec") not in (None, "none")
                and f.get("acodec") not in (None, "none")]
    if combined:
        best = max(combined, key=lambda f: (f.get("height") or 0))
        return best["url"], "video"
    
    # هر فرمت ویدیویی
    videos = [f for f in formats if f.get("url") and f.get("vcodec") not in (None, "none")]
    if videos:
        best = max(videos, key=lambda f: (f.get("height") or 0))
        return best["url"], "video"
    
    # url مستقیم
    if info.get("url"):
        return info["url"], "video"
    
    # thumbnail
    if info.get("thumbnail"):
        return info["thumbnail"], "image"
    
    return None, None

# ── YouTube ──
def download_youtube(url, quality="720"):
    # اول بدون فرمت خاص امتحان کن
    opts = get_ydl_opts({"format": "best"})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_url, _ = best_video_url(info)
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
        formats = info.get("formats") or []
        
        # بهترین فرمت صوتی
        audio = [f for f in formats if f.get("url") and f.get("acodec") not in (None, "none")]
        if audio:
            best = max(audio, key=lambda f: f.get("abr") or 0)
            return {"url": best["url"], "title": info.get("title", ""), "type": "audio"}
        
        if info.get("url"):
            return {"url": info["url"], "title": info.get("title", ""), "type": "audio"}
        
        raise Exception("no audio found")

# ── Instagram ──
def download_instagram(url):
    opts = get_ydl_opts({"format": "best"})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        items = []
        entries = info.get("entries")
        
        if entries:
            for entry in entries:
                if not entry: continue
                u, t = best_video_url(entry)
                if u:
                    items.append({"url": u, "type": t, "thumbnail": entry.get("thumbnail", "")})
        else:
            u, t = best_video_url(info)
            if u:
                items.append({"url": u, "type": t, "thumbnail": info.get("thumbnail", "")})
        
        # اگه هیچی پیدا نشد thumbnail رو بده
        if not items and info.get("thumbnail"):
            items.append({"url": info["thumbnail"], "type": "image"})
        
        return {
            "items": items,
            "caption": (info.get("description") or info.get("title") or "")[:500],
        }

# ── Twitter ──
def download_twitter(url):
    opts = get_ydl_opts({"format": "best"})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        items = []
        entries = info.get("entries")
        
        if entries:
            for entry in entries:
                if not entry: continue
                u, t = best_video_url(entry)
                if u: items.append({"url": u, "type": t})
        else:
            u, t = best_video_url(info)
            if u: items.append({"url": u, "type": t})
        
        return {
            "items": items,
            "caption": (info.get("description") or info.get("title") or "")[:500],
        }

# ── TikTok ──
def download_tiktok(url):
    opts = get_ydl_opts({"format": "best"})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        u, t = best_video_url(info)
        return {
            "items": [{"url": u, "type": t or "video"}],
            "caption": (info.get("title") or "")[:500],
        }

# ══════ ROUTES ══════

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
