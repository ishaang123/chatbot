from flask import Flask, request, render_template_string, send_file
import yt_dlp
import os

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>YT Downloader - 2026 Stable</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; margin-top: 50px; background-color: #f4f4f9; }
        .container { width: 450px; text-align: center; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        input[type="text"] { width: 90%; padding: 12px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 5px; }
        button { padding: 12px 24px; cursor: pointer; background: #ff0000; color: white; border: none; border-radius: 5px; font-weight: bold; }
        .status { margin-top: 20px; color: #555; background: #eee; padding: 10px; border-radius: 5px; word-wrap: break-word; font-size: 13px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>YouTube Downloader</h2>
        <form method="POST">
            <input type="text" name="url" placeholder="Paste YouTube URL here" required>
            <button type="submit">Download MP4</button>
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
        
        ydl_opts = {
            # Forces 720p or 360p pre-merged MP4 files (No FFmpeg needed)
            'format': '22/18/best',
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            'cookiefile': 'cookies.txt',
            # Spoofing Safari on Mac helps bypass Chrome-specific bot checks
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'extractor_args': {
                'youtube': {
                    'player_client': ['web_safari'],
                    'po_token': 'web+none'
                }
            },
            'compat_opts': {'no-youtube-prefer-oauth2'},
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
            return send_file(filename, as_attachment=True)

        except Exception as e:
            message = str(e)
            
    return render_template_string(HTML_TEMPLATE, message=message)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
