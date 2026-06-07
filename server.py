import os
import re
import time
import secrets
import hmac
import hashlib
import urllib.parse
from flask import Flask, request, Response, render_template_string, abort
import yt_dlp
import requests
from yt_dlp.networking.impersonate import ImpersonateTarget

app = Flask(__name__)

# --- SECURITY CONFIGURATION ---
ALLOWED_DOMAIN = "https://cggames.pythonanywhere.com"
# Automatically generates a fresh key on startup to sign streaming tokens
SECRET_KEY = os.environ.get("STREAM_SECRET_KEY", secrets.token_hex(32)).encode('utf-8')
TOKEN_TTL = 14400  # Token validity window: 4 hours

def generate_stream_token(video_id):
    """Generates a timed, cryptographically signed playback token."""
    expires = str(int(time.time()) + TOKEN_TTL)
    msg = f"{video_id}:{expires}".encode('utf-8')
    signature = hmac.new(SECRET_KEY, msg, hashlib.sha256).hexdigest()
    return f"{expires}.{signature}"

def verify_stream_token(video_id, token):
    """Verifies the token cryptographic signature and expiration status."""
    if not token:
        return False
    try:
        expires, signature = token.split('.', 1)
        if int(expires) < time.time():
            return False  # Expired
        msg = f"{video_id}:{expires}".encode('utf-8')
        expected = hmac.new(SECRET_KEY, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False

def check_domain_clearance(req):
    """Enforces strict Origin/Referer browser domain alignment."""
    # Read browser security headers
    origin = req.headers.get("Origin")
    referer = req.headers.get("Referer")
    
    if origin and origin.rstrip('/') != ALLOWED_DOMAIN.rstrip('/'):
        return False
    if referer and not referer.startswith(ALLOWED_DOMAIN):
        return False
    # If a direct browser access attempt is made without Origin/Referer, drop it
    if not origin and not referer:
        return False
    return True

def add_cors_headers(response):
    """Appends explicit cross-origin policy parameters to outbound payloads."""
    response.headers["Access-Control-Allow-Origin"] = ALLOWED_DOMAIN
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Origin, Accept, Content-Type, X-Requested-With"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["X-Frame-Options"] = f"ALLOW-FROM {ALLOWED_DOMAIN}"
    response.headers["Content-Security-Policy"] = f"frame-ancestors 'self' {ALLOWED_DOMAIN}"
    return response


# --- UI TEMPLATES ---
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NebulaView Engine Core</title>
    <style>
        body { background-color: #09090b; color: #f4f4f5; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { max-width: 500px; text-align: center; padding: 40px; background: rgba(15, 15, 20, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; backdrop-filter: blur(20px); }
        h1 { font-size: 1.8rem; margin-bottom: 16px; background: linear-gradient(135deg, #ff0055, #6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p { color: #a1a1aa; line-height: 1.6; font-size: 0.95rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NebulaView Core</h1>
        <p>Direct interaction environment is restricted. Security validation policies active.</p>
    </div>
</body>
</html>
"""

PLAYER_TEMPLATE = """
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
    <style>
        html, body { margin: 0; padding: 0; width: 100%; height: 100%; background-color: #030303; overflow: hidden; font-family: sans-serif; }
        .video-wrapper { position: relative; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }
        .video-js { width: 100% !important; height: 100% !important; background-color: #000 !important; }
        #video-loader { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #09090b; z-index: 9999; display: flex; flex-direction: column; justify-content: center; align-items: center; transition: opacity 0.4s ease; pointer-events: none; }
        .spinner { box-sizing: border-box; width: 64px; height: 64px; border: 4px solid rgba(99, 102, 241, 0.1); border-top: 4px solid #6366f1; border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loader-text { margin-top: 22px; font-size: 0.8rem; font-weight: 600; color: #ffffff; letter-spacing: 2px; text-transform: uppercase; }
        :root { --brand-accent: #ff0055; --glass-bg: rgba(15, 15, 20, 0.6); --glass-border: rgba(255, 255, 255, 0.08); }
        .video-js .vjs-big-play-button { background: linear-gradient(135deg, rgba(255, 0, 85, 0.8), rgba(99, 102, 241, 0.8)) !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 50% !important; width: 76px !important; height: 76px !important; line-height: 74px !important; margin-top: -38px !important; margin-left: -38px !important; backdrop-filter: blur(4px); }
        .video-js .vjs-control-bar { background: var(--glass-bg) !important; backdrop-filter: blur(20px) !important; -webkit-backdrop-filter: blur(20px) !important; border: 1px solid var(--glass-border); border-radius: 16px !important; width: calc(100% - 32px) !important; height: 54px !important; bottom: 16px !important; left: 16px !important; }
        .video-js .vjs-progress-control { position: absolute !important; width: calc(100% - 32px) !important; height: 5px !important; top: -5px !important; left: 16px !important; }
        .video-js .vjs-play-progress { background: linear-gradient(90deg, #6366f1, var(--brand-accent)) !important; border-radius: 3px !important; }
        .video-js .vjs-play-progress:before { display: none !important; }
        .video-js .vjs-time-control { line-height: 54px !important; }
    </style>
</head>
<body>
    <div class="video-wrapper">
        <div id="video-loader"><div class="spinner"></div><div class="loader-text">Authorizing Matrix Access</div></div>
        <video id="my-video" class="video-js vjs-default-skin vjs-big-play-centered" controls playsinline>
            <source src="/manifest?url={{ target_url | urlencode }}&id={{ video_id }}&tk={{ token }}" type="application/x-mpegURL">
        </video>
    </div>
    <script src="https://vjs.zencdn.net/8.10.0/video.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const player = videojs('my-video', {
                preload: 'auto', autoplay: true, controls: true, inactivityTimeout: 2000,
                html5: { vhs: { overrideNative: true, maxBufferLength: 45, liveBufferLength: 12 } }
            });
            player.on('canplay', function() {
                const loader = document.getElementById('video-loader');
                if (loader) { loader.style.opacity = '0'; setTimeout(() => loader.remove(), 400); }
                player.play().catch(() => { player.muted(true); player.play(); });
            });
        });
    </script>
</body>
</html>
"""


# --- ROUTE HANDLERS ---

@app.route('/')
def index():
    if not check_domain_clearance(request):
        abort(403, description="Access Denied: Out of ecosystem context.")
    return add_cors_headers(Response(render_template_string(INDEX_TEMPLATE)))


@app.route('/download', methods=['POST', 'GET'])
def render_player():
    # CORS & Context Verification
    if not check_domain_clearance(request):
        abort(403, description="Access Denied: Embedding Context Violation.")

    user_input = request.form.get('id_or_url', '').strip() if request.method == 'POST' else request.args.get('id_or_url', '').strip()
    if not user_input:
        return "Missing 'id_or_url' parameter.", 400

    # Extract clean target details
    if "dailymotion.com" in user_input:
        target_url = user_input if user_input.startswith(("http://", "https://")) else f"https://{user_input}"
        video_id = user_input.split("/video/")[-1].split("?")[0]
    else:
        target_url = f"https://www.dailymotion.com/video/{user_input}"
        video_id = user_input

    # Cryptographic keys generated exclusively for this single session run
    token = generate_stream_token(video_id)

    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'impersonate': ImpersonateTarget.from_str('chrome'),
        'socket_timeout': 10
    }

    info = None
    m3u8_url = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            formats = info.get('formats', [])
            
            hls_streams = []
            for f in formats:
                fmt_url = f.get('url', '')
                fmt_id = str(f.get('format_id', '')).lower()
                fmt_proto = str(f.get('protocol', '')).lower()
                if 'm3u8' in fmt_url or 'm3u8' in fmt_proto or 'hls' in fmt_id:
                    hls_streams.append(f)

            if hls_streams:
                m3u8_url = hls_streams[-1].get('url')
            else:
                m3u8_url = info.get('url') or (formats[-1].get('url') if formats else None)
                
    except Exception as first_error:
        print(f"Primary fetch bypassed: {first_error}. Adapting schema options...")
        time.sleep(1.5)
        try:
            ydl_opts['format'] = 'b'
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                formats = info.get('formats', [])
                m3u8_url = info.get('url') or (formats[-1].get('url') if formats else None)
        except Exception as second_error:
            print(f"Fallback executed: {second_error}")
            m3u8_url = f"https://www.dailymotion.com/cdn/manifest/video/{video_id}.m3u8"
            info = {'title': 'Dailymotion Stream (Fallback Mode)'}

    if not m3u8_url:
        return "Failed to find manifest endpoint maps.", 500

    response_payload = render_template_string(
        PLAYER_TEMPLATE, 
        title=info.get('title', 'Dailymotion Stream') if info else 'Dailymotion Stream',
        target_url=m3u8_url,
        video_id=video_id,
        token=token
    )
    return add_cors_headers(Response(response_payload))


@app.route('/manifest')
def proxy_m3u8():
    # 1. Validation Interceptors
    if not check_domain_clearance(request):
        abort(403, description="Cross-Origin Stream Hijacking Blocked.")

    video_id = request.args.get('id')
    token = request.args.get('tk')
    
    if not video_id or not verify_stream_token(video_id, token):
        abort(401, description="Invalid or Expired System Token Access Keys.")

    raw_m3u8_url = request.args.get('url')
    if not raw_m3u8_url:
        return "Missing target reference", 400

    raw_m3u8_url = urllib.parse.unquote(raw_m3u8_url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    resp = requests.get(raw_m3u8_url, headers=headers)

    base_url = raw_m3u8_url.rsplit('/', 1)[0] + '/'
    rewritten_lines = []

    for line in resp.text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Append authorization parameters down through nested components
        if 'URI=' in line_stripped:
            def replace_uri(match):
                rel_path = match.group(1).strip('"\'')
                abs_url = urllib.parse.urljoin(base_url, rel_path)
                proxy_route = "/manifest" if (".m3u8" in rel_path or "manifest" in rel_path) else "/segment"
                return f'URI="{proxy_route}?url={urllib.parse.quote_plus(abs_url)}&id={video_id}&tk={token}"'

            line_stripped = re.sub(r'URI=(["\'].*?["\'])', replace_uri, line_stripped)
            rewritten_lines.append(line_stripped)

        elif not line_stripped.startswith('#'):
            if not line_stripped.startswith(('http://', 'https://')):
                full_url = urllib.parse.urljoin(base_url, line_stripped)
            else:
                full_url = line_stripped

            encoded_url = urllib.parse.quote_plus(full_url)

            if '.m3u8' in line_stripped or 'manifest' in line_stripped:
                rewritten_lines.append(f"/manifest?url={encoded_url}&id={video_id}&tk={token}")
            else:
                rewritten_lines.append(f"/segment?url={encoded_url}&id={video_id}&tk={token}")
        else:
            rewritten_lines.append(line_stripped)

    return add_cors_headers(Response("\n".join(rewritten_lines), content_type="application/x-mpegURL"))


@app.route('/segment')
def proxy_ts_segment():
    # 1. Validation Interceptors
    if not check_domain_clearance(request):
        abort(403, description="Cross-Origin Segment Hijacking Blocked.")

    video_id = request.args.get('id')
    token = request.args.get('tk')
    
    if not video_id or not verify_stream_token(video_id, token):
        abort(401, description="Invalid or Expired Segment Token Access Keys.")

    raw_ts_url = request.args.get('url')
    if not raw_ts_url:
        return "Missing segment path", 400

    raw_ts_url = urllib.parse.unquote(raw_ts_url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    req = requests.get(raw_ts_url, headers=headers, stream=True)

    def stream_ts_data():
        for block in req.iter_content(chunk_size=1024 * 64):
            yield block

    content_type = req.headers.get('Content-Type', 'video/MP2T')
    return add_cors_headers(Response(stream_ts_data(), content_type=content_type))


# Global options request interception for CORS Preflight checks
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return add_cors_headers(Response())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
