import os
import re
import urllib.parse
from flask import Flask, request, Response, render_template_string
import yt_dlp
import requests
from yt_dlp.networking.impersonate import ImpersonateTarget

app = Flask(__name__)

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
        html, body { 
            margin: 0; padding: 0; width: 100%; height: 100%; 
            background-color: #020203; overflow: hidden; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .video-wrapper { position: relative; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }
        .video-js { width: 100% !important; height: 100% !important; background-color: #000 !important; }
        #video-loader {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #040406; z-index: 9999; 
            display: flex; flex-direction: column; justify-content: center; align-items: center; transition: opacity 0.3s ease;
        }
        .spinner {
            box-sizing: border-box; width: 48px; height: 48px; border: 3px solid rgba(168, 85, 247, 0.1);
            border-top: 3px solid #a855f7; border-radius: 50%; animation: spin 0.6s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loader-text { margin-top: 16px; font-size: 0.75rem; font-weight: 600; color: #a1a1aa; letter-spacing: 1.5px; text-transform: uppercase; }
        
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
        }
        .video-js .vjs-progress-control { position: absolute !important; width: calc(100% - 24px) !important; height: 4px !important; top: -4px !important; left: 12px !important; }
        .video-js .vjs-play-progress { background: linear-gradient(90deg, #6366f1, var(--accent-color)) !important; }
        .video-js .vjs-play-progress:before { display: none !important; }
        .video-js .vjs-time-control { line-height: 48px !important; }
        
        /* Custom Control Bar Buttons Layout */
        .vjs-download-control, .vjs-cc-toggle-btn { 
            cursor: pointer; display: flex; align-items: center; justify-content: center; width: 38px; height: 100%; order: 99; 
        }
        .vjs-download-control svg, .vjs-cc-toggle-btn svg { width: 18px; height: 18px; fill: #a1a1aa; transition: fill 0.2s, transform 0.2s; }
        .vjs-download-control:hover svg, .vjs-cc-toggle-btn:hover svg { fill: #fff; transform: translateY(0.5px); }
        .vjs-cc-toggle-btn.active svg { fill: var(--accent-color) !important; }

        .video-js .vjs-text-track-cue {
            background-color: rgba(0, 0, 0, 0.75) !important;
            color: #ffffff !important;
            font-family: system-ui, sans-serif !important;
            font-size: 1.1rem !important;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="video-wrapper">
        <div id="video-loader">
            <div class="spinner"></div>
            <div class="loader-text">Extracting Video Matrix</div>
        </div>
        <video id="my-video" class="video-js vjs-default-skin vjs-big-play-centered" controls playsinline>
            <source src="/manifest?url={{ target_url | urlencode }}&priority={{ priority }}" type="application/x-mpegURL">
        </video>
    </div>
    <script src="https://vjs.zencdn.net/8.10.0/video.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const player = videojs('my-video', {
                preload: 'auto',
                autoplay: true,
                controls: true,
                html5: {
                    vhs: {
                        overrideNative: true,
                        maxBufferLength: 12,
                        enableLowInitialPlaylist: true,
                        fastStart: true
                    }
                }
            });

            player.ready(function() {
                const controlBar = player.getChild('controlBar');
                
                # Manual Injected CC Button to show up instantly no matter what
                const ccBtn = document.createElement('div');
                ccBtn.className = 'vjs-cc-toggle-btn vjs-control vjs-button';
                ccBtn.title = 'Toggle Captions';
                ccBtn.innerHTML = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M19 4H5c-1.11 0-2 .9-2 2v12c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.89-2-2-2zm-8 7H9.5v-.5h-2v3h2V13H11v1c0 .55-.45 1-1 1H6c-.55 0-1-.45-1-1V9c0-.55.45-1 1-1h4c0 .55.45 1 1 1v2zm7 0h-1.5v-.5h-2v3h2V13H18v1c0 .55-.45 1-1 1h-4c-.55 0-1-.45-1-1V9c0-.55.45-1 1-1h4c0 .55.45 1 1 1v2z"/></svg>`;
                
                ccBtn.addEventListener('click', function() {
                    const textTracks = player.textTracks();
                    let tracksFound = false;

                    for (let i = 0; i < textTracks.length; i++) {
                        tracksFound = true;
                        if (textTracks[i].mode === 'showing') {
                            textTracks[i].mode = 'disabled';
                            ccBtn.classList.remove('active');
                        } else {
                            textTracks[i].mode = 'showing';
                            ccBtn.classList.add('active');
                        }
                    }

                    # Fallback check if native tracks array isn't parsed yet
                    if (!tracksFound) {
                        alert("Captions are loading or not available for this stream context yet.");
                    }
                });
                controlBar.el().appendChild(ccBtn);

                const downloadBtn = document.createElement('div');
                downloadBtn.className = 'vjs-download-control vjs-control vjs-button';
                downloadBtn.title = 'Source';
                downloadBtn.innerHTML = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 20h14v-2H5v2zM19 9h-4V3H9v6H5l7 7 7-7z"/></svg>`;
                downloadBtn.addEventListener('click', function() {
                    const currentSrc = player.src();
                    const urlParams = new URLSearchParams(currentSrc.split('?')[1]);
                    const targetM3u8Url = urlParams.get('url');
                    window.open(targetM3u8Url ? decodeURIComponent(targetM3u8Url) : currentSrc, '_blank');
                });
                controlBar.el().appendChild(downloadBtn);
            });

            player.on('canplay', function() {
                const loader = document.getElementById('video-loader');
                if (loader) {
                    loader.style.opacity = '0';
                    setTimeout(() => loader.remove(), 300);
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
        return "Missing context identity parameter.", 400

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
        'socket_timeout': 3,                
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if not info:
                return "Extraction failure.", 500
                
            formats = info.get('formats', [])
            hls_streams = [f for f in formats if 'm3u8' in str(f.get('url','')) or 'hls' in str(f.get('format_id','')).lower()]
            m3u8_url = hls_streams[-1].get('url') if hls_streams else info.get('url')

            if not m3u8_url and formats:
                m3u8_url = formats[-1].get('url')

            if not m3u8_url:
                return "No stream targets discovered.", 404

            return render_template_string(
                PLAYER_TEMPLATE, 
                title=info.get('title', 'Native Stream Source'),
                target_url=m3u8_url,
                priority=priority_flag
            )
            
    except Exception as error:
        return f"Extraction Error: {str(error)}", 500


@app.route('/manifest')
def proxy_m3u8():
    raw_m3u8_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_m3u8_url:
        return "Missing tracking targets", 400

    raw_m3u8_url = urllib.parse.unquote(raw_m3u8_url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        resp = http_pool.get(raw_m3u8_url, headers=headers, timeout=3)
    except Exception:
        return "Network Timeout", 504

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
        return "Missing data reference", 400

    raw_ts_url = urllib.parse.unquote(raw_ts_url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    timeout_val = 3 if priority == "high" else 4
    
    try:
        req = http_pool.get(raw_ts_url, headers=headers, stream=True, timeout=timeout_val)
        content_type = req.headers.get('Content-Type', 'video/MP2T')
        
        def stream_ts_data():
            for block in req.iter_content(chunk_size=1024 * 128): 
                yield block

        response = Response(stream_ts_data(), content_type=content_type)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
    except Exception:
        return "Segment dropped", 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
