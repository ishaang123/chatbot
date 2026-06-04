import os
import re
import requests
from flask import Flask, request, jsonify, render_template_string, Response

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Ultra | Advanced Stream Core</title>
    <link href="https://fonts.googleapis.com/css2?family=Syncopate:wght=700&family=Outfit:wght=300;600;900&display=swap" rel="stylesheet">

    <script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.0/dist/hls.min.js"></script>

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

        .control-panel {
            margin: 25px 0;
            display: flex;
            gap: 10px;
            justify-content: center;
        }
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
        <p style="font-size: 0.7rem; opacity: 0.3; letter-spacing: 5px; margin: 10px 0 1rem 0;">DYNAMIC CORE RESOLVER</p>

        <div class="control-panel">
            <input type="text" id="video-url-input" value="{{ initial_url }}" placeholder="Enter Dailymotion Video URL...">
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
            let hlsInstance = null;

            function playStream(videoUrl) {
                if (!videoUrl) return;

                statusBadge.textContent = "Fetching Proxied Stream Manifest...";
                statusBadge.style.color = "var(--primary)";

                if (hlsInstance) {
                    hlsInstance.destroy();
                    hlsInstance = null;
                }
                video.pause();
                video.removeAttribute('src');
                video.load();

                fetch(`/get-stream-manifest?url=${encodeURIComponent(videoUrl)}`)
                    .then(response => {
                        if (!response.ok) throw new Error("Server rejected stream proxy token configuration.");
                        return response.json();
                    })
                    .then(data => {
                        const manifestUrl = data.stream_url;
                        statusBadge.textContent = "Synchronized. Streaming via Proxy Tunnel...";
                        statusBadge.style.color = "#00ff66";

                        if (video.canPlayType('application/vnd.apple.mpegurl')) {
                            video.src = manifestUrl;
                            video.play().catch(() => {});
                        } 
                        else if (Hls.isSupported()) {
                            hlsInstance = new Hls({
                                maxBufferSize: 20 * 1024 * 1024
                            });
                            hlsInstance.loadSource(manifestUrl);
                            hlsInstance.attachMedia(video);
                            hlsInstance.on(Hls.Events.MANIFEST_PARSED, function() {
                                video.play().catch(() => {});
                            });
                        } else {
                            statusBadge.textContent = "Error: Browser missing streaming engines.";
                            statusBadge.style.color = "#ff3333";
                        }
                    })
                    .catch(err => {
                        console.error(err);
                        statusBadge.textContent = "Fault: Stream compilation dropped.";
                        statusBadge.style.color = "#ff3333";
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

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://www.dailymotion.com/',
    'Accept': '*/*'
})


def extract_video_id(url):
    match = re.search(r'(?:dailymotion\.com/(?:video|embed/video)/|dai\.ly/)([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None


@app.route('/')
def home():
    target_url = request.args.get('url', 'https://www.dailymotion.com/video/x9lnilq')
    return render_template_string(HTML_TEMPLATE, initial_url=target_url)


@app.route('/get-stream-manifest')
def get_stream_manifest():
    try:
        video_url = request.args.get('url')
        if not video_url:
            return jsonify({"error": "No URL provided"}), 400

        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({"error": "Could not extract video ID"}), 400

        meta_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
        meta_res = session.get(meta_url, timeout=10)
        if meta_res.status_code != 200:
            return jsonify({"error": f"Upstream Token Error: {meta_res.status_code}"}), 502

        metadata = meta_res.json()
        master_playlist_url = metadata['qualities']['auto'][0]['url']

        # Routes the frontend to request data via our proxy endpoint
        proxied_url = f"/proxy-stream?url={requests.utils.quote(master_playlist_url)}"

        return jsonify({
            "status": "success",
            "stream_url": proxied_url
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/proxy-stream')
def proxy_stream():
    """Proxies the playlist text data through the backend session to resolve headers and CORS."""
    target_url = request.args.get('url')
    if not target_url:
        return "Missing URL parameter", 400

    try:
        response = session.get(target_url, timeout=10)
        return Response(
            response.text,
            status=response.status_code,
            content_type='application/vnd.apple.mpegurl'
        )
    except Exception as e:
        return str(e), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
