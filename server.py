from flask import Flask, request, render_template_string, send_file, jsonify
import yt_dlp
import os
import uuid
import threading
import time

app = Flask(__name__)

# Storage Config
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Ultra | Elite Media Fetcher</title>
    <link href="https://fonts.googleapis.com/css2?family=Syncopate:wght@700&family=Outfit:wght@300;600;900&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #00f2ff; --neon-purple: #bc13fe; --bg: #020202; }
        
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: var(--primary); border-radius: 10px; }

        body { 
            font-family: 'Outfit', sans-serif; background: var(--bg); color: white;
            margin: 0; display: flex; flex-direction: column; align-items: center;
            min-height: 100vh; overflow-y: auto;
            background-image: 
                linear-gradient(rgba(0, 242, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 242, 255, 0.03) 1px, transparent 1px);
            background-size: 30px 30px;
        }

        .hero { margin-top: 50px; text-align: center; padding: 20px; }
        h1 { font-family: 'Syncopate', sans-serif; font-size: 2.2rem; letter-spacing: -3px; margin: 0; }
        .glow { color: var(--primary); text-shadow: 0 0 20px rgba(0,242,255,0.6); }

        .app-card { 
            width: 92%; max-width: 460px; margin: 20px 0; padding: 2rem; 
            background: rgba(15, 15, 15, 0.7); border-radius: 2.5rem; 
            border: 1px solid rgba(255,255,255,0.08); backdrop-filter: blur(40px);
            box-shadow: 0 40px 100px rgba(0,0,0,0.9);
        }

        .mode-toggle { 
            display: flex; gap: 8px; background: #000; padding: 6px; 
            border-radius: 20px; margin-bottom: 1.5rem; border: 1px solid #222;
        }
        .m-btn { 
            flex: 1; padding: 12px; border-radius: 15px; border: none;
            background: transparent; cursor: pointer; color: #555;
            font-weight: 900; font-size: 0.75rem; transition: 0.4s;
            text-transform: uppercase;
        }
        .m-btn.active { background: linear-gradient(135deg, var(--primary), var(--neon-purple)); color: white; }

        .input-box { 
            background: rgba(255,255,255,0.03); border: 1px solid #333; 
            border-radius: 20px; display: flex; align-items: center; padding: 5px 15px;
            margin-bottom: 1.5rem; transition: 0.3s;
        }
        .input-box:focus-within { border-color: var(--primary); box-shadow: 0 0 15px rgba(0,242,255,0.2); }
        input { flex: 1; background: transparent; border: none; padding: 1rem; color: white; outline: none; font-size: 1rem; }

        .action-btn { 
            width: 100%; padding: 1.2rem; background: #fff; color: #000; 
            border: none; border-radius: 20px; font-weight: 900; cursor: pointer;
            font-size: 1rem; transition: 0.3s; box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        }
        .action-btn:active { transform: scale(0.96); }
        .action-btn:hover { background: var(--primary); }

        /* Results Section */
        #result { display: none; margin-top: 2rem; animation: fadeInUp 0.5s ease forwards; }
        .preview-media { width: 100%; border-radius: 20px; margin-bottom: 1rem; border: 1px solid #333; }
        
        .badge { 
            display: inline-block; padding: 5px 12px; border-radius: 10px; 
            background: rgba(0,242,255,0.1); color: var(--primary); 
            font-size: 0.7rem; font-weight: 900; margin-bottom: 10px;
        }

        #loader { 
            position: fixed; inset: 0; background: rgba(0,0,0,0.9); 
            display: none; flex-direction: column; justify-content: center; 
            align-items: center; z-index: 1000; backdrop-filter: blur(10px);
        }
        .scanline { width: 100px; height: 2px; background: var(--primary); box-shadow: 0 0 15px var(--primary); animation: scan 1s infinite alternate; }
        
        @keyframes scan { from { opacity: 0.2; transform: scaleX(0.5); } to { opacity: 1; transform: scaleX(1.5); } }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <div id="loader">
        <div class="scanline"></div>
        <p style="color: var(--primary); font-family: 'Syncopate'; font-size: 0.6rem; margin-top: 20px;">ENCRYPTING STREAM</p>
    </div>

    <div class="hero">
        <h1>NEXUS<span class="glow">ULTRA</span></h1>
        <p style="font-size: 0.8rem; opacity: 0.5; letter-spacing: 2px;">ELITE MEDIA FETCH v4.0</p>
    </div>

    <div class="app-card">
        <div class="mode-toggle">
            <button id="mp4-btn" class="m-btn active" onclick="setFmt('mp4')">Video</button>
            <button id="mp3-btn" class="m-btn" onclick="setFmt('mp3')">Audio</button>
        </div>

        <div class="input-box">
            <input type="text" id="target-url" placeholder="Paste link here..." onpaste="setTimeout(process, 100)">
        </div>

        <button class="action-btn" onclick="process()">FETCH MEDIA</button>

        <div id="result">
            <div class="badge" id="type-badge">MP4</div>
            <img id="p-img" class="preview-media" src="">
            <h3 id="p-title" style="font-size: 1rem; margin: 0 0 15px 0;"></h3>
            
            <a id="p-dl" style="text-decoration: none;">
                <button class="action-btn" style="background: var(--primary);">DOWNLOAD NOW</button>
            </a>
        </div>
    </div>

    <p style="margin: 20px; font-size: 0.7rem; opacity: 0.3;">Supports: TikTok, SoundCloud, Vimeo, IG, Streamable & More</p>

    <script>
        let selectedFmt = 'mp4';
        function setFmt(f) {
            selectedFmt = f;
            document.getElementById('mp4-btn').className = f === 'mp4' ? 'm-btn active' : 'm-btn';
            document.getElementById('mp3-btn').className = f === 'mp3' ? 'm-btn active' : 'm-btn';
            document.getElementById('type-badge').innerText = f.toUpperCase();
        }

        async function process() {
            const url = document.getElementById('target-url').value;
            if(!url) return;

            document.getElementById('loader').style.display = 'flex';
            document.getElementById('result').style.display = 'none';

            try {
                const response = await fetch('/extract', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url, format: selectedFmt })
                });
                const data = await response.json();
                
                if(data.success) {
                    document.getElementById('p-img').src = data.thumbnail;
                    document.getElementById('p-title').innerText = data.title;
                    document.getElementById('p-dl').href = `/get-file?file=${data.filename}`;
                    document.getElementById('result').style.display = 'block';
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                } else {
                    alert(data.error);
                }
            } catch(e) {
                alert("Server Timeout");
            } finally {
                document.getElementById('loader').style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

def delete_file(path):
    time.sleep(300)
    if os.path.exists(path):
        os.remove(path)

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/extract', methods=['POST'])
def extract():
    data = request.json
    url = data.get('url').split('?')[0] # Auto-strip tracking parameters
    fmt = data.get('format', 'mp4')
    
    if any(x in url.lower() for x in ["youtube", "youtu.be"]):
        return jsonify({'success': False, 'error': 'YouTube is restricted.'})

    fid = str(uuid.uuid4())[:8]
    
    # Elite-Level Options
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/{fid}.%(ext)s',
        'quiet': True,
        'noplaylist': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'extractor_args': {'soundcloud': {'formats': ['http_mp3']}},
    }

    if fmt == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
        })
    else:
        # Tries standard MP4 first, falls back to best available
        ydl_opts.update({'format': 'best[ext=mp4]/best'})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if fmt == 'mp3':
                filename = os.path.splitext(filename)[0] + ".mp3"

            threading.Thread(target=delete_file, args=(filename,)).start()

            return jsonify({
                'success': True,
                'title': info.get('title', 'Untitled Media'),
                'thumbnail': info.get('thumbnail') or 'https://via.placeholder.com/600x400/111/00f2ff?text=PREVIEW+READY',
                'filename': os.path.basename(filename)
            })
    except Exception as e:
        return jsonify({'success': False, 'error': "Link incompatible or provider blocked."})

@app.route('/get-file')
def get_file():
    fname = request.args.get('file')
    fpath = os.path.join(DOWNLOAD_FOLDER, os.path.basename(fname))
    if os.path.exists(fpath):
        return send_file(fpath, as_attachment=True)
    return "Error: File expired.", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
