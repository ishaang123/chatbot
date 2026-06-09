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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>{{ title }}</title>
    <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
    <style>
        /* --- CORE DESIGN MODULE --- */
        :root {
            --accent-primary: #ff0000;
            --bg-base: #0f0f0f;
            --text-primary: #f1f1f1;
            --text-secondary: #aaaaaa;
            --border-subtle: rgba(255, 255, 255, 0.1);
            --gradient-top: linear-gradient(to bottom, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
        }

        /* --- INTERACTION LOCKS --- */
        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: "Roboto", "YouTube Noto", Arial, sans-serif;
            overflow: hidden; /* Lock scroll container to prevent messy lower info views */
            
            -webkit-text-size-adjust: 100%;
            -webkit-tap-highlight-color: rgba(0, 0, 0, 0) !important;
            -webkit-touch-callout: none !important;
            -webkit-user-select: none !important;
            user-select: none;
        }

        /* --- STAGE A: VIEWPORT LAYER (FULLY DYNAMIC DIMENSIONS) --- */
        .viewport-player-hero {
            position: relative;
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
            background-color: #000;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }

        /* Force Video.js to respect fluid aspects without structural collapsing */
        .video-js {
            width: 100% !important;
            height: auto !important;
            background-color: #000 !important;
        }

        /* Prevent portrait/9:16 thumbnails from clipping or layout bursting */
        .vjs-poster {
            background-size: contain !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-color: #000 !important;
            display: block !important;
        }

        /* Ensure actual video content scales safely inside the viewport engine */
        .video-js video {
            object-fit: contain !important;
        }

        /* --- YT-STYLE FLOATING OVERLAY --- */
        .embed-floating-header {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            padding: 24px 24px 48px 24px;
            background: var(--gradient-top);
            z-index: 10;
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            box-sizing: border-box;
            pointer-events: none;
            opacity: 1;
            transition: opacity 0.25s ease;
        }

        .vjs-has-started.vjs-user-inactive .embed-floating-header { opacity: 0; }
        .embed-header-left { display: flex; align-items: center; gap: 12px; pointer-events: auto; min-width: 0; }

        .embed-channel-icon-container {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            background: #272727;
            font-weight: 700;
            color: #fff;
            font-size: 1.1rem;
        }
        .embed-channel-icon-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .embed-meta-text { display: flex; flex-direction: column; min-width: 0; }
        .embed-video-title { color: var(--text-primary); font-size: 1.2rem; font-weight: 500; margin: 0; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; text-shadow: 0 1px 3px rgba(0,0,0,0.9); }
        .embed-channel-name { color: var(--text-secondary); font-size: 0.9rem; margin-top: 2px; text-shadow: 0 1px 2px rgba(0,0,0,0.9); white-space: nowrap; text-overflow: ellipsis; overflow: hidden; }
        .embed-header-actions { display: flex; align-items: center; pointer-events: auto; flex-shrink: 0; }
        
        .embed-icon-btn {
            background: transparent;
            border: none;
            color: var(--text-primary);
            cursor: pointer;
            padding: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            filter: drop-shadow(0px 1px 3px rgba(0,0,0,0.9));
        }

        /* --- STAGE B: UP NEXT RECOMMENDATION SLIDER --- */
        .up-next-section-frame {
            max-width: 800px;
            margin: 16px auto 0 auto;
            padding: 0 16px;
            box-sizing: border-box;
        }

        .up-next-header-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin: 0 0 12px 0;
            color: var(--text-primary);
            letter-spacing: 0.3px;
        }

        .up-next-scroll-container {
            display: flex;
            gap: 12px;
            overflow-x: auto;
            padding-bottom: 8px;
            scrollbar-width: none; /* Firefox */
        }
        .up-next-scroll-container::-webkit-scrollbar { display: none; } /* Chrome/Safari */

        .up-next-card {
            display: flex;
            flex-direction: column;
            width: 160px;
            flex-shrink: 0;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
        }

        .up-next-thumbnail-wrapper {
            position: relative;
            width: 160px;
            height: 90px;
            border-radius: 8px;
            overflow: hidden;
            background-color: #1a1a1a;
        }
        .up-next-thumbnail-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .up-next-duration-badge {
            position: absolute;
            bottom: 4px;
            right: 4px;
            background: rgba(0,0,0,0.8);
            color: #fff;
            padding: 2px 4px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 600;
        }

        .up-next-card-title {
            font-size: 0.82rem;
            font-weight: 500;
            line-height: 1.3;
            margin: 6px 0 2px 0;
            color: var(--text-primary);
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .up-next-card-creator {
            font-size: 0.75rem;
            color: var(--text-secondary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* --- VIDEO.JS MODIFICATION MATRIX --- */
        .video-js .vjs-big-play-button {
            background-color: rgba(20, 20, 20, 0.85) !important;
            border: none !important;
            border-radius: 12px !important;
            width: 68px !important;
            height: 48px !important;
            line-height: 48px !important;
            margin-top: -24px !important;
            margin-left: -34px !important;
            z-index: 11;
        }
        .video-js:hover .vjs-big-play-button { background-color: var(--accent-primary) !important; }
        
        .video-js .vjs-control-bar { 
            display: flex !important;
            background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0) 100%) !important; 
            height: 48px !important; 
        }
        .video-js .vjs-progress-control { 
            position: absolute !important; 
            width: calc(100% - 24px) !important; 
            height: 6px !important; 
            top: -6px !important; 
            left: 12px !important; 
            display: flex !important;
            visibility: visible !important;
        }
        .video-js .vjs-play-progress { background: var(--accent-primary) !important; }
        .video-js .vjs-slider { background-color: rgba(255,255,255,0.2) !important; }

        .vjs-download-control { cursor: pointer; display: flex; align-items: center; justify-content: center; width: 40px; height: 100%; order: 99; }
        .vjs-download-control svg { width: 18px; height: 18px; fill: var(--text-primary); opacity: 0.8; }
    </style>
</head>
<body>

    <div class="viewport-player-hero">
        
        <div class="embed-floating-header" id="embed-header">
            <div class="embed-header-left">
                <div class="embed-channel-icon-container" id="avatar-container-hud"></div>
                <div class="embed-meta-text">
                    <span class="embed-video-title">{{ title }}</span>
                    <span class="embed-channel-name">{{ author_name if author_name else "Verified Creator" }}</span>
                </div>
            </div>
            <div class="embed-header-actions">
                <button class="embed-icon-btn" id="embed-share-btn" title="Share Link">
                    <svg style="width:22px;height:22px;fill:currentColor" viewBox="0 0 24 24"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.8 2.04.8 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg>
                </button>
            </div>
        </div>

        <video id="my-video" class="video-js vjs-default-skin vjs-big-play-centered" controls playsinline webkit-playsinline></video>
        
    </div>

    <div class="up-next-section-frame">
        <h2 class="up-next-header-title">Up Next</h2>
        <div class="up-next-scroll-container" id="up-next-list">
            </div>
    </div>

    <script src="https://vjs.zencdn.net/8.10.0/video.js"></script>
    <script>
        // Setup configuration metrics
        const targetVideoId = "{{ current_video_id }}";

        function resolveMediaAssets() {
            let posterUrl = "{{ forced_poster }}".trim();
            if (!posterUrl || posterUrl === "None" || posterUrl === "") {
                posterUrl = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1920";
            }
            
            const myVideo = document.getElementById('my-video');
            myVideo.setAttribute('poster', posterUrl);

            // --- RESOLVE CREATOR PROFILE AVATAR ---
            const creatorName = "{{ author_name }}".trim() || "Verified Creator";
            const passedAvatar = "{{ author_avatar_url }}".trim();
            const hudIconContainer = document.getElementById('avatar-container-hud');

            if (passedAvatar && passedAvatar !== "None" && passedAvatar !== "") {
                hudIconContainer.innerHTML = `<img src="${passedAvatar}" alt="Avatar">`;
            } else {
                const firstLetter = creatorName.charAt(0).toUpperCase();
                const colors = ['#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3'];
                hudIconContainer.style.backgroundColor = colors[firstLetter.charCodeAt(0) % colors.length];
                hudIconContainer.textContent = firstLetter;
            }
        }

        // Fetch recommendations directly using Dailymotion's Endpoint Architecture
        async function fetchUpNextFeed() {
            if(!targetVideoId) return;
            try {
                const response = await fetch(`https://api.dailymotion.com/video/${targetVideoId}/related?fields=id,title,owner.username,thumbnail_240_url,duration&limit=6`);
                const data = await response.json();
                if(data && data.list) {
                    const listContainer = document.getElementById('up-next-list');
                    listContainer.innerHTML = '';
                    
                    data.list.forEach(item => {
                        const mins = Math.floor(item.duration / 60);
                        const secs = String(item.duration % 60).padStart(2, '0');
                        
                        const card = document.createElement('a');
                        card.className = 'up-next-card';
                        card.href = `/download?id_or_url=${item.id}`;
                        card.innerHTML = `
                            <div class="up-next-thumbnail-wrapper">
                                <img src="${item.thumbnail_240_url}" alt="thumb">
                                <div class="up-next-duration-badge">${mins}:${secs}</div>
                            </div>
                            <div class="up-next-card-title">${item.title}</div>
                            <div class="up-next-card-creator">${item['owner.username'] || 'Creator'}</div>
                        `;
                        listContainer.appendChild(card);
                    });
                }
            } catch(e) {
                console.error("Dailymotion API tracking exception:", e);
            }
        }

        document.addEventListener("DOMContentLoaded", function() {
            resolveMediaAssets();
            fetchUpNextFeed();

            // Configured Engine for exact seeking handling across 16:9 and 9:16 files
            const player = videojs('my-video', {
                preload: 'auto',
                autoplay: false, 
                controls: true,
                fluid: true, 
                playsinline: true,
                webkitPlaysinline: true,
                controlBar: {
                    progressControl: {
                        enableTouchPoints: true // High accuracy mobile resolution scrubbing
                    }
                }
            });

            // Set source explicitly via JavaScript to maintain precise playback bounds
            player.src({
                src: "/manifest?url={{ stream_url | urlencode }}&priority={{ priority }}",
                type: 'application/x-mpegURL',
                exact_seeking: true // Enforces native presentation-timestamp alignment
            });

            player.ready(function() {
                const controlBar = player.getChild('controlBar');
                const downloadBtn = document.createElement('div');
                downloadBtn.className = 'vjs-download-control vjs-control vjs-button';
                downloadBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M5 20h14v-2H5v2zM19 9h-4V3H9v6H5l7 7 7-7z"/></svg>`;
                
                const currentSrc = player.src();
                const urlParams = new URLSearchParams(currentSrc.split('?')[1]);
                const targetM3u8Url = urlParams.get('url');
                const decodedUrl = targetM3u8Url ? decodeURIComponent(targetM3u8Url) : currentSrc;

                downloadBtn.addEventListener('click', function() { window.open(decodedUrl, '_blank'); });
                controlBar.el().appendChild(downloadBtn);
            });

            document.getElementById('embed-share-btn').addEventListener('click', function() {
                if (navigator.share) {
                    navigator.share({ title: document.title, url: window.location.href }).catch(console.error);
                } else {
                    navigator.clipboard.writeText(window.location.href);
                    alert("Link copied to clipboard memory.");
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

    # Extract clean video ID context for use within internal API queries
    video_id_match = re.search(r'(?:dailymotion\.com\/video\/|dai\.ly\/)([a-zA-Z0-9]+)', user_input)
    clean_video_id = video_id_match.group(1) if video_id_match else user_input

    if "dailymotion.com" in user_input or "dai.ly" in user_input:
        target_url = user_input if user_input.startswith(("http://", "https://")) else f"https://{user_input}"
    else:
        target_url = f"https://www.dailymotion.com/video/{clean_video_id}"

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

            # --- DYNAMIC METADATA EXTRACTION PIPELINE ---
            video_thumbnail = info.get('thumbnail') or (info.get('thumbnails') and info.get('thumbnails')[-1].get('url')) or ""
            creator_name = info.get('uploader') or info.get('channel') or "Verified Creator"
            creator_avatar = info.get('uploader_url') or "" 
            
            return render_template_string(
                PLAYER_TEMPLATE, 
                title=info.get('title', 'Native Stream Source'),
                current_video_id=clean_video_id,
                target_url=target_url, 
                stream_url=m3u8_url,   
                priority=priority_flag,
                author_name=creator_name,
                author_avatar_url=creator_avatar,
                forced_poster=video_thumbnail 
            )
            
    except Exception as error:
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
