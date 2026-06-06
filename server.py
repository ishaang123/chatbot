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
        /* Immersive True Fullscreen Cinema Styling */
        html, body { 
            margin: 0; padding: 0; width: 100%; height: 100%; 
            background-color: #000; overflow: hidden; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        .video-wrapper { 
            position: relative; width: 100%; height: 100%; 
            display: flex; justify-content: center; align-items: center;
        }

        /* Forces Video.js player component to natively cover 100% viewport dimensions */
        .video-js { 
            width: 100% !important; height: 100% !important; 
        }

        /* Modernized Minimalist Neon Loader Screen overlay */
        #video-loader {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
            background: #0a0a0a; z-index: 9999; 
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            transition: opacity 0.3s cubic-bezier(0.25, 1, 0.5, 1);
        }

        .spinner-box {
            position: relative; width: 64px; height: 64px;
            display: flex; justify-content: center; align-items: center;
        }

        .spinner {
            box-sizing: border-box; width: 100%; height: 100%;
            border: 4px solid rgba(255, 0, 85, 0.1);
            border-top: 4px solid #ff0055;
            border-radius: 50%;
            animation: spin 0.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        .loader-text { 
            margin-top: 20px; font-size: 1rem; font-weight: 500;
            color: #ffffff; letter-spacing: 1.5px; text-transform: uppercase;
            text-shadow: 0 0 10px rgba(255, 0, 85, 0.4);
            animation: pulse 1.5s ease-in-out infinite;
        }

        @keyframes pulse { 50% { opacity: 0.5; } }
    </style>
</head>
<body>

    <div class="video-wrapper">
        <div id="video-loader">
            <div class="spinner-box">
                <div class="spinner"></div>
            </div>
            <div class="loader-text">Streaming Buffer Connecting</div>
        </div>

        <video id="my-video" class="video-js vjs-default-skin vjs-big-play-centered" controls playsinline>
            <source src="/manifest?url={{ target_url | urlencode }}" type="application/x-mpegURL">
        </video>
    </div>

    <script src="https://vjs.zencdn.net/8.10.0/video.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            // High Speed Adaptive Preloading configuration parameters 
            const player = videojs('my-video', {
                preload: 'auto',
                autoplay: true,
                controls: true,
                fluid: false, // Turned off to prevent aspect ratio window restrictions
                inactivityTimeout: 1500,
                html5: {
                    vhs: {
                        overrideNative: true,
                        maxBufferLength: 45, // Expanded caching boundaries for zero buffering lag
                        liveBufferLength: 12
                    }
                }
            });

            // Instantaneous Drop-out hook to drop loader elements fast
            player.on('canplay', function() {
                const loader = document.getElementById('video-loader');
                if (loader) {
                    loader.style.opacity = '0';
                    setTimeout(() => loader.remove(), 300); // Demolish from DOM to save browser GPU memory
                }
                player.play().catch(() => {
                    // Fail-safe protection switch if system autoplay block rules restrict first load chimes
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
