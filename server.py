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
        :root { --primary: #00f2ff; --bg: #050505; --card: rgba(20, 20, 20, 0.8); }
        body { 
            font-family: 'Inter', sans-serif; 
            background: radial-gradient(circle at top right, #1a1a2e, #050505);
            color: white; display: flex; justify-content: center; align-items: center; 
            min-height: 100vh; margin: 0; overflow-x: hidden;
        }
        
        .container { 
            width: 90%; max-width: 450px; padding: 2.5rem; 
            background: var(--card); border-radius: 2rem; 
            border: 1px solid rgba(255,255,255,0.1); text-align: center; 
            backdrop-filter: blur(20px); box-shadow: 0 20px 50px rgba(0,0,0,0.5);
            transition: transform 0.3s ease;
        }

        .type-selector { 
            display: flex; gap: 10px; margin-bottom: 1.5rem; 
            background: rgba(0,0,0,0.3); padding: 5px; border-radius: 15px;
        }
        .t-btn { 
            flex: 1; padding: 12px; border-radius: 12px; border: none;
            background: transparent; cursor: pointer; color: #888;
            transition: 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); font-weight: bold; 
        }
        .t-btn.active { background: var(--primary); color: black; box-shadow: 0 0 20px rgba(0,242,255,0.4); }
        .t-btn.disabled { opacity: 0.2; cursor: not-allowed; filter: grayscale(1); }

        .input-group { 
            background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); 
            border-radius: 15px; display: flex; margin-bottom: 1.5rem;
            transition: 0.3s;
        }
        .input-group:focus-within { border-color: var(--primary); background: rgba(255,255,255,0.08); }
        input { flex: 1; background: transparent; border: none; padding: 1.2rem; color: white; outline: none; font-size: 1rem; }
        
        #dl-btn { 
            width: 100%; padding: 1.2rem; background: white; color: black; 
            border: none; border-radius: 15px; font-weight: 900; cursor: pointer;
            text-transform: uppercase; letter-spacing: 1px; transition: 0.3s;
        }
        #dl-btn:hover { transform: scale(1.02); background: var(--primary); }

        /* Preview Section */
        #preview { display: none; margin-top: 2rem; animation: slideUp 0.6s ease forwards; }
        .thumb-wrapper { position: relative; cursor: pointer; overflow: hidden; border-radius: 15px; line-height: 0; }
        .thumb { width: 100%; transition: 0.5s; }
        .thumb-wrapper:hover .thumb { transform: scale(1.1) rotate(2deg); filter: brightness(0.7); }
        .play-overlay { 
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            font-size: 3rem; color: white; opacity: 0; transition: 0.3s;
        }
        .thumb-wrapper:hover .play-overlay { opacity: 1; }

        #overlay { 
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background: rgba(0,0,0,0.9); display: none; flex-direction: column; 
            justify-content: center; align-items: center; z-index: 100; backdrop-filter: blur(10px); 
        }
        .loader { 
            width: 60px; height: 60px; border: 3px solid transparent; 
            border-top-color: var(--primary); border-bottom-color: var(--primary);
            border-radius: 50%; animation: spin 1.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite; 
        }

        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    </style>
</head>
<body>
    <div id="overlay">
        <div class="loader"></div>
        <p id="loader-text" style="margin-top: 20px; font-weight: bold; color: var(--primary); letter-spacing: 3px;">ANALYZING...</p>
    </div>

    <div class="container">
        <h1 style="margin: 0 0 1.5rem 0; font-size: 2rem; letter-spacing: -2px;">NEXUS<span style="color:var(--primary)">ULTRA</span></h1>
        
        <div class="type-selector">
            <button id="mp4-btn" class="t-btn active" onclick="setFormat('mp4')">VIDEO</button>
            <button id="mp3-btn" class="t-btn" onclick="setFormat('mp3')">AUDIO</button>
        </div>

        <div class="input-group">
            <input type="text" id="url" placeholder="Paste link (SoundCloud, TikTok...)" oninput="checkLink()">
        </div>
        
        <button id="dl-btn" onclick="startDownload()">Fetch Content</button>

        <div id="preview">
            <div class="thumb-wrapper" onclick="openMedia()">
                <img id="p-img" class="thumb" src="">
                <div class="play-overlay"><i class="fas fa-play-circle"></i></div>
            </div>
            <p id="p-title" style="font-size: 0.9rem; margin: 15px 0; font-weight: 500;"></p>
            <a id="p-link" style="text-decoration: none;"><button id="dl-btn" style="background: var(--primary); font-size: 0.8rem;">Save to Device</button></a>
        </div>
    </div>

    <script>
        let format = 'mp4';
        let currentFileData = null;

        function checkLink() {
            const url = document.getElementById('url').value.toLowerCase();
            const mp4Btn = document.getElementById('mp4-btn');
            
            // Auto-detect audio-only sites
            if(url.includes('soundcloud') || url.includes('bandcamp') || url.includes('mixcloud')) {
                setFormat('mp3');
                mp4Btn.classList.add('disabled');
                mp4Btn.onclick = null;
            } else {
                mp4Btn.classList.remove('disabled');
                mp4Btn.onclick = () => setFormat('mp4');
            }
        }

        function setFormat(f) {
            format = f;
            document.getElementById('mp4-btn').className = f === 'mp4' ? 't-btn active' : 't-btn';
            document.getElementById('mp3-btn').className = f === 'mp3' ? 't-btn active' : 't-btn';
        }

        async function startDownload() {
            const url = document.getElementById('url').value;
            if(!url) return;

            document.getElementById('overlay').style.display = 'flex';
            document.getElementById('loader-text').innerText = "SNATCHING MEDIA...";
            
            try {
                const res = await fetch('/extract', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url, format })
                });
                const data = await res.json();
                
                if(data.success) {
                    currentFileData = data;
                    document.getElementById('p-img').src = data.thumbnail;
                    document.getElementById('p-title').innerText = data.title;
                    document.getElementById('p-link').href = `/get-file?file=${data.filename}`;
                    document.getElementById('preview').style.display = 'block';
                } else {
                    alert(data.error);
                }
            } catch(e) {
                alert("Server Connection Failed");
            } finally {
                document.getElementById('overlay').style.display = 'none';
            }
        }

        function openMedia() {
            if(currentFileData) {
                // Creates a temporary "Cinema" view or simply triggers the download
                window.open(`/get-file?file=${currentFileData.filename}`, '_blank');
            }
        }
    </script>
</body>
</html>
"""

def delete_later(path):
    time.sleep(600) # Increased to 10 mins
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
    
    if "youtube" in url.lower() or "youtu.be" in url.lower():
        return jsonify({'success': False, 'error': 'YouTube restricted.'})

    fid = str(uuid.uuid4())[:8]
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/{fid}.%(ext)s',
        'quiet': True,
        'noplaylist': True,
        # THE SOUNDCLOUD SECRET SAUCE:
        'extractor_args': {
            'soundcloud': {
                'formats': ['http_mp3', 'http_aac', 'http_opus']
            }
        },
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
        ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Soundcloud fix: try to get info first to avoid HLS errors
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if fmt == 'mp3':
                # Force rename to .mp3 because yt-dlp might leave it as .webm or .m4a before conversion
                base_path = os.path.splitext(filename)[0]
                if os.path.exists(base_path + ".mp3"):
                    filename = base_path + ".mp3"
                else:
                    filename = base_path + ".mp3" # Post-processor will create this

            threading.Thread(target=delete_later, args=(filename,)).start()

            return jsonify({
                'success': True,
                'title': info.get('title', 'Media Content'),
                'thumbnail': info.get('thumbnail') or 'https://via.placeholder.com/400x225/111/00f2ff?text=No+Thumbnail',
                'filename': os.path.basename(filename)
            })
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}") # Check your Render logs for this!
        return jsonify({'success': False, 'error': "SoundCloud Link Protected or Rate Limited."})

@app.route('/get-file')
def get_file():
    fname = request.args.get('file')
    fpath = os.path.join(DOWNLOAD_FOLDER, os.path.basename(fname))
    if os.path.exists(fpath):
        return send_file(fpath, as_attachment=True)
    return "Link Expired", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
