"""
═══════════════════════════════════════════════
 Downloader API Server — Render.com
 ✦ Instagram / YouTube / Twitter / TikTok
 ✦ With YouTube cookies support
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

# ── YouTube ──
def download_youtube(url, quality="720"):
    opts = get_ydl_opts({
        "format": f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best[ext=mp4]/best",
    })
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        # پیدا کردن url
        video_url = None
        if info.get("requested_formats"):
            # merge format — url اول رو برمیگردونه
            video_url = info["requested_formats"][0].get("url")
        elif info.get("url"):
            video_url = info["url"]
        elif info.get("formats"):
            for f in reversed(info["formats"]):
                if f.get("url") and f.get("vcodec") != "none":
                    video_url = f["url"]
                    break

        return {
            "url": video_url,
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "type": "video",
        }

def download_youtube_mp3(url):
    opts = get_ydl_opts({
        "format": "bestaudio/best",
    })
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info.get("url")
        if not audio_url and info.get("formats"):
            for f in reversed(info["formats"]):
                if f.get("url") and f.get("acodec") != "none":
                    audio_url = f["url"]
                    break
        return {
            "url": audio_url,
            "title": info.get("title", ""),
            "type": "audio",
        }

# ── Instagram ──
def download_instagram(url):
    opts = get_ydl_opts({
        "format": "best",
    })
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        items = []

        entries = info.get("entries") or ([info] if info.get("url") or info.get("thumbnail") else [])

        for entry in entries:
            if not entry:
                continue
            u = entry.get("url")
            thumb = entry.get("thumbnail", "")
            is_video = entry.get("vcodec") not in (None, "none")

            if u:
                items.append({"url": u, "type": "video" if is_video else "image", "thumbnail": thumb})
            elif thumb:
                items.append({"url": thumb, "type": "image"})

        return {
            "items": items,
            "caption": info.get("description", "") or info.get("title", ""),
        }

# ── Twitter ──
def download_twitter(url):
    opts = get_ydl_opts({"format": "best"})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        items = []
        entries = info.get("entries") or ([info] if info.get("url") else [])
        for entry in entries:
            if not entry:
                continue
            u = entry.get("url")
            if u:
                is_video = entry.get("vcodec") not in (None, "none")
                items.append({"url": u, "type": "video" if is_video else "image"})
        return {
            "items": items,
            "caption": info.get("description", "") or info.get("title", ""),
        }

# ── TikTok ──
def download_tiktok(url):
    opts = get_ydl_opts({"format": "best"})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "items": [{"url": info["url"], "type": "video"}],
            "caption": info.get("title", ""),
        }

# ══════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════

@app.route("/health")
def health():
    cookie_exists = os.path.exists(COOKIES_FILE)
    return jsonify({"status": "ok", "cookies": cookie_exists})

@app.route("/youtube", methods=["POST"])
def youtube():
    if not check_auth(request):
        return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    quality = data.get("quality", "720")
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        if quality == "mp3":
            result = download_youtube_mp3(url)
        else:
            result = download_youtube(url, quality)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/instagram", methods=["POST"])
def instagram():
    if not check_auth(request):
        return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        result = download_instagram(url)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/twitter", methods=["POST"])
def twitter():
    if not check_auth(request):
        return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        result = download_twitter(url)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/tiktok", methods=["POST"])
def tiktok():
    if not check_auth(request):
        return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    url = data.get("url")
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        result = download_tiktok(url)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
