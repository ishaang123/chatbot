from flask import Flask, request, render_template_string, send_file
import yt_dlp
import os

app = Flask(__name__)

# The HTML interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>YT Downloader</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; margin-top: 50px; background-color: #f4f4f9; }
        .container { width: 450px; text-align: center; padding: 20px; background: white; border-radius: 10px; shadow: 0 4px 6px rgba(0,0,0,0.1); }
        input[type="text"] { width: 90%; padding: 12px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 5px; }
        button { padding: 12px 24px; cursor: pointer; background: #ff0000; color: white; border: none; border-radius: 5px; font-weight: bold; }
        button:hover { background: #cc0000; }
        .status { margin-top: 20px; color: #555; }
    </style>
</head>
<body>
    <div class="container">
        <h2>YouTube Downloader</h2>
        <form method="POST">
            <input type="text" name="url" placeholder="Paste YouTube URL here" required>
            <button type="submit">Download to Computer</button>
        </form>
        {% if message %}
            <p class="status">{{ message }}</p>
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
        
        # Options to bypass bot detection and get the best file
        ydl_opts = {
            'format': 'best',
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            # Bypasses the "Sign in to confirm you're not a bot" error
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info and download
                info = ydl.extract_info(url, download=True)
                # Get the actual filename generated
                filename = ydl.prepare_filename(info)
            
            # Send the file from Render's server to your local Downloads folder
            response = send_file(filename, as_attachment=True)
            
            # Optional: Clean up the file from the server after sending
            # Note: In a production app, you'd use a background task to delete this.
            return response

        except Exception as e:
            message = f"Error: {str(e)}"
            
    return render_template_string(HTML_TEMPLATE, message=message)

if __name__ == '__main__':
    # Required for Render to bind to the correct port and address
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
