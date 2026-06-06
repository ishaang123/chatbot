import os
import re
import urllib.parse
from flask import Flask, request, Response, render_template_string
import yt_dlp
import requests
from yt_dlp.networking.impersonate import ImpersonateTarget

app = Flask(__name__)

PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
    <style>
        /* ==========================================================================
           1. IMMERSIVE CANVAS AND ENGINE WRAPPERS
           ========================================================================== */
        html, body { 
            margin: 0; padding: 0; width: 100%; height: 100%; 
            background-color: #030303; overflow: hidden; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        .video-wrapper { 
            position: relative; width: 100%; height: 100%; 
            display: flex; justify-content: center; align-items: center;
        }

        .video-js { 
            width: 100% !important; height: 100% !important; 
            background-color: #000 !important;
        }

        /* ==========================================================================
           2. PREMIUM THEMED NEON LOADER OVERLAY
           ========================================================================== */
        #video-loader {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
            background: #09090b; z-index: 9999; 
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            transition: opacity 0.4s cubic-bezier(0.25, 1, 0.5, 1);
            pointer-events: none;
        }

        .spinner-box {
            position: relative; width: 64px; height: 64px;
            display: flex; justify-content: center; align-items: center;
        }

        .spinner {
            box-sizing: border-box; width: 100%; height: 100%;
            border: 4px solid rgba(99, 102, 241, 0.1);
            border-top: 4px solid #6366f1; 
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        .loader-text { 
            margin-top: 22px; font-size: 0.8rem; font-weight: 600;
            color: #ffffff; letter-spacing: 2px; text-transform: uppercase;
            text-shadow: 0 0 12px rgba(99, 102, 241, 0.4);
            animation: pulse 1.5s ease-in-out infinite;
            opacity: 0.8;
        }

        @keyframes pulse { 50% { opacity: 0.3; } }

        /* ==========================================================================
           3. MOVIE THEATER GLASSMORPHISM SKIN OVERRIDES
           ========================================================================== */
        :root {
            --brand-accent: #ff0055;       
            --glass-bg: rgba(15, 15, 20, 0.75); 
            --glass-border: rgba(255, 255, 255, 0.08);
        }

        /* Center Play Button Upgrade */
        .video-js .vjs-big-play-button {
            background: linear-gradient(135deg, rgba(255, 0, 85, 0.85), rgba(99, 102, 241, 0.85)) !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
            border-radius: 50% !important;
            width: 80px !important; height: 80px !important;
            line-height: 78px !important;
            box-shadow: 0 12px 40px rgba(255, 0, 85, 0.4) !important;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease !important;
        }

        .video-js:hover .vjs-big-play-button {
            transform: scale(1.1) translate(-45%, -45%); /* Corrects default videojs absolute offset math */
            box-shadow: 0 16px 48px rgba(255, 0, 85, 0.6) !important;
        }

        /* Floating Control Panel Layout */
        .video-js .vjs-control-bar {
            background: var(--glass-bg) !important;
            backdrop-filter: blur(24px) !important;
            -webkit-backdrop-filter: blur(24px) !important;
            border: 1px solid var(--glass-border);
            border-radius: 16px !important;
            width: calc(100% - 40px) !important;
            height: 60px !important;
            bottom: 20px !important; left: 20px !important;
            padding: 0 12px !important;
            box-shadow: 0 24px 50px rgba(0, 0, 0, 0.6) !important;
            display: flex !important;
            align-items: center !important;
            transition: opacity 0.3s elements, transform 0.3s cubic-bezier(0.25, 1, 0.5, 1) !important;
        }

        /* Smooth slide-down when inactive */
        .video-js.vjs-user-inactive .vjs-control-bar {
            transform: translateY(15px);
            opacity: 0;
        }

        /* Structural Adjustments for Video.JS Layout Grid */
        .video-js .vjs-control {
            height: 100% !important;
            width: 48px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        .video-js .vjs-button > .vjs-icon-placeholder:before {
            position: relative !important;
            text-align: center !important;
            line-height: 60px !important;
            height: 100% !important;
            width: 100% !important;
            font-size: 1.8em !important;
        }

        /* Cleaned, Flex-based Fluid Timeline Progress Loop */
        .video-js .vjs-progress-control {
            flex: 1 !important;
            display: flex !important;
            align-items: center !important;
            min-width: 100px !important;
            height: 100% !important;
            margin-right: 12px !important;
        }

        .video-js .vjs-progress-holder {
            height: 6px !important;
            margin: 0 !important;
            width: 100% !important;
            background: rgba(255, 255, 255, 0.12) !important;
            border-radius: 4px !important;
        }

        /* Play Progress Glow Line Track */
        .video-js .vjs-play-progress {
            background: linear-gradient(90deg, #6366f1, var(--brand-accent)) !important;
            border-radius: 4px !important;
        }
        
        /* Remove the classic huge seek circle handle */
        .video-js .vjs-play-progress:before {
            display: none !important; 
        }

        .video-js .vjs-load-progress {
            background: rgba(255, 255, 255, 0.18) !important;
            border-radius: 4px !important;
        }
        .video-js .vjs-load-progress div {
            background: transparent !important;
        }

        /* Universal Text Formatting Matrix */
        .video-js .vjs-time-control {
            display: flex !important;
            align-items: center !important;
            height: 100% !important;
            padding: 0 4px !important;
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            color: #e4e4e7 !important;
            min-width: auto !important;
        }
        
        .video-js .vjs-time-divider { min-width: auto !important; padding: 0 2px !important; }

        /* Volume Elements Uniform Grid Alignment */
        .video-js .vjs-volume-panel {
            display: flex !important;
            align-items: center !important;
            height: 100% !important;
        }

        .video-js .vjs-volume-bar {
            margin: 0 !important;
            background: rgba(255, 255, 255, 0.15) !important;
            height: 5px !important;
            border-radius: 3px !important;
        }

        .video-js .vjs-volume-level {
            background: #ffffff !important;
            border-radius: 3px !important;
        }
    </style>
</head>
<body>

    <div class="video-wrapper">
        <div id="video-loader">
            <div class="spinner-box">
                <div class="spinner"></div>
            </div>
            <div class="loader-text">Decrypting Stream Matrix</div>
        </div>

        <video id="my-video" class="video-js vjs-default-skin vjs-big-play-centered" controls playsinline>
            <source src="/manifest?url={{ target_url | urlencode }}" type="application/x-mpegURL">
        </video>
    </div>

    <script src="https://vjs.zencdn.net/8.10.0/video.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const player = videojs('my-video', {
                preload: 'auto',
                autoplay: true,
                controls: true,
                fluid: false, 
                inactivityTimeout: 2500, // Seamless vanishing timer interface frame
                controlBar: {
                    // Turn off components that clutter standard structural alignment blueprints
                    pictureInPictureToggle: false,
                    remainingTimeDisplay: false
                },
                html5: {
                    vhs: {
                        overrideNative: true,
                        maxBufferLength: 45, 
                        liveBufferLength: 12
                    }
                }
            });

            // Fast Event Hook Matrix to destroy Loader Screen Elements
            player.on('canplay', function() {
                const loader = document.getElementById('video-loader');
                if (loader) {
                    loader.style.opacity = '0';
                    setTimeout(() => loader.remove(), 400); 
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

import time  # Make sure to add this at the top of your starter.py file!

@app.route('/download', methods=['POST', 'GET'])
def render_player():
    user_input = request.form.get('id_or_url', '').strip() if request.method == 'POST' else request.args.get('id_or_url', '').strip()

    if not user_input:
        return "Missing 'id_or_url' parameter.", 400

    if "dailymotion.com" in user_input:
        target_url = user_input if user_input.startswith(("http://", "https://")) else f"https://{user_input}"
    else:
        target_url = f"https://www.dailymotion.com/video/{user_input}"

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'impersonate': ImpersonateTarget.from_str('chrome')
    }

    info = None
    m3u8_url = None

    # First Attempt
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            formats = info.get('formats', [])
            hls_streams = [f for f in formats if 'hls' in f.get('format_id', '') and f.get('url')]
            m3u8_url = hls_streams[-1].get('url') if hls_streams else (info.get('url') or formats[-1].get('url'))
    except Exception as first_error:
        print(f"First attempt failed: {first_error}. Retrying in 1 second...")
        time.sleep(1)  # Cool-down pause to clear temporary rate limits
        
        # Second Attempt (The Retry)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                formats = info.get('formats', [])
                hls_streams = [f for f in formats if 'hls' in f.get('format_id', '') and f.get('url')]
                m3u8_url = hls_streams[-1].get('url') if hls_streams else (info.get('url') or formats[-1].get('url'))
        except Exception as second_error:
            # Absolute Backup Fallback: Build the direct CDN link manually so it STILL plays
            print(f"Retry failed too: {second_error}. Using fallback template link.")
            video_id = user_input.split("/video/")[-1].split("?")[0] if "/video/" in user_input else user_input
            m3u8_url = f"https://www.dailymotion.com/cdn/manifest/video/{video_id}.m3u8"
            
            # Create a mock info dict so the page doesn't crash on title rendering
            info = {'title': 'Dailymotion Stream (Fallback Mode)'}

    # Final validation safety check
    if not m3u8_url:
        return "Failed to find manifest endpoint maps.", 500

    return render_template_string(
        PLAYER_TEMPLATE, 
        title=info.get('title', 'Dailymotion Stream') if info else 'Dailymotion Stream',
        target_url=m3u8_url
    )


@app.route('/manifest')
def proxy_m3u8():
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

        # CRITICAL FIXED PIECE: Capture separate audio manifests hiding in attributes like:
        # #EXT-X-MEDIA:TYPE=AUDIO,...,URI="https://..."
        if 'URI=' in line_stripped:
            def replace_uri(match):
                rel_path = match.group(1).strip('"\'')
                abs_url = urllib.parse.urljoin(base_url, rel_path)
                proxy_route = "/manifest" if (".m3u8" in rel_path or "manifest" in rel_path) else "/segment"
                return f'URI="{proxy_route}?url={urllib.parse.quote_plus(abs_url)}"'

            line_stripped = re.sub(r'URI=(["\'].*?["\'])', replace_uri, line_stripped)
            rewritten_lines.append(line_stripped)

        elif not line_stripped.startswith('#'):
            if not line_stripped.startswith(('http://', 'https://')):
                full_url = urllib.parse.urljoin(base_url, line_stripped)
            else:
                full_url = line_stripped

            encoded_url = urllib.parse.quote_plus(full_url)

            if '.m3u8' in line_stripped or 'manifest' in line_stripped:
                rewritten_lines.append(f"/manifest?url={encoded_url}")
            else:
                rewritten_lines.append(f"/segment?url={encoded_url}")
        else:
            rewritten_lines.append(line_stripped)

    return Response("\n".join(rewritten_lines), content_type="application/x-mpegURL")


@app.route('/segment')
def proxy_ts_segment():
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
    return Response(stream_ts_data(), content_type=content_type)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
