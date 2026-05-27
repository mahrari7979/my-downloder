"""
Downloader API Server — Render.com
با debug endpoint برای تشخیص مشکل
"""
from flask import Flask, request, jsonify
import yt_dlp
import os
import json

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY", "mySecretApiKey2024")
COOKIES_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")

def check_auth(req):
    return req.headers.get("X-API-Key") == API_KEY

def get_ydl_opts(extra={}):
    opts = {
        "quiet": False,
        "no_warnings": False,
        "skip_download": True,
        "nocheckcertificate": True,
        "extractor_args": {"instagram": {"include_feed_data": ["1"]}},
    }
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    opts.update(extra)
    return opts

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "cookies_exists": os.path.exists(COOKIES_FILE),
        "cookies_size": os.path.getsize(COOKIES_FILE) if os.path.exists(COOKIES_FILE) else 0,
    })

@app.route("/debug", methods=["POST"])
def debug():
    """endpoint برای دیدن کامل info از yt-dlp"""
    if not check_auth(request): return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    if not url: return jsonify({"error": "url required"}), 400
    try:
        opts = get_ydl_opts({"format": "best"})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # برگردوندن اطلاعات مهم
            formats = info.get("formats") or []
            return jsonify({
                "ok": True,
                "title": info.get("title"),
                "url": info.get("url"),
                "vcodec": info.get("vcodec"),
                "acodec": info.get("acodec"),
                "thumbnail": info.get("thumbnail"),
                "extractor": info.get("extractor"),
                "has_entries": bool(info.get("entries")),
                "entries_count": len(info.get("entries") or []),
                "formats_count": len(formats),
                "formats_sample": [
                    {
                        "format_id": f.get("format_id"),
                        "url": f.get("url", "")[:100],
                        "vcodec": f.get("vcodec"),
                        "acodec": f.get("acodec"),
                        "height": f.get("height"),
                    }
                    for f in formats[:5]
                ],
            })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/instagram", methods=["POST"])
def instagram():
    if not check_auth(request): return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    if not url: return jsonify({"error": "url required"}), 400
    try:
        opts = get_ydl_opts({"format": "best"})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            items = []
            entries = info.get("entries")

            if entries:
                for entry in entries:
                    if not entry: continue
                    formats = entry.get("formats") or []
                    # بهترین فرمت ویدیویی
                    video_formats = [f for f in formats if f.get("url") and f.get("vcodec") not in (None, "none")]
                    if video_formats:
                        best = max(video_formats, key=lambda f: f.get("height") or 0)
                        items.append({"url": best["url"], "type": "video"})
                    elif entry.get("url"):
                        items.append({"url": entry["url"], "type": "video"})
                    elif entry.get("thumbnail"):
                        items.append({"url": entry["thumbnail"], "type": "image"})
            else:
                formats = info.get("formats") or []
                video_formats = [f for f in formats if f.get("url") and f.get("vcodec") not in (None, "none")]
                if video_formats:
                    best = max(video_formats, key=lambda f: f.get("height") or 0)
                    items.append({"url": best["url"], "type": "video"})
                elif info.get("url"):
                    items.append({"url": info["url"], "type": "video"})
                elif info.get("thumbnail"):
                    items.append({"url": info["thumbnail"], "type": "image"})

            return jsonify({
                "ok": True,
                "items": items,
                "caption": (info.get("description") or info.get("title") or "")[:500],
            })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/youtube", methods=["POST"])
def youtube():
    if not check_auth(request): return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    quality = data.get("quality", "720")
    if not url: return jsonify({"error": "url required"}), 400
    try:
        if quality == "mp3":
            opts = get_ydl_opts({"format": "bestaudio/best"})
        else:
            opts = get_ydl_opts({"format": "best"})
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats") or []
            
            video_url = None
            if quality == "mp3":
                audio = [f for f in formats if f.get("url") and f.get("acodec") not in (None, "none")]
                if audio:
                    best = max(audio, key=lambda f: f.get("abr") or 0)
                    video_url = best["url"]
            else:
                videos = [f for f in formats if f.get("url") and f.get("vcodec") not in (None, "none")]
                if videos:
                    best = max(videos, key=lambda f: f.get("height") or 0)
                    video_url = best["url"]
            
            if not video_url:
                video_url = info.get("url")
            
            return jsonify({
                "ok": True,
                "url": video_url,
                "title": info.get("title", ""),
                "thumbnail": info.get("thumbnail", ""),
                "type": "audio" if quality == "mp3" else "video",
            })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/twitter", methods=["POST"])
def twitter():
    if not check_auth(request): return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    if not url: return jsonify({"error": "url required"}), 400
    try:
        opts = get_ydl_opts({"format": "best"})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            items = []
            entries = info.get("entries")
            if entries:
                for entry in entries:
                    if entry and entry.get("url"):
                        items.append({"url": entry["url"], "type": "video"})
            elif info.get("url"):
                items.append({"url": info["url"], "type": "video"})
            return jsonify({"ok": True, "items": items, "caption": (info.get("description") or "")[:500]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/tiktok", methods=["POST"])
def tiktok():
    if not check_auth(request): return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    if not url: return jsonify({"error": "url required"}), 400
    try:
        opts = get_ydl_opts({"format": "best"})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({"ok": True, "items": [{"url": info.get("url"), "type": "video"}], "caption": info.get("title", "")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
