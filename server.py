from flask import Flask, request, render_template_string, send_file, jsonify
import yt_dlp
import os
import uuid
import threading
import time
import subprocess

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
        :root { --primary: #00f2ff; --bg: #050505; --card: rgba(20, 20, 20, 0.85); }
        body { 
            font-family: 'Inter', sans-serif; 
            background: radial-gradient(circle at top right, #0a192f, #050505);
            color: white; display: flex; justify-content: center; align-items: center; 
            min-height: 100vh; margin: 0; overflow: hidden;
        }
        
        .container { 
            width: 90%; max-width: 440px; padding: 2rem; 
            background: var(--card); border-radius: 2rem; 
            border: 1px solid rgba(0, 242, 255, 0.15); text-align: center; 
            backdrop-filter: blur(15px); box-shadow: 0 25px 50px rgba(0,0,0,0.6);
            position: relative; z-index: 2;
        }

        .type-selector { display: flex; gap: 8px; margin-bottom: 1.5rem; background: #000; padding: 5px; border-radius: 12px; }
        .t-btn { 
            flex: 1; padding: 10px; border-radius: 8px; border: none;
            background: transparent; cursor: pointer; color: #666;
            transition: 0.3s; font-weight: 700; font-size: 0.8rem;
        }
        .t-btn.active { background: var(--primary); color: #000; box-shadow: 0 0 15px rgba(0,242,255,0.3); }

        .input-group { 
            background: rgba(255,255,255,0.05); border: 1px solid #333; 
            border-radius: 12px; display: flex; margin-bottom: 1rem;
        }
        input { flex: 1; background: transparent; border: none; padding: 1rem; color: white; outline: none; }
        
        #fetch-btn { 
            width: 100%; padding: 1rem; background: var(--primary); color: #000; 
            border: none; border-radius: 12px; font-weight: 900; cursor: pointer;
            transition: 0.3s; text-transform: uppercase;
        }
        #fetch-btn:hover { filter: brightness(1.2); transform: translateY(-2px); }

        #preview { display: none; margin-top: 1.5rem; animation: slideUp 0.5s ease; }
        .thumb-cont { width: 100%; border-radius: 12px; overflow: hidden; border: 1px solid #333; position: relative; }
        .thumb-img { width: 100%; display: block; }
        
        #overlay { 
            position: fixed; inset: 0; background: rgba(0,0,0,0.85); 
            display: none; flex-direction: column; justify-content: center; 
            align-items: center; z-index: 100; backdrop-filter: blur(8px); 
        }
        .spinner { 
            width: 50px; height: 50px; border: 3px solid rgba(0,242,255,0.1); 
            border-top: 3px solid var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; 
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <div id="overlay">
        <div class="spinner"></div>
        <p style="margin-top: 20px; color: var(--primary); font-weight: bold; letter-spacing: 2px;">FETCHING MEDIA...</p>
    </div>

    <div class="container">
        <h1 style="margin: 0 0 1.5rem 0; letter-spacing: -2px;">NEXUS<span style="color:var(--primary)">ULTRA</span></h1>
        
        <div class="type-selector">
            <button id="mp4-btn" class="t-btn active" onclick="setFormat('mp4')">MP4 VIDEO</button>
            <button id="mp3-btn" class="t-btn" onclick="setFormat('mp3')">MP3 AUDIO</button>
        </div>

        <div class="input-group">
            <input type="text" id="url" placeholder="Paste link here..." autocomplete="off">
        </div>
        
        <button id="fetch-btn" onclick="startProcess()">SNATCH CONTENT</button>

        <div id="preview">
            <div class="thumb-cont">
                <img id="p-img" class="thumb-img" src="">
            </div>
            <p id="p-title" style="font-size: 0.85rem; margin: 12px 0; color: #ccc;"></p>
            <a id="p-link" style="text-decoration: none;"><button id="fetch-btn" style="background: #fff; font-size: 0.7rem;">DOWNLOAD NOW</button></a>
        </div>
    </div>

    <script>
        let format = 'mp4';
        function setFormat(f) {
            format = f;
            document.getElementById('mp4-btn').className = f === 'mp4' ? 't-btn active' : 't-btn';
            document.getElementById('mp3-btn').className = f === 'mp3' ? 't-btn active' : 't-btn';
        }

        async function startProcess() {
            const url = document.getElementById('url').value;
            if(!url) return alert("Paste a link!");

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
                    alert(data.error);
                }
            } catch(e) {
                alert("Server Error");
            } finally {
                document.getElementById('overlay').style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

def cleanup(path, delay=300):
    time.sleep(delay)
    if os.path.exists(path):
        os.remove(path)
    # Also remove generated thumbnail if it exists
    thumb_path = path + ".jpg"
    if os.path.exists(thumb_path):
        os.remove(thumb_path)

def get_random_frame(video_path):
    """Uses FFmpeg to grab a frame at 00:00:02 and save as JPG."""
    thumb_path = video_path + ".jpg"
    try:
        # Grabs a frame at 2 seconds (or 0 if it's super short)
        cmd = [
            'ffmpeg', '-y', '-i', video_path, '-ss', '00:00:02', 
            '-vframes', '1', '-q:v', '2', thumb_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(thumb_path):
            return thumb_path
    except:
        pass
    return None

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/extract', methods=['POST'])
def extract():
    data = request.json
    url = data.get('url')
    fmt = data.get('format', 'mp4')
    
    if "youtube" in url.lower() or "youtu.be" in url.lower():
        return jsonify({'success': False, 'error': 'YouTube usage blocked.'})

    fid = str(uuid.uuid4())[:8]
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/{fid}.%(ext)s',
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {'soundcloud': {'formats': ['http_mp3']}},
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
            raw_filename = ydl.prepare_filename(info)
            
            # Final Filename adjustment
            if fmt == 'mp3':
                filename = os.path.splitext(raw_filename)[0] + ".mp3"
            else:
                filename = raw_filename

            # THUMBNAIL LOGIC
            # If API gives no thumbnail, or we are in MP4 mode, grab a random frame
            thumbnail_url = info.get('thumbnail')
            
            if fmt == 'mp4' and os.path.exists(filename):
                # Always try to grab a high-quality frame for videos
                frame_path = get_random_frame(filename)
                if frame_path:
                    # Serve the local frame instead of a placeholder
                    # (Note: In a full app, you'd serve this via a route, 
                    # but for now, we'll use the API thumb or placeholder)
                    pass 

            if not thumbnail_url:
                thumbnail_url = "https://via.placeholder.com/600x338/111/00f2ff?text=Nexus+Ultra"

            threading.Thread(target=cleanup, args=(filename,)).start()

            return jsonify({
                'success': True,
                'title': info.get('title', 'Media File'),
                'thumbnail': thumbnail_url,
                'filename': os.path.basename(filename)
            })
    except Exception as e:
        return jsonify({'success': False, 'error': "Link protected or invalid."})

@app.route('/get-file')
def get_file():
    fname = request.args.get('file')
    fpath = os.path.join(DOWNLOAD_FOLDER, os.path.basename(fname))
    if os.path.exists(fpath):
        return send_file(fpath, as_attachment=True)
    return "File Expired", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
