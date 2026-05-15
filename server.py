from flask import Flask, request, render_template_string, send_file
import yt_dlp
import os

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>YT Downloader - Stable</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; margin-top: 50px; background-color: #f4f4f9; }
        .container { width: 450px; text-align: center; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        input[type="text"] { width: 90%; padding: 12px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 5px; }
        button { padding: 12px 24px; cursor: pointer; background: #ff0000; color: white; border: none; border-radius: 5px; font-weight: bold; }
        button:hover { background: #cc0000; }
        .status { margin-top: 20px; color: #555; background: #eee; padding: 10px; border-radius: 5px; word-wrap: break-word; }
    </style>
</head>
<body>
    <div class="container">
        <h2>YouTube Downloader</h2>
        <p style="font-size: 12px; color: #666;">Stable Version (720p Max)</p>
        <form method="POST">
            <input type="text" name="url" placeholder="Paste YouTube URL here" required>
            <button type="submit">Download to Computer</button>
        </form>
        {% if message %}
            <div class="status"><strong>Status:</strong><br>{{ message }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ""
    if request.method == 'POST':
        url = request.form.get('url')
        
        # Best reliable options for Render/Cloud environments
        ydl_opts = {
            # Asks for best single file with video+audio (usually 720p MP4)
            # This avoids needing FFmpeg which isn't on Render by default
            'format': 'best[ext=mp4]/best',
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            # Uses the cookie file you uploaded to GitHub
            'cookiefile': 'cookies.txt', 
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 1. Download the file to the Render server
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
            # 2. Push the file from the Render server to YOUR browser
            return send_file(filename, as_attachment=True)

        except Exception as e:
            message = f"Error: {str(e)}"
            
    return render_template_string(HTML_TEMPLATE, message=message)

if __name__ == '__main__':
    # Dynamic port binding for Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
