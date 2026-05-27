"""
═══════════════════════════════════════════════
 Downloader API Server — Railway.app
 ✦ Instagram / YouTube / Twitter / TikTok
═══════════════════════════════════════════════
"""

from flask import Flask, request, jsonify
import yt_dlp
import os
import re

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY", "mySecretApiKey2024")

def check_auth(req):
    return req.headers.get("X-API-Key") == API_KEY

# ── YouTube ──
def download_youtube(url, quality="720"):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "url": info.get("url") or info["requested_formats"][0]["url"] if info.get("requested_formats") else None,
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "type": "video",
        }

def download_youtube_mp3(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestaudio/best",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "url": info.get("url"),
            "title": info.get("title", ""),
            "type": "audio",
        }

# ── Instagram ──
def download_instagram(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "best",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        items = []
        if info.get("_type") == "playlist" or info.get("entries"):
            for entry in info.get("entries", []):
                if entry.get("url"):
                    items.append({
                        "url": entry["url"],
                        "type": "video" if entry.get("vcodec") != "none" else "image",
                        "thumbnail": entry.get("thumbnail", ""),
                    })
        else:
            url_result = info.get("url")
            thumb = info.get("thumbnail", "")
            is_video = info.get("vcodec") != "none" and info.get("vcodec") is not None
            if url_result:
                items.append({
                    "url": url_result,
                    "type": "video" if is_video else "image",
                    "thumbnail": thumb,
                })
            elif thumb:
                items.append({"url": thumb, "type": "image"})
        return {
            "items": items,
            "caption": info.get("description", "") or info.get("title", ""),
        }

# ── Twitter ──
def download_twitter(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "best",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        items = []
        if info.get("entries"):
            for e in info["entries"]:
                if e.get("url"):
                    items.append({"url": e["url"], "type": "video" if e.get("vcodec") != "none" else "image"})
        else:
            if info.get("url"):
                items.append({
                    "url": info["url"],
                    "type": "video" if info.get("vcodec") != "none" else "image",
                })
        return {
            "items": items,
            "caption": info.get("description", "") or info.get("title", ""),
        }

# ── TikTok ──
def download_tiktok(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "best",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "items": [{"url": info["url"], "type": "video"}],
            "caption": info.get("title", ""),
        }

# ══════════════════════════════════════════════
#  API ROUTES
# ══════════════════════════════════════════════

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/youtube", methods=["POST"])
def youtube():
    if not check_auth(request): return jsonify({"error": "unauthorized"}), 401
    data = request.json
    url = data.get("url")
    quality = data.get("quality", "720")
    if not url: return jsonify({"error": "url required"}), 400
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
    if not check_auth(request): return jsonify({"error": "unauthorized"}), 401
    data = request.json
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
    data = request.json
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
    data = request.json
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
