from flask import Flask, request, render_template_string, send_file
import yt_dlp
import os

app = Flask(__name__)

# Modern, responsive CSS for a better look
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MediaFetch | Universal Downloader</title>
    <style>
        :root {
            --bg: #0f172a;
            --card: #1e293b;
            --accent: #38bdf8;
            --text: #f1f5f9;
        }
        body { 
            font-family: 'Inter', -apple-system, sans-serif; 
            background-color: var(--bg); 
            color: var(--text);
            display: flex; justify-content: center; align-items: center; 
            height: 100vh; margin: 0;
        }
        .container { 
            width: 90%; max-width: 500px; 
            padding: 2.5rem; background: var(--card); 
            border-radius: 1.5rem; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
            text-align: center;
        }
        h2 { margin-bottom: 0.5rem; font-size: 1.8rem; color: var(--accent); }
        p { color: #94a3b8; margin-bottom: 2rem; font-size: 0.9rem; }
        input[type="text"] { 
            width: 100%; padding: 1rem; margin-bottom: 1rem; 
            background: #0f172a; border: 2px solid #334155; 
            border-radius: 0.75rem; color: white; box-sizing: border-box;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus { outline: none; border-color: var(--accent); }
        button { 
            width: 100%; padding: 1rem; cursor: pointer; 
            background: var(--accent); color: #0f172a; 
            border: none; border-radius: 0.75rem; 
            font-weight: 700; font-size: 1rem; transition: transform 0.2s, opacity 0.2s;
        }
        button:hover { opacity: 0.9; transform: translateY(-2px); }
        .status { 
            margin-top: 1.5rem; padding: 1rem; 
            background: rgba(56, 189, 248, 0.1); 
            border-radius: 0.5rem; border: 1px solid rgba(56, 189, 248, 0.2);
            font-size: 0.85rem; color: var(--accent);
        }
        .error { color: #f87171; background: rgba(248, 113, 113, 0.1); border-color: rgba(248, 113, 113, 0.2); }
    </style>
</head>
<body>
    <div class="container">
        <h2>MediaFetch</h2>
        <p>Universal Downloader (Vimeo, TikTok, Twitter, etc.)<br><strong>YouTube not supported.</strong></p>
        <form method="POST">
            <input type="text" name="url" placeholder="Paste link here..." required autocomplete="off">
            <button type="submit">Download Video</button>
        </form>
        {% if message %}
            <div class="status {{ 'error' if 'Error' in message }}">
                {{ message }}
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ""
    if request.method == 'POST':
        url = request.form.get('url').strip()
        
        # Block YouTube specifically
        if "youtube.com" in url.lower() or "youtu.be" in url.lower():
            message = "Error: YouTube is not supported by this tool."
            return render_template_string(HTML_TEMPLATE, message=message)

        ydl_opts = {
            'format': 'best',
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
            return send_file(filename, as_attachment=True)

        except Exception as e:
            message = f"Error: {str(e)}"
            
    return render_template_string(HTML_TEMPLATE, message=message)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
