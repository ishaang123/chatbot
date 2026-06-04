import os
import re
import urllib.parse
import requests
from flask import Flask, request, jsonify, render_template_string, Response
import yt_dlp

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Ultra | Advanced Stream Core</title>
    <link href="https://fonts.googleapis.com/css2?family=Syncopate:wght=700&family=Outfit:wght=300;600;900&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #00f2ff; --bg: #020202; --card: rgba(12, 12, 12, 0.98); }
        body { 
            font-family: 'Outfit', sans-serif; background: var(--bg); color: white;
            margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center;
            min-height: 100vh; background-image: radial-gradient(circle at 50% 10%, #001a1a 0%, #020202 100%);
        }
        .container { 
            width: 100%; max-width: 640px; margin: 40px auto; padding: 2.5rem; 
            background: var(--card); border-radius: 2rem; border: 1px solid rgba(255, 255, 255, 0.03); 
            text-align: center; backdrop-filter: blur(40px); box-shadow: 0 40px 120px rgba(0,0,0,0.9);
        }
        h1 { font-family: 'Syncopate', sans-serif; font-size: 1.8rem; margin: 0; letter-spacing: -3px; }
        .neon { color: var(--primary); text-shadow: 0 0 20px rgba(0,242,255,0.4); }
        .control-panel { margin: 25px 0; display: flex; gap: 10px; justify-content: center; }
        input {
            background: #111; border: 1px solid #333; padding: 12px 20px;
            border-radius: 30px; color: #fff; font-family: 'Outfit', sans-serif;
            font-size: 1rem; width: 70%; outline: none; transition: 0.3s;
        }
        input:focus { border-color: var(--primary); box-shadow: 0 0 10px rgba(0,242,255,0.2); }
        button {
            background: var(--primary); color: #000; font-weight: bold; border: none;
            padding: 12px 25px; border-radius: 30px; cursor: pointer;
            font-family: 'Outfit', sans-serif; font-size: 1rem;
            box-shadow: 0 0 15px rgba(0,242,255,0.3); transition: 0.3s;
        }
        button:hover { opacity: 0.9; transform: scale(1.02); }
        .status-badge { font-size: 0.65rem; color: #aaa; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 15px; height: 15px; }
        video { width: 100%; aspect-ratio: 16/9; border-radius: 15px; border: 1px solid #222; background: #000; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NEXUS<span class="neon">STREAM</span></h1>
        <p style="font-size: 0.7rem; opacity: 0.3; letter-spacing: 5px; margin: 10px 0 1rem 0;">HYBRID MANIFEST RESOLVER</p>
        <div class="control-panel">
            <input type="text" id="video-url-input" value="{{ initial_url }}" placeholder="Enter Video URL...">
            <button id="load-btn">STREAM</button>
        </div>
        <div class="status-badge" id="buffer-status">Ready</div>
        <video id="video-engine" controls playsinline></video>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const video = document.getElementById('video-engine');
            const loadBtn = document.getElementById('load-btn');
            const urlInput = document.getElementById('video-url-input');
            const statusBadge = document.getElementById('buffer-status');

            function playStream(videoUrl) {
                if (!videoUrl) return;
                statusBadge.textContent = "Resolving backend manifest...";
                statusBadge.style.color = "var(--primary)";

                video.pause();
                video.removeAttribute('src');
                video.load();

                const proxyUrl = `/stream-bridge?url=${encodeURIComponent(videoUrl)}`;
                
                video.src = proxyUrl;
                statusBadge.textContent = "Streaming Live Pipeline...";
                statusBadge.style.color = "#00ff66";
                
                video.play().catch(err => {
                    console.log("Playback deferred.");
                });
            }

            playStream(urlInput.value.trim());

            loadBtn.addEventListener('click', () => {
                const cleanUrl = urlInput.value.trim();
                if (cleanUrl) playStream(cleanUrl);
            });
        });
    </script>
</body>
</html>
"""

def extract_video_id(url):
    match = re.search(r'(?:dailymotion\.com\/(?:video|embed\/video)\/|dai\.ly\/)([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None

@app.route('/')
def home():
    target_url = request.args.get('url', 'https://www.dailymotion.com/video/x9lnilq')
    return render_template_string(HTML_TEMPLATE, initial_url=target_url)

@app.route('/stream-bridge')
def stream_bridge():
    video_url = request.args.get('url')
    if not video_url:
        return "Missing URL", 400

    video_id = extract_video_id(video_url)
    if not video_id:
        return "Invalid Link Structure", 400

    # Step 1: Handshake with Dailymotion metadata to fetch the raw direct .m3u8 url
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.dailymotion.com/'
    }
    
    try:
        meta_res = requests.get(f"https://www.dailymotion.com/player/metadata/video/{video_id}", headers=headers, timeout=10)
        metadata = meta_res.json()
        master_m3u8_url = metadata['qualities']['auto'][0]['url']
        
        # Step 2: Feed the raw, extracted .m3u8 url directly into yt-dlp
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # yt-dlp interprets raw .m3u8 urls as direct stream lists natively
            info = ydl.extract_info(master_m3u8_url, download=False)
            direct_stream_url = info.get('url')

        if not direct_stream_url:
            return "Could not resolve stream source url", 500

        # Step 3: Stream the video data through Render
        res = requests.get(direct_stream_url, headers=headers, stream=True, timeout=15)
        
        def pipe_data():
            for chunk in res.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk

        return Response(
            pipe_data(),
            status=res.status_code,
            content_type=res.headers.get('Content-Type', 'video/mp4'),
            headers={
                'X-Accel-Buffering': 'no',
                'Cache-Control': 'no-cache, no-store'
            }
        )

    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
