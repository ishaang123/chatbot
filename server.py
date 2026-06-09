import os
import re
import sys
import subprocess
import threading
import time
import urllib.parse
import requests
from flask import Flask, request, Response, render_template_string
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

# Global lock to prevent multiple update processes from running at the exact same time
update_lock = threading.Lock()

def run_pip_update():
    """Helper function to execute the pip upgrade safely within a lock."""
    if update_lock.locked():
        print("[Engine Lifecycle] Update already in progress, skipping duplicate request.")
        return
        
    with update_lock:
        try:
            print("[Engine Lifecycle] Running extraction framework update check...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("[Engine Lifecycle] Engine package update routine completed successfully.")
        except Exception as e:
            print(f"[Engine Lifecycle] Upgrade execution deferred: {e}")

# --- CONTINUOUS BACKGROUND UPDATE LOOP ---
def upgrade_extractor_engine_loop():
    """Runs continuously. Checks and updates yt-dlp on startup, then every 2 hours."""
    time.sleep(5)  # Short pause to let Flask bind its ports smoothly
    while True:
        run_pip_update()
        time.sleep(7200)  # Sleep for 2 hours (7200 seconds)

# Start the continuous 2-hour background loop thread
threading.Thread(target=upgrade_extractor_engine_loop, daemon=True).start()


app = Flask(__name__)

# Streamlined persistent network pool for proxy operations
http_pool = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=200, pool_maxsize=200, pool_block=False)
http_pool.mount('http://', adapter)
http_pool.mount('https://', adapter)

INTERNAL_INFRASTRUCTURE_HOST = "cggames.pythonanywhere.com"

# --- UI TEMPLATES ---

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NebulaView Core</title>
    <style>
        body {
            background: radial-gradient(circle at center, #0c0a0f 0%, #050506 100%);
            color: #f4f4f5;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            max-width: 420px;
            text-align: center;
            padding: 40px;
            background: rgba(10, 10, 12, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 24px;
            backdrop-filter: blur(40px);
            box-shadow: 0 30px 60px rgba(0, 0, 0, 0.8);
        }
        h1 {
            font-size: 2rem;
            margin: 0 0 12px 0;
            background: linear-gradient(135deg, #a855f7, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }
        p { color: #71717a; line-height: 1.6; font-size: 0.95rem; margin: 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NebulaView Mobile</h1>
        <p>Pure Native Extraction Engine Active.</p>
    </div>
</body>
</html>
"""
PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
    <style>
        /* --- YT-EMBED DESIGN SYSTEM --- */
        :root {
            --accent-primary: #ff0000; /* YouTube Red Accent Line */
            --text-primary: #f1f1f1;
            --text-secondary: #c0c0c0;
            --gradient-top: linear-gradient(to bottom, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
        }

        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background-color: #000;
            overflow: hidden;
            font-family: "YouTube Noto", Roboto, Arial, sans-serif;
            -webkit-user-select: none;
            user-select: none;
        }

        .embed-player-canvas {
            position: relative;
            width: 100%;
            height: 100%;
            overflow: hidden;
        }

        .video-js {
            width: 100% !important;
            height: 100% !important;
            background-color: #000 !important;
        }

        /* --- FLOATING HEADER WITH TITLE & CHANNEL DATA --- */
        .embed-floating-header {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            padding: 20px 24px 40px 24px;
            background: var(--gradient-top);
            z-index: 10;
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            box-sizing: border-box;
            pointer-events: none;
            opacity: 1;
            transition: opacity 0.25s cubic-bezier(0.25, 1, 0.5, 1);
        }

        /* Fades header out alongside control bar interaction lifecycle */
        .vjs-has-started.vjs-user-inactive .embed-floating-header {
            opacity: 0;
        }

        .embed-header-left {
            display: flex;
            align-items: center;
            gap: 12px;
            pointer-events: auto;
            min-width: 0;
        }

        .embed-channel-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #a855f7, #6366f1);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: #fff;
            font-size: 0.9rem;
            flex-shrink: 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        }

        .embed-meta-text {
            display: flex;
            flex-direction: column;
            min-width: 0;
        }

        .embed-video-title {
            color: var(--text-primary);
            font-size: 1.1rem;
            font-weight: 500;
            margin: 0;
            white-space: nowrap;
            text-overflow: ellipsis;
            overflow: hidden;
            text-shadow: 0 1px 3px rgba(0,0,0,0.9);
            text-decoration: none;
        }
        .embed-video-title:hover { text-decoration: underline; }

        .embed-channel-name {
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin: 2px 0 0 0;
            text-shadow: 0 1px 2px rgba(0,0,0,0.9);
        }

        .embed-header-actions {
            display: flex;
            align-items: center;
            gap: 16px;
            pointer-events: auto;
            flex-shrink: 0;
        }
        
        .embed-icon-btn {
            background: transparent;
            border: none;
            color: var(--text-primary);
            cursor: pointer;
            padding: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            filter: drop-shadow(0px 1px 3px rgba(0,0,0,0.9));
            transition: transform 0.1s;
        }
        .embed-icon-btn:hover { transform: scale(1.1); }

        /* --- LOADING LAYER --- */
        #video-loader {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #000;
            z-index: 999;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: opacity 0.3s ease;
        }
        .spinner {
            box-sizing: border-box;
            width: 50px;
            height: 50px;
            border: 5px solid rgba(255, 255, 255, 0.15);
            border-top: 5px solid var(--accent-primary);
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* --- VIDEO.JS INTERFACE MODIFICATIONS --- */
        .video-js .vjs-big-play-button {
            background-color: rgba(33, 33, 33, 0.85) !important;
            border: none !important;
            border-radius: 12px !important;
            width: 68px !important;
            height: 48px !important;
            line-height: 48px !important;
            margin-top: -24px !important;
            margin-left: -34px !important;
            transition: background-color 0.1s ease !important;
            z-index: 20;
        }
        .video-js:hover .vjs-big-play-button { 
            background-color: var(--accent-primary) !important; 
        }
        
        .video-js .vjs-control-bar {
            background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.3) 60%, rgba(0,0,0,0) 100%) !important;
            height: 48px !important;
            width: 100% !important;
            bottom: 0 !important;
            left: 0 !important;
            border: none !important;
        }
        
        .video-js .vjs-progress-control {
            position: absolute !important;
            width: calc(100% - 24px) !important;
            height: 3px !important;
            top: -3px !important;
            left: 12px !important;
            transition: height 0.1s, top 0.1s;
        }
        .video-js .vjs-progress-control:hover { height: 5px !important; top: -5px !important; }
        .video-js .vjs-play-progress { background: var(--accent-primary) !important; }
        .video-js .vjs-play-progress:before { display: block !important; font-size: 11px !important; top: -3px !important; color: var(--accent-primary) !important; }
        .video-js .vjs-slider { background-color: rgba(255,255,255,0.2) !important; }
        .video-js .vjs-load-progress { background-color: rgba(255,255,255,0.35) !important; }
        .video-js .vjs-time-control { line-height: 48px !important; }
        
        .vjs-download-control { cursor: pointer; display: flex; align-items: center; justify-content: center; width: 40px; height: 100%; order: 99; }
        .vjs-download-control svg { width: 18px; height: 18px; fill: var(--text-primary); opacity: 0.8; transition: opacity 0.2s; }
        .vjs-download-control:hover svg { opacity: 1; }
    </style>
</head>
<body>

    <div class="embed-player-canvas">
        
        <div class="embed-floating-header" id="embed-header">
            <div class="embed-header-left">
                <div class="embed-channel-icon">NV</div>
                <div class="embed-meta-text">
                    <a class="embed-video-title" id="title-link" target="_blank">{{ title }}</a>
                    <span class="embed-channel-name">NebulaView Pipeline</span>
                </div>
            </div>
            <div class="embed-header-actions">
                <button class="embed-icon-btn" id="embed-share-btn" title="Share Video">
                    <svg style="width:22px;height:22px;fill:currentColor" viewBox="0 0 24 24"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.8 2.04.8 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg>
                </button>
            </div>
        </div>

        <div id="video-loader">
            <div class="spinner"></div>
        </div>
        
        <video id="my-video" class="video-js vjs-default-skin vjs-big-play-centered" controls playsinline poster="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1920&auto=format&fit=crop">
            <source src="/manifest?url={{ target_url | urlencode }}&priority={{ priority }}" type="application/x-mpegURL">
        </video>
        
    </div>

    <script src="https://vjs.zencdn.net/8.10.0/video.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            // Instantiate video framework engine without autoplay parameter overrides
            const player = videojs('my-video', {
                preload: 'metadata',
                autoplay: false, 
                controls: true,
                fluid: false,
                html5: {
                    vhs: {
                        overrideNative: true,
                        maxBufferLength: 45,
                        enableLowInitialPlaylist: true,
                        fastStart: true
                    }
                }
            });

            player.ready(function() {
                const controlBar = player.getChild('controlBar');
                const downloadBtn = document.createElement('div');
                downloadBtn.className = 'vjs-download-control vjs-control vjs-button';
                downloadBtn.title = 'Open Media Source';
                downloadBtn.innerHTML = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 20h14v-2H5v2zM19 9h-4V3H9v6H5l7 7 7-7z"/></svg>`;
                
                const currentSrc = player.src();
                const urlParams = new URLSearchParams(currentSrc.split('?')[1]);
                const targetM3u8Url = urlParams.get('url');
                const decodedUrl = targetM3u8Url ? decodeURIComponent(targetM3u8Url) : currentSrc;
                
                document.getElementById('title-link').href = decodedUrl;

                downloadBtn.addEventListener('click', function() {
                    window.open(decodedUrl, '_blank');
                });
                controlBar.el().appendChild(downloadBtn);
                
                // Remove initial load screen since user must explicitly press play
                const loader = document.getElementById('video-loader');
                if (loader) {
                    loader.style.opacity = '0';
                    setTimeout(() => loader.remove(), 300);
                }
            });

            document.getElementById('embed-share-btn').addEventListener('click', function() {
                if (navigator.share) {
                    navigator.share({
                        title: document.title,
                        url: window.location.href
                    }).catch(console.error);
                } else {
                    navigator.clipboard.writeText(window.location.href);
                    alert("Share link copied to clipboard.");
                }
            });
        });
    </script>
</body>
</html>
"""


# --- ROUTE HANDLERS ---

@app.route('/')
def index():
    return render_template_string(INDEX_TEMPLATE)


@app.route('/download', methods=['POST', 'GET'])
def render_player():
    user_input = request.form.get('id_or_url', '').strip() if request.method == 'POST' else request.args.get('id_or_url', '').strip()

    if not user_input:
        return "Missing identity context parameter.", 400

    referer = request.headers.get("Referer", "")
    priority_flag = "high" if INTERNAL_INFRASTRUCTURE_HOST in referer else "standard"

    if "dailymotion.com" in user_input:
        target_url = user_input if user_input.startswith(("http://", "https://")) else f"https://{user_input}"
    else:
        target_url = f"https://www.dailymotion.com/video/{user_input}"

    ydl_opts = {
        'format': 'best/any', 
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,              
        'check_formats': 'cached',          
        'extract_flat': False,
        'impersonate': ImpersonateTarget.from_str('chrome'),
        'socket_timeout': 5,                
        'extractor_args': {
            'dailymotion': {
                'pubkey': [''],             
            }
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            
            if not info:
                return "yt_dlp failed to extract a valid metadata envelope.", 500
                
            formats = info.get('formats', [])
            hls_streams = [f for f in formats if 'm3u8' in str(f.get('url','')) or 'hls' in str(f.get('format_id','')).lower()]
            m3u8_url = hls_streams[-1].get('url') if hls_streams else info.get('url')

            if not m3u8_url and formats:
                m3u8_url = formats[-1].get('url')

            if not m3u8_url:
                return "No playable stream paths found within the yt_dlp response object.", 404

            return render_template_string(
                PLAYER_TEMPLATE, 
                title=info.get('title', 'Native Stream Source'),
                target_url=m3u8_url,
                priority=priority_flag
            )
            
    except Exception as error:
        # --- CRITICAL FALLBACK TRIGGER ---
        # If extraction drops an error, we immediately fire a separate update check 
        # in a thread so the current visitor doesn't get blocked by an entirely frozen process loop.
        print(f"[Extraction Failure] Forcing emergency update check due to error: {error}")
        threading.Thread(target=run_pip_update).start()
        
        return f"Extraction Pipeline Exception Error: {str(error)}. A critical engine patch check has been initiated.", 500


@app.route('/manifest')
def proxy_m3u8():
    raw_m3u8_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_m3u8_url:
        return "Missing proxy reference targets", 400

    raw_m3u8_url = urllib.parse.unquote(raw_m3u8_url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        resp = http_pool.get(raw_m3u8_url, headers=headers, timeout=4)
    except Exception:
        return "Edge latency timeout during proxy resolution", 504

    base_url = raw_m3u8_url.rsplit('/', 1)[0] + '/'
    rewritten_lines = []

    for line in resp.text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if 'URI=' in line_stripped:
            def replace_uri(match):
                rel_path = match.group(1).strip('"\'')
                abs_url = urllib.parse.urljoin(base_url, rel_path)
                proxy_route = "/manifest" if (".m3u8" in rel_path or "manifest" in rel_path) else "/segment"
                return f'URI="{proxy_route}?url={urllib.parse.quote_plus(abs_url)}&priority={priority}"'
            line_stripped = re.sub(r'URI=(["\'].*?["\'])', replace_uri, line_stripped)
            rewritten_lines.append(line_stripped)

        elif not line_stripped.startswith('#'):
            full_url = line_stripped if line_stripped.startswith(('http://', 'https://')) else urllib.parse.urljoin(base_url, line_stripped)
            encoded_url = urllib.parse.quote_plus(full_url)
            
            if '.m3u8' in line_stripped or 'manifest' in line_stripped:
                rewritten_lines.append(f"/manifest?url={encoded_url}&priority={priority}")
            else:
                rewritten_lines.append(f"/segment?url={encoded_url}&priority={priority}")
        else:
            rewritten_lines.append(line_stripped)

    response = Response("\n".join(rewritten_lines), content_type="application/x-mpegURL")
    response.headers["Cache-Control"] = "public, max-age=3"
    return response


@app.route('/segment')
def proxy_ts_segment():
    raw_ts_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_ts_url:
        return "Missing segment sequence indices", 400

    raw_ts_url = urllib.parse.unquote(raw_ts_url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    timeout_val = 4 if priority == "high" else 5
    
    try:
        req = http_pool.get(raw_ts_url, headers=headers, stream=True, timeout=timeout_val)
        content_type = req.headers.get('Content-Type', 'video/MP2T')
        
        def stream_ts_data():
            for block in req.iter_content(chunk_size=1024 * 256):
                yield block

        response = Response(stream_ts_data(), content_type=content_type)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
    except Exception:
        return "Segment connection dropped", 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
