import os
import re
import urllib.parse
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

                statusBadge.textContent = "Syncing Token IP Handshake...";
                statusBadge.style.color = "var(--primary)";

                if (hlsInstance) {
                    hlsInstance.destroy();
                    hlsInstance = null;
                }
                video.pause();
                video.removeAttribute('src');
                video.load();

                const targetUrl = `/fetch-stream?url=${encodeURIComponent(videoUrl)}&type=meta`;

                fetch(targetUrl)
                    .then(response => {
                        if (!response.ok) throw new Error("Stream compilation dropped.");
                        return response.json();
                    })
                    .then(data => {
                        const proxiedManifestUrl = data.stream_url;

                        statusBadge.textContent = "IP Synchronized. Tunneling Video Tracks...";
                        statusBadge.style.color = "#00ff66";

                        if (video.canPlayType('application/vnd.apple.mpegurl')) {
                            video.src = proxiedManifestUrl;
                            video.play().catch(() => {});
                        } 
                        else if (Hls.isSupported()) {
                            hlsInstance = new Hls({
                                maxBufferSize: 20 * 1024 * 1024
                            });
                            hlsInstance.loadSource(proxiedManifestUrl);
                            hlsInstance.attachMedia(video);
                            hlsInstance.on(Hls.Events.MANIFEST_PARSED, function() {
                                video.play().catch(() => {});
                            });
                        }
                    })
                    .catch(err => {
                        console.error(err);
                        statusBadge.textContent = "Fault: Security verification dropped.";
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


def extract_video_id(url):
    match = re.search(r'(?:dailymotion\.com\/(?:video|embed\/video)\/|dai\.ly\/)([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None


@app.route('/')
def home():
    target_url = request.args.get('url', 'https://www.dailymotion.com/video/x9lnilq')
    return render_template_string(HTML_TEMPLATE, initial_url=target_url)


@app.route('/fetch-stream')
def fetch_stream():
    target_url = request.args.get('url')
    req_type = request.args.get('type', 'chunk')

    # Context survival parameter for underlying fragments
    fallback_base = request.args.get('base_url', '')

    if not target_url:
        return "Missing Target Resource URL", 400

    # Reconstruct root relative addresses if they escape client side mapping
    if target_url.startswith('/') and not target_url.startswith('//') and fallback_base:
        target_url = urllib.parse.urljoin(fallback_base, target_url)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': 'https://www.dailymotion.com/',
        'Accept': '*/*'
    }

    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip:
        headers['X-Forwarded-For'] = user_ip.split(',')[0].strip()
        headers['Client-IP'] = headers['X-Forwarded-For']

    try:
        if req_type == 'meta':
            video_id = extract_video_id(target_url)
            if not video_id:
                return jsonify({"error": "Invalid Video Link Structure"}), 400

            meta_res = requests.get(f"https://www.dailymotion.com/player/metadata/video/{video_id}", headers=headers,
                                    timeout=10)
            metadata = meta_res.json()
            master_url = metadata['qualities']['auto'][0]['url']

            encoded_url = urllib.parse.quote(master_url)
            return jsonify({
                "status": "success",
                "stream_url": f"/fetch-stream?url={encoded_url}&type=playlist"
            })

        elif req_type == 'playlist':
            res = requests.get(target_url, headers=headers, timeout=10)
            lines = res.text.splitlines()
            rewritten_lines = []

            # Save the true remote host origin to resolve sub-items later
            parsed_origin = urllib.parse.urlparse(target_url)
            base_origin_url = f"{parsed_origin.scheme}://{parsed_origin.netloc}"

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith('#'):
                    rewritten_lines.append(line)
                    continue

                # Form fully qualified URLs immediately
                absolute_url = urllib.parse.urljoin(target_url, line)
                encoded_line = urllib.parse.quote(absolute_url)
                encoded_origin = urllib.parse.quote(base_origin_url)

                if '.m3u8' in line:
                    next_type = "playlist"
                else:
                    next_type = "chunk"

                # Append absolute local proxy routes with context trackers
                local_proxy_route = f"/fetch-stream?url={encoded_line}&type={next_type}&base_url={encoded_origin}"
                rewritten_lines.append(local_proxy_route)

            return Response(
                "\n".join(rewritten_lines),
                content_type='application/vnd.apple.mpegurl',
                headers={'Access-Control-Allow-Origin': '*'}
            )

        else:
            res = requests.get(target_url, headers=headers, stream=True, timeout=10)

            def generate_chunks():
                for chunk in res.iter_content(chunk_size=8192):
                    yield chunk

            return Response(
                generate_chunks(),
                status=res.status_code,
                content_type=res.headers.get('Content-Type', 'video/mp2t'),
                headers={'Access-Control-Allow-Origin': '*'}
            )

    except Exception as e:
        return str(e), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
