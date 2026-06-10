import os
import re
import sys
import threading
import time
import urllib.parse
import requests
from flask import Flask, request, Response, render_template_string 
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

app = Flask(__name__)

# Highly optimized connection pool for immediate data passthrough
http_pool = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=500,       # Bumped for high-concurrency scrubbing/seeking
    pool_maxsize=500, 
    pool_block=False
)
http_pool.mount('http://', adapter)
http_pool.mount('https://', adapter)

INTERNAL_INFRASTRUCTURE_HOST = "cggames.pythonanywhere.com"

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NebulaView Core</title>
    <style>
        body {
            background: radial-gradient(circle at center, #0c0a0f 0%, #050506 100%);
            color: #f4f4f5;
            font-family: sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
    </style>
</head>
<body>
    <h1>NebulaView Mobile Active</h1>
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
:root {
    --accent: #ff3b3b;

    /* CONTROLLED GLASS SYSTEM (IMPORTANT FIX) */
    --glass-1: rgba(255,255,255,0.06);
    --glass-2: rgba(255,255,255,0.09);
    --glass-3: rgba(255,255,255,0.14);

    --blur-1: blur(10px);
    --blur-2: blur(16px);
    --blur-3: blur(22px);

    --text: rgba(255,255,255,0.92);
    --muted: rgba(255,255,255,0.6);

    --shadow: 0 18px 45px rgba(0,0,0,0.55);
}

/* BACKGROUND (LESS DISTRACTING = BIG IMPROVEMENT) */
html, body {
    margin: 0;
    height: 100%;
    overflow: hidden;
    background: radial-gradient(circle at top, #141824 0%, #07080c 70%);
    font-family: Arial, sans-serif;
    color: var(--text);
}

/* PLAYER WRAPPER (LIGHT GLASS ONLY) */
.viewport-player-hero {
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.25);
}

/* VIDEO (KEEP CLEAN — IMPORTANT) */
.video-js {
    width: 100% !important;
    height: 100% !important;
    background: #000 !important;
}

.video-js video {
    object-fit: contain !important;
}

/* =========================
   TOP HUD (STRONGEST GLASS LAYER)
========================= */
.embed-floating-header {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    padding: 14px 16px 40px;

    background: rgba(20,20,28,0.35);
    backdrop-filter: var(--blur-3);
    -webkit-backdrop-filter: var(--blur-3);

    border-bottom: 1px solid rgba(255,255,255,0.08);
    box-shadow: var(--shadow);

    display: flex;
    justify-content: space-between;
    z-index: 10;
}

/* AVATAR (SOFT GLASS ORB) */
.embed-channel-icon-container {
    width: 42px;
    height: 42px;
    border-radius: 50%;

    background: rgba(255,255,255,0.08);
    backdrop-filter: var(--blur-2);

    border: 1px solid rgba(255,255,255,0.12);

    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;

    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}

/* TEXT (CLEANER, LESS GLOW) */
.embed-video-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
}

.embed-channel-name {
    font-size: 0.85rem;
    color: var(--muted);
}

/* =========================
   BUTTONS (MODERN GLASS, NOT OVERDONE)
========================= */
.embed-icon-btn {
    background: rgba(255,255,255,0.07);
    backdrop-filter: var(--blur-2);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 9px;
    transition: 0.2s ease;
}

.embed-icon-btn:hover {
    background: rgba(255,255,255,0.12);
    transform: translateY(-2px);
}

/* =========================
   END SCREEN (LIGHTER GLASS)
========================= */
.player-endscreen-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.65);
    backdrop-filter: var(--blur-3);
    display: none;
    align-items: center;
    justify-content: center;
    flex-direction: column;
}

/* CARDS (MOST IMPORTANT FIX) */
.endscreen-card {
    display: flex;
    gap: 12px;
    padding: 10px;
    border-radius: 14px;

    background: rgba(255,255,255,0.06);
    backdrop-filter: var(--blur-2);

    border: 1px solid rgba(255,255,255,0.1);

    box-shadow: var(--shadow);
    transition: 0.25s ease;
}

.endscreen-card:hover {
    transform: translateY(-4px);
    background: rgba(255,255,255,0.1);
}

/* THUMB (LESS GLOW, MORE CLEAN) */
.endscreen-thumb-container {
    width: 130px;
    height: 74px;
    border-radius: 10px;
    overflow: hidden;
}

/* =========================
   CONTROL BAR (LESS NOISE)
========================= */
.video-js .vjs-control-bar {
    background: rgba(15,15,20,0.4) !important;
    backdrop-filter: var(--blur-3);
    border-top: 1px solid rgba(255,255,255,0.08);
}

.video-js .vjs-play-progress {
    background: var(--accent) !important;
    box-shadow: 0 0 10px var(--accent);
}

/* BIG PLAY BUTTON (SIMPLIFIED) */
.video-js .vjs-big-play-button {
    background: rgba(255,255,255,0.08) !important;
    backdrop-filter: var(--blur-2);
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 14px !important;
}
</style>
</head>
<body>

    <div class="viewport-player-hero" id="player-view-wrapper">
        
        <video id="my-video" class="video-js vjs-default-skin vjs-big-play-centered" controls playsinline webkit-playsinline></video>

        <div class="embed-floating-header" id="embed-header">
            <div class="embed-header-left">
                <div class="embed-channel-icon-container" id="avatar-container-hud"></div>
                <div class="embed-meta-text">
                    <span class="embed-video-title">{{ title }}</span>
                    <span class="embed-channel-name">{{ author_name if author_name else "Verified Creator" }}</span>
                </div>
            </div>
            <div class="embed-header-actions">
                <button class="embed-icon-btn" id="embed-share-btn">
                    <svg style="width:22px;height:22px;fill:currentColor" viewBox="0 0 24 24"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.8 2.04.8 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg>
                </button>
            </div>
        </div>

        <div class="player-endscreen-overlay" id="endscreen-display">
            <div class="endscreen-title">Up Next</div>
            <div class="endscreen-grid" id="endscreen-grid-items"></div>
        </div>
        
    </div>

    <script src="https://vjs.zencdn.net/8.10.0/video.js"></script>
    <script>
        const targetVideoId = "{{ current_video_id }}";

        if ('mediaSession' in navigator) {
            navigator.mediaSession.metadata = new MediaMetadata({
                title: "{{ title }}",
                artist: "{{ author_name if author_name else 'Verified Creator' }}",
                artwork: [{ src: "{{ forced_poster }}", sizes: '512x512', type: 'image/jpeg' }]
            });
        }

        function resolveMediaAssets() {
            let posterUrl = "{{ forced_poster }}".trim();
            if (!posterUrl || posterUrl === "None" || posterUrl === "") {
                posterUrl = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1920";
            }
            document.getElementById('my-video').setAttribute('poster', posterUrl);

            const creatorName = "{{ author_name }}".trim() || "Verified Creator";
            const passedAvatar = "{{ author_avatar_url }}".trim();
            const hudIconContainer = document.getElementById('avatar-container-hud');

            if (passedAvatar && passedAvatar !== "None" && passedAvatar !== "") {
                hudIconContainer.innerHTML = `<img src="${passedAvatar}">`;
            } else {
                const firstLetter = creatorName.charAt(0).toUpperCase();
                const colors = ['#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3'];
                hudIconContainer.style.backgroundColor = colors[firstLetter.charCodeAt(0) % colors.length];
                hudIconContainer.textContent = firstLetter;
            }
        }

        async function runLazyEndscreenGeneration() {
            if(!targetVideoId) return;
            try {
                const response = await fetch(`https://api.dailymotion.com/video/${targetVideoId}/related?fields=id,title,owner.username,thumbnail_240_url,duration&limit=4`);
                const data = await response.json();
                if(data && data.list) {
                    const gridContainer = document.getElementById('endscreen-grid-items');
                    gridContainer.innerHTML = '';
                    
                    data.list.forEach(item => {
                        const mins = Math.floor(item.duration / 60);
                        const secs = String(item.duration % 60).padStart(2, '0');
                        
                        const element = document.createElement('a');
                        element.className = 'endscreen-card';
                        element.href = `/download?id_or_url=${item.id}`;
                        element.innerHTML = `
                            <div class="endscreen-thumb-container">
                                <img src="${item.thumbnail_240_url}">
                                <div class="endscreen-duration">${mins}:${secs}</div>
                            </div>
                            <div class="endscreen-meta">
                                <div class="endscreen-v-title">${item.title}</div>
                                <div class="endscreen-v-creator">${item['owner.username'] || 'Creator'}</div>
                            </div>
                        `;
                        gridContainer.appendChild(element);
                    });
                    
                    document.getElementById('endscreen-display').style.display = 'flex';
                }
            } catch(e) {
                console.error("Delayed endscreen engine exception:", e);
            }
        }

        document.addEventListener("DOMContentLoaded", function() {
            resolveMediaAssets();

            const player = videojs('my-video', {
                preload: 'auto',
                autoplay: false, 
                controls: true,
                fluid: false, 
                playsinline: true, 
                webkitPlaysinline: true,
                preferFullWindow: false, 
                controlBar: {
                    progressControl: { enableTouchPoints: true }
                }
            });

            player.src({
                src: "/manifest?url={{ stream_url | urlencode }}&priority={{ priority }}",
                type: 'application/x-mpegURL',
                exact_seeking: true 
            });

            player.on('ended', function() {
                runLazyEndscreenGeneration();
            });

            player.on('play', function() {
                document.getElementById('endscreen-display').style.display = 'none';
            });

            player.ready(function() {
                const controlBar = player.getChild('controlBar');

                // 1. DOWNLOAD INTERACTION BUTTON
                const downloadBtn = document.createElement('div');
                downloadBtn.className = 'vjs-download-control vjs-control vjs-button';
                downloadBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M5 20h14v-2H5v2zM19 9h-4V3H9v6H5l7 7 7-7z"/></svg>`;
                
                const currentSrc = player.src();
                const urlParams = new URLSearchParams(currentSrc.split('?')[1]);
                const targetM3u8Url = urlParams.get('url');
                const decodedUrl = targetM3u8Url ? decodeURIComponent(targetM3u8Url) : currentSrc;
                downloadBtn.addEventListener('click', function() { window.open(decodedUrl, '_blank'); });
                controlBar.el().appendChild(downloadBtn);

                // 2. UNRESTRICTED DIRECT HARDWARE MOBILE FULLSCREEN BYPASS
                const fsBtn = document.createElement('div');
                fsBtn.className = 'vjs-custom-fullscreen-control vjs-control vjs-button';
                fsBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>`;
                
                fsBtn.addEventListener('click', function() {
                    // Pull direct baseline DOM node created by the video layer engine
                    const videoEl = document.getElementById('my-video_html5_api') || player.tech({ IWillNotUseThisInPlugins: true }).el();

                    if (videoEl) {
                        // Direct iOS Safari Pipeline execution
                        if (videoEl.webkitEnterFullscreen) {
                            videoEl.webkitEnterFullscreen();
                        } 
                        // Direct Android Chrome / Standard W3C execution
                        else if (videoEl.requestFullscreen) {
                            videoEl.requestFullscreen();
                        } else if (videoEl.msRequestFullscreen) {
                            videoEl.msRequestFullscreen();
                        } else if (videoEl.mozRequestFullScreen) {
                            videoEl.mozRequestFullScreen();
                        } else {
                            player.requestFullscreen();
                        }

                        // Force rotation configuration lock if ecosystem supports it
                        if (screen.orientation && screen.orientation.lock) {
                            screen.orientation.lock('landscape').catch(() => {});
                        }
                    }
                });
                controlBar.el().appendChild(fsBtn);
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
        'socket_timeout': 5
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if not info:
                return "Extraction failed.", 500
                
            formats = info.get('formats', [])
            hls_streams = [f for f in formats if 'm3u8' in str(f.get('url','')) or 'hls' in str(f.get('format_id','')).lower()]
            m3u8_url = hls_streams[-1].get('url') if hls_streams else info.get('url')

            if not m3u8_url and formats:
                m3u8_url = formats[-1].get('url')

            if not m3u8_url:
                return "No playable stream paths found.", 404

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
        return f"Extraction Pipeline Exception Error: {str(error)}", 500

@app.route('/manifest')
def proxy_m3u8():
    raw_m3u8_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_m3u8_url:
        return "Missing proxy targets", 400

    raw_m3u8_url = urllib.parse.unquote(raw_m3u8_url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
        'Accept': '*/*',
    }
    
    try:
        resp = http_pool.get(raw_m3u8_url, headers=headers, timeout=4)
    except Exception:
        return "Timeout during proxy resolution", 504

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

    # CRITICAL: Use correct Apple HTTP Live Streaming Content Type
    response = Response("\n".join(rewritten_lines), content_type="application/vnd.apple.mpegurl")
    response.headers["Cache-Control"] = "public, max-age=2"
    return response

@app.route('/segment')
def proxy_ts_segment():
    raw_ts_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_ts_url:
        return "Missing segment sequence indices", 400

    raw_ts_url = urllib.parse.unquote(raw_ts_url)
    
    # Mirror matching engine profiles so Dailymotion connection tracks don't close
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }
    timeout_val = 4 if priority == "high" else 6
    
    try:
        req = http_pool.get(raw_ts_url, headers=headers, stream=True, timeout=timeout_val)
        content_type = req.headers.get('Content-Type', 'video/MP2T')
        
        # Pull original length so client native seekers can compute byte range offsets instantly
        content_length = req.headers.get('Content-Length')

        def stream_ts_data():
            # Drop block size to 16KB for zero pipeline lag when fast forwarding
            for block in req.iter_content(chunk_size=1024 * 16):
                if block:
                    yield block

        response = Response(stream_ts_data(), content_type=content_type)
        if content_length:
            response.headers['Content-Length'] = content_length
            
        # Keep aggressive edge caching for instant segment re-reads when seeking backwards
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
    except Exception:
        return "Segment connection dropped", 502

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
