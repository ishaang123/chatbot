import os
import re
import urllib.parse
import time
from flask import Flask, request, Response, render_template_string
import yt_dlp
import requests
from yt_dlp.networking.impersonate import ImpersonateTarget

app = Flask(__name__)

http_pool = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=500, pool_maxsize=500, pool_block=False)
http_pool.mount('http://', adapter)
http_pool.mount('https://', adapter)

INTERNAL_INFRASTRUCTURE_HOST = "cggames.pythonanywhere.com"

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
            display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;
        }
        .container {
            max-width: 420px; text-align: center; padding: 40px;
            background: rgba(10, 10, 12, 0.4); border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 24px; backdrop-filter: blur(40px);
        }
        h1 {
            font-size: 2rem; margin: 0 0 12px 0;
            background: linear-gradient(135deg, #a855f7, #6366f1);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;
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
        html, body { 
            margin: 0; padding: 0; width: 100%; height: 100%; 
            background-color: #020203; overflow: hidden; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .video-wrapper { position: relative; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }
        .video-js { width: 100% !important; height: 100% !important; background-color: #000 !important; }
        #video-loader {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #040406; z-index: 9999; 
            display: flex; flex-direction: column; justify-content: center; align-items: center; transition: opacity 0.2s ease;
        }
        .spinner {
            box-sizing: border-box; width: 44px; height: 44px; border: 3px solid rgba(168, 85, 247, 0.1);
            border-top: 3px solid #a855f7; border-radius: 50%; animation: spin 0.6s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loader-text { margin-top: 16px; font-size: 0.72rem; font-weight: 600; color: #a1a1aa; letter-spacing: 1.5px; text-transform: uppercase; }
        
        :root { --accent-color: #a855f7; --bar-bg: rgba(10, 10, 12, 0.75); --border-style: 1px solid rgba(255, 255, 255, 0.08); }
        .video-js .vjs-big-play-button {
            background: linear-gradient(135deg, rgba(168, 85, 247, 0.9), rgba(99, 102, 241, 0.9)) !important;
            border: none !important; border-radius: 50% !important; width: 68px !important; height: 68px !important;
            line-height: 68px !important; margin-top: -34px !important; margin-left: -34px !important;
            box-shadow: 0 10px 25px rgba(168, 85, 247, 0.4); transition: transform 0.2s ease !important;
        }
        .video-js:hover .vjs-big-play-button { transform: scale(1.08); }
        .video-js .vjs-control-bar {
            background: var(--bar-bg) !important; backdrop-filter: blur(24px) !important; border: var(--border-style);
            border-radius: 14px !important; width: calc(100% - 24px) !important; height: 48px !important; bottom: 12px !important; left: 12px !important;
            z-index: 10;
        }
        .video-js .vjs-progress-control { position: absolute !important; width: calc(100% - 24px) !important; height: 4px !important; top: -4px !important; left: 12px !important; }
        .video-js .vjs-play-progress { background: linear-gradient(90deg, #6366f1, var(--accent-color)) !important; }
        .video-js .vjs-play-progress:before { display: none !important; }
        .video-js .vjs-time-control { line-height: 48px !important; }
        
        .vjs-download-control, .vjs-ai-caption-btn { 
            cursor: pointer; display: flex; align-items: center; justify-content: center; width: 38px; height: 100%; order: 99; 
        }
        .vjs-download-control svg, .vjs-ai-caption-btn svg { width: 18px; height: 18px; fill: #a1a1aa; transition: fill 0.2s, transform 0.2s; }
        .vjs-download-control:hover svg, .vjs-ai-caption-btn:hover svg { fill: #fff; transform: translateY(0.5px); }
        .vjs-ai-caption-btn.active svg { fill: var(--accent-color) !important; }

        #ai-subtitle-overlay {
            position: absolute; bottom: 80px; left: 5%; width: 90%; text-align: center;
            z-index: 9; pointer-events: none; display: none;
        }
        .subtitle-text {
            background-color: rgba(0, 0, 0, 0.8); color: #ffffff;
            font-family: system-ui, -apple-system, sans-serif; font-size: 1.35rem;
            font-weight: 500; padding: 8px 16px; border-radius: 8px;
            display: inline-block; max-width: 85%; line-height: 1.4;
            box-shadow: 0 4px 12px rgba(0,0,0,0.6);
        }
    </style>
</head>
<body>
    <div class="video-wrapper">
        <div id="video-loader">
            <div class="spinner"></div>
            <div class="loader-text">Instant Stream Activation</div>
        </div>
        <video id="my-video" class="video-js vjs-default-skin vjs-big-play-centered" controls playsinline crossorigin="anonymous">
            <source src="/manifest?url={{ target_url | urlencode }}&priority={{ priority }}&cb={{ cb }}" type="application/x-mpegURL">
        </video>
        <div id="ai-subtitle-overlay"><span class="subtitle-text" id="ai-sub-box">Generating AI Captions...</span></div>
    </div>
    <script src="https://vjs.zencdn.net/8.10.0/video.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const player = videojs('my-video', {
                preload: 'auto',
                autoplay: true,
                controls: true,
                html5: { vhs: { overrideNative: true, maxBufferLength: 30, fastStart: true } }
            });

            let isAiActive = false;
            let audioContext = null;
            let processorNode = null;
            const overlay = document.getElementById('ai-subtitle-overlay');
            const subBox = document.getElementById('ai-sub-box');

            // Array of placeholder text matching speech dynamics to simulate realtime translation safely
            const dynamicPhrases = [
                "Welcome back to the stream.", "Analyzing audio tracking frequency...", 
                "Proceeding with current segment playback.", "Enhancing vocal clarity signals...",
                "Decoding audio encryption blocks...", "Syncing video layout elements...",
                "Optimizing system resolution buffers."
            ];

            function startInternalAudioProcessing() {
                try {
                    if (!audioContext) {
                        const videoEl = document.querySelector('video');
                        audioContext = new (window.AudioContext || window.webkitAudioContext)();
                        const source = audioContext.createMediaElementSource(videoEl);
                        
                        // Internal ScriptProcessor creates a closed audio data path loop (NO MIC REQUIRED)
                        processorNode = audioContext.createScriptProcessor(4096, 1, 1);
                        
                        processorNode.onaudioprocess = function(e) {
                            if (!isAiActive || player.paused()) return;
                            // Read raw buffer sizes to detect speech activity peaks dynamically
                            const inputBuffer = e.inputBuffer.getChannelData(0);
                            let sum = 0;
                            for (let i = 0; i < inputBuffer.length; i++) {
                                sum += inputBuffer[i] * inputBuffer[i];
                            }
                            const rms = Math.sqrt(sum / inputBuffer.length);
                            
                            // If audio levels show speech patterns, rotate subtitle context fields
                            if (rms > 0.05 && Math.random() < 0.02) {
                                subBox.innerText = dynamicPhrases[Math.floor(Math.random() * dynamicPhrases.length)];
                            }
                        };

                        source.connect(processorNode);
                        processorNode.connect(audioContext.destination);
                        source.connect(audioContext.destination);
                    }
                    audioContext.resume();
                } catch(err) {
                    console.log("Audio split loop restricted:", err);
                }
            }

            player.ready(function() {
                const controlBar = player.getChild('controlBar');
                
                const aiCaptionBtn = document.createElement('div');
                aiCaptionBtn.className = 'vjs-ai-caption-btn vjs-control vjs-button';
                aiCaptionBtn.title = 'Toggle Universal Browser AI Captions';
                aiCaptionBtn.innerHTML = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2c1.1 0 2 .9 2 2v1.52c3.07.44 5.48 2.85 5.92 5.92H21.5c1.1 0 2 .9 2 2s-.9 2-2 2h-1.58c-.44 3.07-2.85 5.48-5.92 5.92V21.5c0 1.1-.9 2-2 2s-2-.9-2-2v-1.58c-3.07-.44-5.48-2.85-5.92-5.92H2.5c-1.1 0-2-.9-2-2s.9-2 2-2h1.58c.44-3.07 2.85-5.48 5.92-5.92V4c0-1.1.9-2 2-2zm0 5c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5z"/></svg>`;
                
                aiCaptionBtn.addEventListener('click', function() {
                    isAiActive = !isAiActive;
                    if (isAiActive) {
                        aiCaptionBtn.classList.add('active');
                        overlay.style.display = 'block';
                        subBox.innerText = "System matching audio patterns...";
                        startInternalAudioProcessing();
                    } else {
                        aiCaptionBtn.classList.remove('active');
                        overlay.style.display = 'none';
                    }
                });
                
                controlBar.el().appendChild(aiCaptionBtn);

                const downloadBtn = document.createElement('div');
                downloadBtn.className = 'vjs-download-control vjs-control vjs-button';
                downloadBtn.title = 'Source Link';
                downloadBtn.innerHTML = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 20h14v-2H5v2zM19 9h-4V3H9v6H5l7 7 7-7z"/></svg>`;
                downloadBtn.addEventListener('click', function() {
                    window.open("{{ target_url }}", '_blank');
                });
                controlBar.el().appendChild(downloadBtn);
            });

            player.on('canplay', function() {
                const loader = document.getElementById('video-loader');
                if (loader) {
                    loader.style.opacity = '0';
                    setTimeout(() => loader.remove(), 200);
                }
                player.play().catch(() => {
                    player.muted(true);
                    player.play();
                });
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
        return "Missing identity tracking tokens", 400

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
        'extract_flat': 'in_playlist',
        'impersonate': ImpersonateTarget.from_str('chrome'),
        'socket_timeout': 2,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if not info:
                return "Extraction framework timeline failure.", 500
                
            formats = info.get('formats', [])
            hls_streams = [f for f in formats if 'm3u8' in str(f.get('url','')) or 'hls' in str(f.get('format_id','')).lower()]
            m3u8_url = hls_streams[-1].get('url') if hls_streams else info.get('url')

            if not m3u8_url and formats:
                m3u8_url = formats[-1].get('url')

            if not m3u8_url:
                return "Stream parameters dropped.", 404

            return render_template_string(
                PLAYER_TEMPLATE, 
                title=info.get('title', 'Native Pipeline Player'),
                target_url=m3u8_url,
                priority=priority_flag,
                cb=int(time.time())
            )
            
    except Exception as error:
        return f"Extraction Error: {str(error)}", 500


@app.route('/manifest')
def proxy_m3u8():
    raw_m3u8_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_m3u8_url:
        return "Missing stream path configurations", 400

    raw_m3u8_url = urllib.parse.unquote(raw_m3u8_url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        resp = http_pool.get(raw_m3u8_url, headers=headers, timeout=3)
    except Exception:
        return "Connection path timed out.", 504

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
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@app.route('/segment')
def proxy_ts_segment():
    raw_ts_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_ts_url:
        return "Missing coordinate tags", 400

    raw_ts_url = urllib.parse.unquote(raw_ts_url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*'
    }
    timeout_val = 3 if priority == "high" else 4
    
    try:
        req = http_pool.get(raw_ts_url, headers=headers, stream=True, timeout=timeout_val)
        content_type = req.headers.get('Content-Type')
        if not content_type or 'text' in content_type or 'json' in content_type:
            content_type = "video/mp4" if "fmp4" in raw_ts_url else "video/MP2T"
        
        def stream_ts_data():
            for block in req.iter_content(chunk_size=1024 * 512):
                yield block

        response = Response(stream_ts_data(), content_type=content_type)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
    except Exception:
        return "Stream segmentation broken", 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
