from flask import Flask, request, render_template_string, send_file, jsonify
import yt_dlp
import os
import uuid

app = Flask(__name__)

# Temporary storage
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
        :root { --primary: #00f2ff; --bg: #050505; --card: rgba(25, 25, 25, 0.9); }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: white; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { width: 90%; max-width: 500px; padding: 2rem; background: var(--card); border-radius: 2rem; border: 1px solid rgba(0,242,255,0.2); text-align: center; box-shadow: 0 0 30px rgba(0,0,0,0.5); position: relative; }
        
        /* Modern Input */
        .input-group { background: #111; border: 1px solid #333; border-radius: 1rem; display: flex; margin-top: 2rem; overflow: hidden; }
        input { flex: 1; background: transparent; border: none; padding: 1rem; color: white; outline: none; }
        
        button { width: 100%; margin-top: 1rem; padding: 1rem; background: var(--primary); color: black; border: none; border-radius: 1rem; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { box-shadow: 0 0 15px var(--primary); transform: translateY(-2px); }

        /* Previewer Styling */
        #preview { display: none; margin-top: 2rem; border-top: 1px solid #333; padding-top: 1.5rem; animation: fadeIn 0.5s ease; }
        .thumb-img { width: 100%; border-radius: 1rem; border: 2px solid var(--primary); margin-bottom: 1rem; box-shadow: 0 10px 20px rgba(0,0,0,0.5); }
        h4 { margin: 10px 0; color: var(--primary); }

        /* Full Screen Loader */
        #loader-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); display: none; border-radius: 2rem; flex-direction: column; justify-content: center; align-items: center; z-index: 10; }
        .spinner { width: 50px; height: 50px; border: 3px solid rgba(0,242,255,0.1); border-top: 3px solid var(--primary); border-radius: 50%; animation: spin 1s infinite linear; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    </style>
</head>
<body>
    <div class="container">
        <div id="loader-overlay">
            <div class="spinner"></div>
            <p style="color: var(--primary); margin-top: 1rem;">SNATCHING MEDIA...</p>
        </div>

        <h1 style="margin:0;">NEXUS<span style="color:var(--primary)">ULTRA</span></h1>
        
        <div class="input-group">
            <input type="text" id="url" placeholder="Paste link (TikTok, Vimeo, etc.)" autocomplete="off">
        </div>
        
        <button onclick="fetchMedia()">DOWNLOAD NOW</button>

        <div id="preview">
            <img id="thumb-img" class="thumb-img" src="" alt="Thumbnail">
            <h4 id="video-title">Loading Title...</h4>
            <p style="font-size: 0.8rem; color: #888;">Extraction Complete! Check your downloads.</p>
        </div>
    </div>

    <script>
        async function fetchMedia() {
            const url = document.getElementById('url').value;
            const loader = document.getElementById('loader-overlay');
            const preview = document.getElementById('preview');

            if (!url) return alert("Paste a link first!");
            if (url.includes("youtube.com") || url.includes("youtu.be")) return alert("YouTube is not supported on this server.");

            loader.style.display = 'flex';
            preview.style.display = 'none';

            try {
                const response = await fetch('/extract', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url})
                });
                
                const data = await response.json();

                if (data.success) {
                    // SET THE THUMBNAIL AND TITLE
                    document.getElementById('thumb-img').src = data.thumbnail;
                    document.getElementById('video-title').innerText = data.title;
                    preview.style.display = 'block';

                    // Trigger actual file download
                    window.location.href = `/get-file?file=${data.filename}`;
                } else {
                    alert("Error: " + data.error);
                }
            } catch (e) {
                alert("Server Error");
            } finally {
                loader.style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/extract', methods=['POST'])
def extract():
    data = request.json
    url = data.get('url')
    
    # Block YouTube
    if "youtube" in url.lower():
        return jsonify({'success': False, 'error': 'YouTube Blocked'})

    fid = str(uuid.uuid4())[:8]
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': f'{DOWNLOAD_FOLDER}/{fid}.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # THIS EXTRACTS THE THUMBNAIL DATA
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Get thumbnail (fallback to placeholder if not found)
            thumbnail_url = info.get('thumbnail') or info.get('thumbnails', [{}])[0].get('url') or 'https://via.placeholder.com/640x360'

            return jsonify({
                'success': True,
                'title': info.get('title', 'Video File'),
                'thumbnail': thumbnail_url,
                'filename': os.path.basename(filename)
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get-file')
def get_file():
    fname = request.args.get('file')
    fpath = os.path.join(DOWNLOAD_FOLDER, fname)
    if os.path.exists(fpath):
        return send_file(fpath, as_attachment=True)
    return "Not Found", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
