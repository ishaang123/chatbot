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
        <p style="font-size: 0.7rem; opacity: 0.3; letter-spacing: 5px; margin: 10px 0 1rem 0;">NATIVE BYPASS TRANSLATOR</p>

        <video id="video-engine" controls playsinline src="/stream-video/{{ active_id }}"></video>
    </div>
</body>
</html>
"""

# Maintain full connection lifecycle headers to hold off anti-scraping triggers
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.dailymotion.com/',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9'
})

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, active_id="x9lnilq")


@app.route('/stream-video/<video_id>')
def stream_video(video_id):
    try:
        # Step 1: Grab metadata structure using our active session tracking
        meta_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
        meta_res = session.get(meta_url, timeout=10)
        
        if meta_res.status_code != 200:
            return f"Upstream API Rejected with code: {meta_res.status_code}", 502
            
        metadata = meta_res.json()
        
        # Exact extraction matching your actual payload payload template
        try:
            master_m3u8_url = metadata['qualities']['auto'][0]['url']
        except (KeyError, IndexError):
            return "Unable to parse stream manifest from structural map target.", 500

        # Step 2: Grab the master index configuration data
        master_res = session.get(master_m3u8_url, timeout=10)
        master_text = master_res.text
        
        base_url = master_m3u8_url[0:master_m3u8_url.rfind('/')+1]
        target_playlist_url = ""
        
        # Read down options to pick the target quality lane sub-manifest
        for line in master_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                target_playlist_url = line if line.startswith('http') else base_url + line
                break
                
        if not target_playlist_url:
            target_playlist_url = master_m3u8_url
            
        # Step 3: Fetch the sub-playlist holding chunk segment addresses
        playlist_res = session.get(target_playlist_url, timeout=10)
        playlist_text = playlist_res.text
        playlist_base_url = target_playlist_url[0:target_playlist_url.rfind('/')+1]
        
        chunk_urls = []
        for line in playlist_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                chunk_urls.append(line if line.startswith('http') else playlist_base_url + line)
                
        if not chunk_urls:
            return "No stream translation segments located.", 404

        # Step 4: Iterative generator to yield bytes sequentially down the pipe
        def generate_video_stream():
            for url in chunk_urls:
                try:
                    # Stream true response chunks sequentially
                    chunk_res = session.get(url, stream=True, timeout=15)
                    if chunk_res.status_code == 200:
                        for block in chunk_res.iter_content(chunk_size=65536):
                            yield block
                except Exception:
                    continue # Skip segment drops cleanly

        # Crucial Fix: Setting mimetype to video/mp2t (MPEG Transport Stream)
        # matches the binary formatting of the raw chunks so the video element reads it smoothly
        return Response(
            generate_video_stream(),
            mimetype="video/mp2t",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "video/mp2t",
                "Accept-Ranges": "bytes"
            }
        )
        
    except Exception as e:
        return f"Stream Core Error Trace: {str(e)}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
