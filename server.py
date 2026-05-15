from flask import Flask, request, render_template_string, send_file, jsonify
import yt_dlp
import os
import uuid
import threading
import time

app = Flask(__name__)

# Storage setup
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Ultra | Elite V7</title>
    <link href="https://fonts.googleapis.com/css2?family=Syncopate:wght@700&family=Outfit:wght@300;600;900&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #00f2ff; --bg: #020202; --card: rgba(12, 12, 12, 0.98); }
        
        * { box-sizing: border-box; transition: all 0.25s ease-out; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-thumb { background: var(--primary); border-radius: 10px; }

        body { 
            font-family: 'Outfit', sans-serif; background: var(--bg); color: white;
            margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center;
            min-height: 100vh; overflow-y: auto;
            background-image: radial-gradient(circle at 50% 10%, #001a1a 0%, #020202 100%);
        }

        .container { 
            width: 100%; max-width: 480px; margin: 40px auto; padding: 2.5rem; 
            background: var(--card); border-radius: 3rem; 
            border: 1px solid rgba(255, 255, 255, 0.03); text-align: center; 
            backdrop-filter: blur(40px); box-shadow: 0 40px 120px rgba(0,0,0,0.9);
        }

        h1 { font-family: 'Syncopate', sans-serif; font-size: 1.8rem; margin: 0; letter-spacing: -3px; }
        .neon { color: var(--primary); text-shadow: 0 0 20px rgba(0,242,255,0.4); }

        .selector { 
            display: flex; background: #000; padding: 6px; border-radius: 20px; 
            margin: 2rem 0; border: 1px solid #1a1a1a;
        }
        .s-btn { 
            flex: 1; padding: 12px; border-radius: 15px; border: none;
            background: transparent; cursor: pointer; color: #444;
            font-weight: 900; font-size: 0.75rem; text-transform: uppercase;
        }
        .s-btn.active { background: #fff; color: #000; }

        input { 
            width: 100%; background: #080808; border: 1px solid #222; padding: 1.2rem; 
            border-radius: 20px; color: white; outline: none; font-size: 1rem; margin-bottom: 1rem;
        }
        input:focus { border-color: var(--primary); box-shadow: 0 0 20px rgba(0,242,255,0.1); }

        .go-btn { 
            width: 100%; padding: 1.2rem; background: var(--primary); color: #000; 
            border: none; border-radius: 20px; font-weight: 900; cursor: pointer;
            font-size: 1rem; letter-spacing: 1px; text-transform: uppercase;
        }
        .go-btn:hover { transform: scale(1.02); filter: brightness(1.1); }
        .go-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        #preview-area { display: none; margin-top: 2.5rem; width: 100%; animation: slideUp 0.5s ease; }
        
        .preview-grid {
            display: grid; grid-template-columns: 1fr; gap: 20px;
        }

        .sub-card {
            background: rgba(255, 255, 255, 0.02); border: 1px solid #1a1a1a;
            border-radius: 25px; padding: 15px; text-align: left;
        }

        .label {
            font-size: 0.6rem; color: var(--primary); text-transform: uppercase;
            letter-spacing: 3px; margin-bottom: 10px; display: block; font-weight: 900;
        }

        .p-thumb { 
            width: 100%; border-radius: 15px; border: 1px solid #333; 
            background: #000; 
            object-fit: contain; /* Changed from cover to show full image */
            max-height: 450px;    /* Prevents vertical overflow */
        }
        
        #loader { margin-top: 20px; }
        .pulse { width: 10px; height: 10px; background: var(--primary); border-radius: 50%; display: inline-block; margin-right: 8px; animation: pulse 1.5s infinite; }
        
        @keyframes pulse { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(3); opacity: 0; } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>NEXUS<span class="neon">ULTRA</span></h1>
        <p style="font-size: 0.7rem; opacity: 0.3; letter-spacing: 5px; margin: 10px 0 2rem 0;">ELITE BYPASS v7.0</p>
        
        <div class="selector">
            <button id="mode-mp4" class="s-btn active" onclick="setMode('mp4')">Video</button>
            <button id="mode-mp3" class="s-btn" onclick="setMode('mp3')">Audio</button>
        </div>

        <input type="text" id="url-box" placeholder="Paste media link here..." spellcheck="false">
        <button class="go-btn" id="main-action" onclick="fetchContent()">Fetch Content</button>

        <div id="loader" style="display: none;">
            <span class="pulse"></span>
            <span id="load-text" style="font-size: 0.7rem; letter-spacing: 2px; color: var(--primary); font-weight: bold;">INITIALIZING...</span>
        </div>

        <div id="preview-area">
            <div class="preview-grid">
                <div class="sub-card">
                    <span class="label">Live Site Feed</span>
                    <img id="res-img-site" class="p-thumb" src="">
                </div>

                <div class="sub-card" id="media-card" style="display: none;">
                    <span class="label">Media Detected</span>
                    <img id="res-img-media" class="p-thumb" src="">
                    <div id="res-title" style="font-size: 0.85rem; font-weight: 600; margin: 12px 0; opacity: 0.8;"></div>
                    <a id="res-dl" style="text-decoration: none;">
                        <button class="go-btn" style="background: #fff; padding: 12px; font-size: 0.8rem;">Download File</button>
                    </a>
                </div>
            </div>
        </div>
    </div>

    <script>
        let mode = 'mp4';
        const sleep = ms => new Promise(res => setTimeout(res, ms));

        function setMode(m) {
            mode = m;
            document.getElementById('mode-mp4').className = m === 'mp4' ? 's-btn active' : 's-btn';
            document.getElementById('mode-mp3').className = m === 'mp3' ? 's-btn active' : 's-btn';
        }

        async function fetchContent() {
            const urlBox = document.getElementById('url-box');
            const url = urlBox.value.trim();
            if(!url) return;
            
            const mainBtn = document.getElementById('main-action');
            const loader = document.getElementById('loader');
            const loadText = document.getElementById('load-text');
            const previewArea = document.getElementById('preview-area');
            const mediaCard = document.getElementById('media-card');
            const siteImg = document.getElementById('res-img-site');

            mainBtn.disabled = true;
            loader.style.display = 'block';
            loadText.innerText = "CAPTURING SITE FEED...";
            
            // REMOVED /crop/ parameter to ensure full image capture
            siteImg.src = `https://image.thum.io/get/maxAge/1/width/800/${url}`;
            previewArea.style.display = 'block';
            mediaCard.style.display = 'none';

            try {
                await sleep(1500);
                loadText.innerText = "BYPASSING PROTOCOLS...";
                
                const res = await fetch('/extract', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url, format: mode })
                });
                const data = await res.json();
                
                if(data.success) {
                    await sleep(1000);
                    document.getElementById('res-img-media').src = data.thumbnail;
                    document.getElementById('res-title').innerText = data.title;
                    document.getElementById('res-dl').href = `/get-file?file=${data.filename}`;
                    
                    mediaCard.style.display = 'block';
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                } else {
                    alert("Error: " + data.error);
                }
            } catch(e) {
                alert("Nexus Server Timed Out.");
            } finally {
                loader.style.display = 'none';
                mainBtn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

def auto_delete(path):
    time.sleep(300) 
    if os.path.exists(path):
        os.remove(path)

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/extract', methods=['POST'])
def extract():
    data = request.json
    url = data.get('url').split('?')[0]
    fmt = data.get('format', 'mp4')
    
    forbidden = ["soundcloud.com", "snd.sc", "youtube.com", "youtu.be", "music.youtube"]
    if any(x in url.lower() for x in forbidden):
        return jsonify({'success': False, 'error': 'Platform restricted.'})

    fid = str(uuid.uuid4())[:8]
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/{fid}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    if fmt == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
        })
    else:
        ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fname = ydl.prepare_filename(info)
            if fmt == 'mp3': fname = os.path.splitext(fname)[0] + ".mp3"

            threading.Thread(target=auto_delete, args=(fname,)).start()

            return jsonify({
                'success': True,
                'title': info.get('title', 'Media File'),
                'thumbnail': info.get('thumbnail') or 'https://via.placeholder.com/600x338/111/00f2ff?text=Nexus+V7',
                'filename': os.path.basename(fname)
            })
    except Exception:
        return jsonify({'success': False, 'error': "Link incompatible or site protected."})

@app.route('/get-file')
def get_file():
    fname = request.args.get('file')
    fpath = os.path.join(DOWNLOAD_FOLDER, os.path.basename(fname))
    if os.path.exists(fpath):
        return send_file(fpath, as_attachment=True)
    return "Expired", 404 

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
