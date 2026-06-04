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
        <p style="font-size: 0.7rem; opacity: 0.3; letter-spacing: 5px; margin: 10px 0 1rem 0;">DYNAMIC TUNNEL MATRIX</p>
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
            let hlsInstance = null;

            function playStream(videoUrl) {
                if (!videoUrl) return;
                statusBadge.textContent = "Negotiating Proxy Handshake...";
                statusBadge.style.color = "var(--primary)";

                if (hlsInstance) {
                    hlsInstance.destroy();
                    hlsInstance = null;
                }
                video.pause();
                video.removeAttribute('src');
                video.load();

                // Initial handshake to get our rewritten master playlist
                const proxyManifestUrl = `/fetch-stream?url=${encodeURIComponent(videoUrl)}&type=meta`;
                
                fetch(proxyManifestUrl)
                    .then(res => {
                        if (!res.ok) throw new Error("Manifest generation rejected.");
                        return res.json();
                    })
                    .then(data => {
                        statusBadge.textContent = "Tunnel Secured. Pipeline Active...";
                        statusBadge.style.color = "#00ff66";

                        if (video.canPlayType('application/vnd.apple.mpegurl')) {
                            video.src = data.stream_url;
                            video.play().catch(() => {});
                        } 
                        else if (Hls.isSupported()) {
                            hlsInstance = new Hls({
                                maxBufferSize: 20 * 1024 * 1024,
                                enableWorker: false
                            });
                            hlsInstance.loadSource(data.stream_url);
                            hlsInstance.attachMedia(video);
                            hlsInstance.on(Hls.Events.MANIFEST_PARSED, function() {
                                video.play().catch(() => {});
                            });
                        }
                    })
                    .catch(err => {
                        console.error(err);
                        statusBadge.textContent = "Connection Fault.";
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
    fallback_base = request.args.get('base_url', '')

    if not target_url:
        return "Missing Target URL", 400

    if target_url.startswith('/') and not target_url.startswith('//') and fallback_base:
        target_url = urllib.parse.urljoin(fallback_base, target_url)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.dailymotion.com/'
    }

    try:
        # Phase 1: Call API endpoint to get the hidden master m3u8
        if req_type == 'meta':
            video_id = extract_video_id(target_url)
            if not video_id:
                return jsonify({"error": "Invalid Video Link Structure"}), 400
                
            meta_res = requests.get(f"https://www.dailymotion.com/player/metadata/video/{video_id}", headers=headers, timeout=10)
            master_url = meta_res.json()['qualities']['auto'][0]['url']
            
            return jsonify({
                "status": "success",
                "stream_url": f"/fetch-stream?url={urllib.parse.quote(master_url)}&type=playlist"
            })

        # Phase 2: Rewrite sub-playlists so everything points back to your Render server
        elif req_type == 'playlist':
            res = requests.get(target_url, headers=headers, timeout=10)
            lines = res.text.splitlines()
            rewritten_lines = []
            
            parsed_origin = urllib.parse.urlparse(target_url)
            base_origin_url = f"{parsed_origin.scheme}://{parsed_origin.netloc}"
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    rewritten_lines.append(line)
                    continue

                absolute_url = urllib.parse.urljoin(target_url, line)
                next_type = "playlist" if (".m3u8" in line or "manifest" in line) else "chunk"
                
                # Turn every segment URL into an internal route through your Render proxy
                local_route = f"/fetch-stream?url={urllib.parse.quote(absolute_url)}&type={next_type}&base_url={urllib.parse.quote(base_origin_url)}"
                rewritten_lines.append(local_route)
                    
            return Response(
                "\n".join(rewritten_lines),
                content_type='application/vnd.apple.mpegurl',
                headers={'Access-Control-Allow-Origin': '*'}
            )

        # Phase 3: Act as the data pipeline tunnel for the actual video data chunks (.ts)
        else:
            res = requests.get(target_url, headers=headers, stream=True, timeout=15)
            
            def generate_chunks():
                for chunk in res.iter_content(chunk_size=32768):
                    if chunk:
                        yield chunk

            return Response(
                generate_chunks(),
                status=res.status_code,
                content_type=res.headers.get('Content-Type', 'video/mp2t'),
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'X-Accel-Buffering': 'no',
                    'Cache-Control': 'no-cache, no-store'
                }
            )

    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
