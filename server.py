from flask import Flask, request, render_template_string
import yt_dlp
import os

app = Flask(__name__)

# The HTML interface embedded directly in the Python script
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>YT Downloader</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; margin-top: 50px; }
        .container { width: 400px; text-align: center; }
        input[type="text"] { width: 100%; padding: 10px; margin-bottom: 10px; }
        button { padding: 10px 20px; cursor: pointer; background: #ff0000; color: white; border: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2>YouTube Downloader</h2>
        <form method="POST">
            <input type="text" name="url" placeholder="Paste YouTube URL here" required>
            <button type="submit">Download Best Quality</button>
        </form>
        {% if message %}
            <p>{{ message }}</p>
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
        
        # yt-dlp options: downloads to the current folder
        ydl_opts = {
            'format': 'best',
            'outtmpl': '%(title)s.%(ext)s',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            message = "Download successful! Check your project folder."
        except Exception as e:
            message = f"Error: {str(e)}"
            
    return render_template_string(HTML_TEMPLATE, message=message)

import os

if __name__ == '__main__':
    # Use the PORT environment variable provided by Render, default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
