import os
import requests
from flask import Flask, request, Response, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Ultra | Advanced Stream Core</title>
    <link href="https://fonts.googleapis.com/css2?family=Syncopate:wght@700&family=Outfit:wght@300;600;900&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/hls.js@1.4.12/dist/hls.min.js"></script>
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
        video { width: 100%; aspect-ratio: 16/9; border-radius: 15px; border: 1px solid #222; background: #000; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NEXUS<span class="neon">STREAM</span></h1>
        <p style="font-size: 0.7rem; opacity: 0.3; letter-spacing: 5px; margin: 10px 0 1rem 0;">SECURE IP-BOUND TRANSLATOR</p>

        <video id="video-engine" controls playsinline></video>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const video = document.getElementById('video-engine');
            // Route directly to our backend stream map resolver
            const manifestSource = "/get-stream/{{ active_id }}";

            if (Hls.isSupported()) {
                const hls = new Hls();
                hls.loadSource(manifestSource);
                hls.attachMedia(video);
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                // Compatibility layer for Apple Safari
                video.src = manifestSource;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    # Pass the strict target stream id directly
    return render_template_string(HTML_TEMPLATE, active_id="x9lnilq")

@app.route('/get-stream/<video_id>')
def get_stream(video_id):
    """
    Acts as a unified request handler. Python requests the metadata AND 
    the manifest text internally, aligning the IP signature footprint perfectly.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.dailymotion.com/'
    }
    
    try:
        # Step 1: Request metadata from Python server IP
        meta_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
        meta_res = requests.get(meta_url, headers=headers)
        if meta_res.status_code != 200:
            return "Upstream Token Authorization Rejected.", meta_res.status_code
        
        metadata = meta_res.json()
        master_m3u8_url = metadata['qualities']['auto'][0]['url']
        
        # Step 2: Request master playlist content immediately using same IP context
        master_res = requests.get(master_m3u8_url, headers=headers)
        master_text = master_res.text
        
        # Rewrite links to point directly back through our local `/proxy` route
        base_url = master_m3u8_url[0:master_m3u8_url.rfind('/')+1]
        proxy_root = f"{request.url_root.rstrip('/')}/proxy?url="
        
        rewritten_lines = []
        for line in master_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                absolute_url = line if line.startswith('http') else base_url + line
                line = proxy_root + requests.utils.quote(absolute_url)
            rewritten_lines.append(line)
            
        final_manifest = "\n".join(rewritten_lines)
        
        return Response(
            final_manifest,
            mimetype="application/vnd.apple.mpegurl",
            headers={"Access-Control-Allow-Origin": "*"}
        )
        
    except Exception as e:
        return f"Stream Generator Fault: {str(e)}", 500

@app.route('/proxy')
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing URL proxy string target.", 400

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.dailymotion.com/'
    }
    
    try:
        res = requests.get(target_url, headers=headers, stream=True)
        excluded = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(n, v) for (n, v) in res.headers.items() if n.lower() not in excluded]
        
        response_headers.append(('Access-Control-Allow-Origin', '*'))
        return Response(res.iter_content(chunk_size=8192), status=res.status_code, headers=response_headers)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
