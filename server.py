from flask import Flask, request, render_template_string, send_file, jsonify
import yt_dlp
import os
import uuid
import threading
import time

app = Flask(__name__)

# Config
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Ultra | Media Fetcher</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/js/all.min.js"></script>
    <style>
        :root { --primary: #00f2ff; --bg: #0a0a0a; --card: #151515; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: white; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { width: 90%; max-width: 450px; padding: 2rem; background: var(--card); border-radius: 1.5rem; border: 1px solid #222; text-align: center; }
        
        .type-selector { display: flex; gap: 10px; margin-bottom: 1.5rem; }
        .t-btn { flex: 1; padding: 12px; border-radius: 10px; background: #222; cursor: pointer; border: 1px solid #333; transition: 0.3s; font-weight: bold; font-size: 0.8rem; }
        .t-btn.active { background: var(--primary); color: black; border-color: var(--primary); }

        .input-group { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; display: flex; margin-bottom: 1rem; }
        input { flex: 1; background: transparent; border: none; padding: 1rem; color: white; outline: none; }
        
        #dl-btn { width: 100%; padding: 1rem; background: var(--primary); color: black; border: none; border-radius: 12px; font-weight: 800; cursor: pointer; }
        
        #preview { display: none; margin-top: 1.5rem; animation: slideUp 0.4s ease; }
        .thumb { width: 100%; border-radius: 12px; margin-bottom: 10px; border: 1px solid #444; }

        #overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: none; flex-direction: column; justify-content: center; align-items: center; z-index: 100; backdrop-filter: blur(5px); }
        .loader { width: 40px; height: 40px; border: 4px solid #222; border-top: 4px solid var(--primary); border-radius: 50%; animation: spin 1s infinite linear; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    </style>
</head>
<body>
    <div id="overlay">
        <div class="loader"></div>
        <p style="margin-top: 15px; font-weight: bold; color: var(--primary)">CONVERTING MEDIA...</p>
    </div>

    <div class="container">
        <h1 style="margin-bottom: 1.5rem; letter-spacing: -1px;">NEXUS<span style="color:var(--primary)">ULTRA</span></h1>
        
        <div class="type-selector">
            <div id="mp4" class="t-btn active" onclick="setFormat('mp4')"><i class="fas fa-video"></i> MP4 VIDEO</div>
            <div id="mp3" class="t-btn" onclick="setFormat('mp3')"><i class="fas fa-headphones"></i> MP3 AUDIO</div>
        </div>

        <div class="input-group">
            <input type="text" id="url" placeholder="Paste link here..." autocomplete="off">
        </div>
        
        <button id="dl-btn" onclick="startDownload()">GENERATE LINK</button>

        <div id="preview">
            <img id="p-img" class="thumb" src="">
            <div id="p-title" style="font-size: 0.9rem; margin-bottom: 10px; opacity: 0.8;"></div>
            <a id="p-link" style="text-decoration: none;"><button id="dl-btn" style="background: #fff;">DOWNLOAD FILE</button></a>
        </div>
    </div>

    <script>
        let format = 'mp4';
        function setFormat(f) {
            format = f;
            document.getElementById('mp4').className = f === 'mp4' ? 't-btn active' : 't-btn';
            document.getElementById('mp3').className = f === 'mp3' ? 't-btn active' : 't-btn';
        }

        async function startDownload() {
            const url = document.getElementById('url').value;
            if(!url) return alert("URL is missing!");

            document.getElementById('overlay').style.display = 'flex';
            
            try {
                const res = await fetch('/extract', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url, format })
                });
                const data = await res.json();
                
                if(data.success) {
                    document.getElementById('p-img').src = data.thumbnail;
                    document.getElementById('p-title').innerText = data.title;
                    document.getElementById('p-link').href = `/get-file?file=${data.filename}`;
                    document.getElementById('preview').style.display = 'block';
                } else {
                    alert("Error: " + data.error);
                }
            } catch(e) {
                alert("Server busy. Try again.");
            } finally {
                document.getElementById('overlay').style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

def delete_later(path):
    """Wait 5 minutes then delete the file to save space on Render."""
    time.sleep(300)
    if os.path.exists(path):
        os.remove(path)

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/extract', methods=['POST'])
def extract():
    data = request.json
    url = data.get('url')
    fmt = data.get('format', 'mp4')
    
    # YouTube check (optional, but good for keeping Render accounts safe)
    if "youtube" in url.lower() or "youtu.be" in url.lower():
        return jsonify({'success': False, 'error': 'YouTube is restricted on this free instance.'})

    fid = str(uuid.uuid4())[:8]
    
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/{fid}.%(ext)s',
        'quiet': True,
        'noplaylist': True,
    }

    if fmt == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({'format': 'best[ext=mp4]/best'})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # If MP3, the filename extension needs to be swapped because prepare_filename 
            # shows the original extension (like .webm) before FFmpeg converts it.
            if fmt == 'mp3':
                filename = os.path.splitext(filename)[0] + ".mp3"

            # Auto-delete thread to keep Render storage clean
            threading.Thread(target=delete_later, args=(filename,)).start()

            return jsonify({
                'success': True,
                'title': info.get('title', 'Video Content'),
                'thumbnail': info.get('thumbnail') or 'https://via.placeholder.com/400',
                'filename': os.path.basename(filename)
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get-file')
def get_file():
    fname = request.args.get('file')
    fpath = os.path.join(DOWNLOAD_FOLDER, os.path.basename(fname))
    if os.path.exists(fpath):
        return send_file(fpath, as_attachment=True)
    return "Link expired (links last 5 minutes)", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
