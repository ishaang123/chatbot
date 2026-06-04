import os
import requests
from flask import Flask, request, Response, render_template_string

app = Flask(__name__)

# Minimalistic HTML UI featuring only the local network bypass architecture
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Ultra | Elite Proxy</title>
    <link href="https://fonts.googleapis.com/css2?family=Syncopate:wght@700&family=Outfit:wght@300;600;900&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #00f2ff; --bg: #020202; --card: rgba(12, 12, 12, 0.98); }
        * { box-sizing: border-box; transition: all 0.25s ease-out; }
        body { 
            font-family: 'Outfit', sans-serif; background: var(--bg); color: white;
            margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center;
            min-height: 100vh; background-image: radial-gradient(circle at 50% 10%, #001a1a 0%, #020202 100%);
        }
        .container { 
            width: 100%; max-width: 640px; margin: 40px auto; padding: 2.5rem; 
            background: var(--card); border-radius: 2rem; border: 1px solid rgba(255, 255, 255, 0.03); 
            text-align: center; backdrop-filter: blur(40px); box-shadow: 0 40px 120px rgba(0,0,0,0.9);
        }
        h1 { font-family: 'Syncopate', sans-serif; font-size: 1.8rem; margin: 0; letter-spacing: -3px; }
        .neon { color: var(--primary); text-shadow: 0 0 20px rgba(0,242,255,0.4); }
        
        #loading-container { width: 100%; margin: 20px 0; }
        #loading-status { font-size: 14px; margin-bottom: 10px; color: #aaa; }
        .bar-bg { width: 100%; background: #222; height: 8px; border-radius: 4px; overflow: hidden; }
        #loading-bar { width: 0%; height: 100%; background: var(--primary); transition: width 0.2s ease; }
        
        video { width: 100%; aspect-ratio: 16/9; border-radius: 15px; border: 1px solid #222; background: #000; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NEXUS<span class="neon">PROXY</span></h1>
        <p style="font-size: 0.7rem; opacity: 0.3; letter-spacing: 5px; margin: 10px 0 2rem 0;">NATIVE STREAM STITCHER</p>

        <div id="loading-container">
            <div id="loading-status">Initializing dynamic proxy pipeline...</div>
            <div class="bar-bg">
                <div id="loading-bar"></div>
            </div>
        </div>

        <video id="native-stitched-player" controls playsinline>
            Your browser does not support native video playback.
        </video>
    </div>

    <script>
        async function downloadAndStitchVideo(videoId) {
            const statusDiv = document.getElementById('loading-status');
            const progressBar = document.getElementById('loading-bar');
            const loadingContainer = document.getElementById('loading-container');
            const videoElement = document.getElementById('native-stitched-player');

            // Route calls directly back through your Flask proxy
            const localProxyEndpoint = `${window.location.origin}/proxy?url=`;

            try {
                // Step 1: Request manifest configurations
                statusDiv.innerText = "Routing metadata matrix...";
                progressBar.style.width = "15%";

                const targetMetadataUrl = `https://www.dailymotion.com/player/metadata/video/${videoId}`;
                const metaResponse = await fetch(`${localProxyEndpoint}${encodeURIComponent(targetMetadataUrl)}`);
                if (!metaResponse.ok) throw new Error("Metadata request rejected.");
                const metadata = await metaResponse.json();
                
                const m3u8Url = metadata.qualities.auto[0].url;

                // Step 2: Grab the HLS index manifest mapping
                statusDiv.innerText = "Parsing streaming segment indexes...";
                progressBar.style.width = "35%";

                const playlistResponse = await fetch(`${localProxyEndpoint}${encodeURIComponent(m3u8Url)}`);
                if (!playlistResponse.ok) throw new Error("Index playlist mapping rejected.");
                const playlistText = await playlistResponse.text();

                // Step 3: Match segment file vectors
                const chunkUrls = playlistText.split('\\n').filter(line => line.trim().startsWith('http'));
                if (chunkUrls.length === 0) throw new Error("No active media sequences detected.");

                // Step 4: Stream fragments sequentially through local service proxy
                const videoPieces = [];
                const totalChunks = chunkUrls.length;

                for (let i = 0; i < totalChunks; i++) {
                    const percentDone = 35 + Math.floor((i / totalChunks) * 55);
                    progressBar.style.width = `${percentDone}%`;
                    statusDiv.innerText = `Buffering media asset chunk ${i + 1} of ${totalChunks}...`;

                    const chunkResponse = await fetch(`${localProxyEndpoint}${encodeURIComponent(chunkUrls[i])}`);
                    if (!chunkResponse.ok) throw new Error(`Segment [${i}] buffer drop fault.`);

                    const chunkData = await chunkResponse.arrayBuffer();
                    videoPieces.push(chunkData);
                }

                // Step 5: Merge buffers and construct binary video blob data
                statusDiv.innerText = "Stitching chunk arrays into media package...";
                progressBar.style.width = "95%";
                const finalBlob = new Blob(videoPieces, { type: 'video/mp4' });
                const localVideoUrl = URL.createObjectURL(finalBlob);

                progressBar.style.width = "100%";
                setTimeout(() => {
                    loadingContainer.style.display = 'none';
                    videoElement.style.display = 'block';
                    videoElement.src = localVideoUrl;
                }, 300);

            } catch (error) {
                console.error(error);
                statusDiv.style.color = "#ff4444";
                statusDiv.innerText = "Proxy alignment failure or broken stream link target.";
            }
        }

        // Auto initialization parameter injects custom metadata target string
        downloadAndStitchVideo("{{ active_id }}");
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    # Renders the clean frontend layout with a target testing stream ID
    return render_template_string(HTML_TEMPLATE, active_id="x7tf8v2")

@app.route('/proxy')
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing URL target parameter", 400

    # Emulate necessary headers to bypass the origin gatekeeper
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    try:
        # Stream the response content to avoid heavy RAM usage spikes on small server nodes
        res = requests.get(target_url, headers=headers, stream=True)
        
        # Clean down hop-by-hop delivery configurations
        excluded = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(n, v) for (n, v) in res.headers.items() if n.lower() not in excluded]
        
        # Append dynamic origin properties to resolve browser CORS security constraints
        response_headers.append(('Access-Control-Allow-Origin', '*'))
        response_headers.append(('Access-Control-Allow-Headers', 'X-Requested-With, Origin'))

        return Response(
            res.iter_content(chunk_size=8192),
            status=res.status_code,
            headers=response_headers
        )
    except Exception as e:
        return f"Tunnel Connection Exception: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
