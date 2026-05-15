from flask import Flask, request, render_template_string, send_file
import yt_dlp
import os

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>YT Downloader - OAuth2</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; margin-top: 50px; background-color: #f4f4f9; }
        .container { width: 450px; text-align: center; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        input[type="text"] { width: 90%; padding: 12px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 5px; }
        button { padding: 12px 24px; cursor: pointer; background: #ff0000; color: white; border: none; border-radius: 5px; font-weight: bold; }
        .status { margin-top: 20px; color: #555; white-space: pre-wrap; font-size: 14px; text-align: left; background: #eee; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>YouTube Downloader (OAuth2)</h2>
        <form method="POST">
            <input type="text" name="url" placeholder="Paste YouTube URL here" required>
            <button type="submit">Download</button>
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
            'format': 'best',
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            # Acts like a Smart TV to trigger the device code login
            'username': 'oauth2',
            'password': '', 
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            return send_file(filename, as_attachment=True)
            
        except Exception as e:
            error_str = str(e)
            # Catch the specific OAuth2 instruction and display it to the user
            if "google.com/device" in error_str:
                message = f"ACTION REQUIRED: {error_str}"
            else:
                message = f"Error: {error_str}"
            
    return render_template_string(HTML_TEMPLATE, message=message)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
