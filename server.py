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

# Configure an optimized connection pool for proxying
http_pool = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=200, pool_maxsize=200, pool_block=False)
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
            --accent-primary: #ff0000;
            --bg-base: #0f0f0f;
            --text-primary: #f1f1f1;
            --text-secondary: #aaaaaa;
            --gradient-top: linear-gradient(to bottom, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
        }

        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: "Roboto", Arial, sans-serif;
            overflow: hidden;
            user-select: none;
        }

        /* --- STAGE: FULL VIEWPORT OVERRIDE ENGINE --- */
        .viewport-player-hero {
            position: absolute;
            top: 0;
            left: 0;
            width: 100vw !important;
            height: 100vh !important;
            max-width: 100vw !important;
            max-height: 100vh !important;
            background-color: #000;
            z-index: 1;
            overflow: hidden;
        }

        .video-js {
            width: 100% !important;
            height: 100% !important;
            background-color: #000 !important;
        }

        .vjs-poster {
            background-size: contain !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-color: #000 !important;
        }

        .video-js video { 
            object-fit: contain !important; 
            width: 100% !important;
            height: 100% !important;
        }

        /* --- FLOATING HEADER --- */
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

        .video-js.vjs-user-inactive ~ #embed-header { 
            opacity: 0; 
            pointer-events: none;
        }
        .video-js.vjs-user-active ~ #embed-header,
        .video-js.vjs-paused ~ #embed-header { 
            opacity: 1; 
            pointer-events: auto;
        }

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
        }
        .embed-channel-icon-container img { width: 100%; height: 100%; object-fit: cover; }

        .embed-meta-text { display: flex; flex-direction: column; min-width: 0; }
        .embed-video-title { color: var(--text-primary); font-size: 1.1rem; font-weight: 500; margin: 0; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; text-shadow: 0 1px 3px rgba(0,0,0,0.9); }
        .embed-channel-name { color: var(--text-secondary); font-size: 0.85rem; margin-top: 2px; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; }
        
        .embed-icon-btn {
            background: transparent; border: none; color: var(--text-primary); cursor: pointer; padding: 8px;
            filter: drop-shadow(0px 1px 3px rgba(0,0,0,0.9)); pointer-events: auto;
        }

        /* --- INTERACTIVE END SCREEN --- */
        .player-endscreen-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.92);
            z-index: 12; 
            display: none; 
            flex-direction: column;
            justify-content: center;
            align-items: center;
            box-sizing: border-box;
            padding: 32px 24px;
        }

        .endscreen-title {
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 20px;
            align-self: flex-start;
            width: 100%;
            max-width: 720px;
            margin-left: auto;
            margin-right: auto;
            letter-spacing: 0.5px;
        }

        .endscreen-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            width: 100%;
            max-width: 720px;
            overflow-y: auto;
        }

        @media (max-width: 560px) {
            .endscreen-grid { grid-template-columns: 1fr; gap: 14px; }
            .endscreen-title { font-size: 1.1rem; margin-bottom: 14px; }
        }

        .endscreen-card {
            display: flex;
            gap: 14px;
            background: rgba(255, 255, 255, 0.04);
            padding: 10px;
            border-radius: 12px;
            text-decoration: none;
            color: inherit;
            align-items: center;
            border: 1px solid rgba(255,255,255,0.02);
            transition: background 0.2s ease, transform 0.2s ease;
        }
        .endscreen-card:hover { 
            background: rgba(255, 255, 255, 0.12);
            transform: translateY(-2px);
        }

        .endscreen-thumb-container {
            position: relative;
            width: 130px;
            height: 74px;
            flex-shrink: 0;
            border-radius: 6px;
            overflow: hidden;
            background: #111;
        }
        .endscreen-thumb-container img { width: 100%; height: 100%; object-fit: cover; }

        .endscreen-duration {
            position: absolute; bottom: 4px; right: 4px; background: rgba(0,0,0,0.85);
            color: #fff; padding: 2px 4px; border-radius: 3px; font-size: 0.68rem; font-weight: 600;
        }

        .endscreen-meta { display: flex; flex-direction: column; min-width: 0; }
        .endscreen-v-title {
            font-size: 0.88rem; font-weight: 500; line-height: 1.35; color: var(--text-primary);
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 4px;
        }
        .endscreen-v-creator { font-size: 0.78rem; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        /* --- VIDEO.JS CONTROL INTERFACE --- */
        .video-js .vjs-big-play-button {
            background-color: rgba(20, 20, 20, 0.85) !important; border: none !important; border-radius: 12px !important;
            width: 68px !important; height: 48px !important; line-height: 48px !important; margin-top: -24px !important; margin-left: -34px !important; z-index: 11;
        }
        .video-js:hover .vjs-big-play-button { background-color: var(--accent-primary) !important; }
        .video-js .vjs-control-bar { display: flex !important; background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0) 100%) !important; height: 48px !important; z-index: 11; }
        .video-js .vjs-progress-control { position: absolute !important; width: calc(100% - 24px) !important; height: 6px !important; top: -6px !important; left: 12px !important; display: flex !important; visibility: visible !important;}
        .video-js .vjs-play-progress { background: var(--accent-primary) !important; }
        .video-js .vjs-slider { background-color: rgba(255,255,255,0.2) !important; }
        
        .video-js .vjs-fullscreen-control { display: none !important; }
        
        .vjs-download-control, .vjs-custom-fullscreen-control { cursor: pointer; display: flex; align-items: center; justify-content: center; width: 40px; height: 100%; order: 99; }
        .vjs-download-control svg, .vjs-custom-fullscreen-control svg { width: 18px; height: 18px; fill: var(--text-primary); opacity: 0.8; }
        .vjs-download-control svg:hover, .vjs-custom-fullscreen-control svg:hover { opacity: 1; }

        /* --- MODERN MINIMALIST GLOW LOADER ENGINE --- */
        .video-js .vjs-loading-spinner {
            border: 3px solid rgba(255, 255, 255, 0.1) !important;
            border-top: 3px solid var(--accent-primary) !important;
            border-radius: 50% !important;
            width: 50px !important;
            height: 50px !important;
            margin: -25px 0 0 -25px !important;
            animation: vjs-spinner-spin 0.8s linear infinite !important;
            background: none !important;
        }
        .video-js .vjs-loading-spinner:before, 
        .video-js .vjs-loading-spinner:after {
            display: none !important;
        }
        @keyframes vjs-spinner-spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
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

                // 2. TRUE MOBILE COMPATIBLE HARDWARE FULLSCREEN
                const fsBtn = document.createElement('div');
                fsBtn.className = 'vjs-custom-fullscreen-control vjs-control vjs-button';
                fsBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>`;
                
                fsBtn.addEventListener('click', function() {
                    if (!player.isFullscreen()) {
                        player.requestFullscreen();
                        if (screen.orientation && screen.orientation.lock) {
                            screen.orientation.lock('landscape').catch(() => {});
                        }
                    } else {
                        player.exitFullscreen();
                        if (screen.orientation && screen.orientation.unlock) {
                            screen.orientation.unlock();
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
        # Avoid crashing running server systems on permission-locked cloud layers
        return f"Extraction Pipeline Exception Error: {str(error)}", 500

@app.route('/manifest')
def proxy_m3u8():
    raw_m3u8_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_m3u8_url:
        return "Missing proxy targets", 400

    raw_m3u8_url = urllib.parse.unquote(raw_m3u8_url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
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
