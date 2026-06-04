import os
import requests
from flask import Flask, request, Response, render_template_string

app = Flask(__name__)

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

            const localProxyEndpoint = `${window.location.origin}/proxy?url=`;
            const fetchOptions = { method: 'GET', referrerPolicy: 'no-referrer' };

            try {
                // Step 1: Request manifest configurations
                statusDiv.innerText = "Routing metadata matrix...";
                progressBar.style.width = "10%";

                const targetMetadataUrl = `https://www.dailymotion.com/player/metadata/video/${videoId}`;
                const metaResponse = await fetch(`${localProxyEndpoint}${encodeURIComponent(targetMetadataUrl)}`, fetchOptions);
                if (!metaResponse.ok) throw new Error("Metadata request rejected.");
                const metadata = await metaResponse.json();
                
                const masterM3u8Url = metadata.qualities.auto[0].url;

                // Step 2: Grab the HLS index manifest mapping
                statusDiv.innerText = "Parsing streaming segment indexes...";
                progressBar.style.width = "25%";

                const masterResponse = await fetch(`${localProxyEndpoint}${encodeURIComponent(masterM3u8Url)}`, fetchOptions);
                if (!masterResponse.ok) throw new Error("Master manifest collection dropped.");
                const masterText = await masterResponse.text();

                // Correct relative sub-playlist matching structures
                const masterLines = masterText.split('\\n');
                let targetPlaylistUrl = "";
                let masterBaseUrl = masterM3u8Url.substring(0, masterM3u8Url.lastIndexOf('/') + 1);

                for (let i = 0; i < masterLines.length; i++) {
                    let line = masterLines[i].trim();
                    if (line && !line.startsWith('#')) {
                        targetPlaylistUrl = line.startsWith('http') ? line : masterBaseUrl + line;
                        break;
                    }
                }
                if (!targetPlaylistUrl) targetPlaylistUrl = masterM3u8Url;

                // Step 3: Fetch active data chunks sub-manifest layout
                statusDiv.innerText = "Mapping block fragment paths...";
                progressBar.style.width = "40%";
                
                const playlistResponse = await fetch(`${localProxyEndpoint}${encodeURIComponent(targetPlaylistUrl)}`, fetchOptions);
                if (!playlistResponse.ok) throw new Error("Index playlist mapping rejected.");
                const playlistText = await playlistResponse.text();

                const chunkLines = playlistText.split('\\n');
                const chunkUrls = [];
                let playlistBaseUrl = targetPlaylistUrl.substring(0, targetPlaylistUrl.lastIndexOf('/') + 1);

                for (let line of chunkLines) {
                    line = line.trim();
                    if (line && !line.startsWith('#')) {
                        chunkUrls.push(line.startsWith('http') ? line : playlistBaseUrl + line);
                    }
                }

                if (chunkUrls.length === 0) throw new Error("No active media sequences detected.");

                // Step 4: Stream fragments sequentially through local service proxy
                const videoPieces = [];
                // Capped at 35 segments to avoid resource crashing browser engine tabs
                const totalChunks = Math.min(chunkUrls.length, 35); 

                for (let i = 0; i < totalChunks; i++) {
                    const percentDone = 40 + Math.floor((i / totalChunks) * 50);
                    progressBar.style.width = `${percentDone}%`;
                    statusDiv.innerText = `Buffering media asset chunk ${i + 1} of ${totalChunks}...`;

                    const chunkResponse = await fetch(`${localProxyEndpoint}${encodeURIComponent(chunkUrls[i])}`, fetchOptions);
                    if (!chunkResponse.ok) continue; // Bypass isolated dropped fragments safely

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

    # Clean headers emulating real browser calls to bypass anti-hotlinking rules
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.dailymotion.com/',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        res = requests.get(target_url, headers=headers, stream=True)
        
        excluded = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(n, v) for (n, v) in res.headers.items() if n.lower() not in excluded]
        
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
