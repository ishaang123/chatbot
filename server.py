import os
import re
import urllib.parse
from flask import Flask, request, Response, render_template_string
import yt_dlp
import requests
from yt_dlp.networking.impersonate import ImpersonateTarget

app = Flask(__name__)

PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        /* ==========================================================================
           1. CORE CANVAS ARCHITECTURE
           ========================================================================== */
        html, body {
            margin: 0; padding: 0; width: 100%; height: 100%;
            background-color: #030303; overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex; justify-content: center; align-items: center;
        }

        :root {
            --brand-accent: #ff0055;
            --brand-gradient: linear-gradient(90deg, #6366f1, #ff0055);
            --glass-bg: rgba(15, 15, 24, 0.45);
            --glass-border: rgba(255, 255, 255, 0.08);
            --glass-glow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        /* Video Workspace Container */
        .custom-player-wrapper {
            position: relative;
            width: 100%;
            height: 100%;
            max-width: 100%;
            max-height: 100%;
            background-color: #000;
            overflow: hidden;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        video {
            width: 100%;
            height: 100%;
            object-fit: contain;
            cursor: pointer;
        }

        /* Hide native player controls universally */
        video::-webkit-media-controls { display: none !important; }

        /* ==========================================================================
           2. PREMIUM THEMED NEON LOADER OVERLAY
           ========================================================================== */
        #video-loader {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: #09090b; z-index: 5;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            transition: opacity 0.4s ease;
            pointer-events: none;
        }

        .spinner {
            box-sizing: border-box; width: 64px; height: 64px;
            border: 4px solid rgba(99, 102, 241, 0.1);
            border-top: 4px solid #6366f1;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        .loader-text {
            margin-top: 22px; font-size: 0.8rem; font-weight: 600;
            color: #ffffff; letter-spacing: 2px; text-transform: uppercase;
            text-shadow: 0 0 12px rgba(99, 102, 241, 0.4);
        }

        /* ==========================================================================
           3. HIGH-END GLASSMORPHISM UI CONTROLS
           ========================================================================== */
        .ui-controls-panel {
            position: absolute;
            bottom: 24px; left: 24px;
            width: calc(100% - 48px);
            box-sizing: border-box;
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 12px 18px;
            box-shadow: var(--glass-glow);
            z-index: 3;
            opacity: 1;
            transform: translateY(0);
            transition: opacity 0.3s cubic-bezier(0.25, 1, 0.5, 1), transform 0.3s cubic-bezier(0.25, 1, 0.5, 1);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        /* Auto-hide panel layout state */
        .custom-player-wrapper.user-inactive .ui-controls-panel {
            opacity: 0;
            transform: translateY(12px);
            cursor: none;
        }

        .controls-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
        }

        .controls-cluster {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        /* Universal Clean Icon Buttons */
        .control-btn {
            background: none;
            border: none;
            color: #f4f4f5;
            cursor: pointer;
            padding: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.15s ease, color 0.15s ease;
        }

        .control-btn:hover {
            color: #ffffff;
            transform: scale(1.08);
        }

        .control-btn svg {
            width: 22px;
            height: 22px;
            fill: currentColor;
        }

        /* Time Text Readout Settings */
        .time-display {
            color: #d4d4d8;
            font-size: 0.85rem;
            font-weight: 500;
            letter-spacing: 0.5px;
            user-select: none;
        }

        /* ==========================================================================
           4. CUSTOM TIMELINE PROGRESS SLIDER TRACKS
           ========================================================================== */
        .timeline-container {
            width: 100%;
            position: relative;
            cursor: pointer;
            height: 6px;
            display: flex;
            align-items: center;
        }

        .timeline-bar {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.12);
            border-radius: 4px;
            position: relative;
            overflow: hidden;
        }

        .play-progress {
            height: 100%;
            width: 0%;
            background: var(--brand-gradient);
            border-radius: 4px;
            position: absolute;
            top: 0; left: 0;
        }

        /* ==========================================================================
           5. SLICK HOVER VOLUME CONTROLLER PANEL
           ========================================================================== */
        .volume-panel {
            display: flex;
            align-items: center;
            gap: 0;
            overflow: hidden;
            transition: gap 0.2s ease;
        }

        .volume-slider-wrapper {
            width: 0;
            opacity: 0;
            display: flex;
            align-items: center;
            transition: width 0.25s ease, opacity 0.2s ease;
        }

        .volume-panel:hover .volume-slider-wrapper,
        .volume-panel:focus-within .volume-slider-wrapper {
            width: 70px;
            opacity: 1;
        }

        .volume-panel:hover { gap: 6px; }

        input[type="range"].volume-slider {
            -webkit-appearance: none;
            width: 100%;
            background: transparent;
            cursor: pointer;
        }

        input[type="range"].volume-slider:focus { outline: none; }

        input[type="range"].volume-slider::-webkit-slider-runnable-track {
            width: 100%;
            height: 4px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 2px;
        }

        input[type="range"].volume-slider::-webkit-slider-thumb {
            height: 12px;
            width: 12px;
            border-radius: 50%;
            background: #ffffff;
            -webkit-appearance: none;
            margin-top: -4px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.4);
        }
    </style>
</head>
<body>

    <div class="custom-player-wrapper" id="player-container">
        <div id="video-loader">
            <div class="spinner"></div>
            <div class="loader-text">Decrypting Stream Matrix</div>
        </div>

        <video id="video-engine" playsinline>
            <source src="/manifest?url={{ target_url | urlencode }}" type="application/x-mpegURL">
            <source src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4" type="video/mp4">
        </video>

        <div class="ui-controls-panel">
            <div class="timeline-container" id="timeline-box">
                <div class="timeline-bar">
                    <div class="play-progress" id="progress-line"></div>
                </div>
            </div>

            <div class="controls-row">
                <div class="controls-cluster">
                    <button class="control-btn" id="play-pause-btn" title="Toggle Playback">
                        <svg viewBox="0 0 24 24" id="play-icon"><path d="M8 5v14l11-7z"/></svg>
                        <svg viewBox="0 0 24 24" id="pause-icon" style="display: none;"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                    </button>

                    <div class="time-display">
                        <span id="current-time-string">0:00</span> / <span id="duration-time-string">0:00</span>
                    </div>
                </div>

                <div class="controls-cluster">
                    <div class="volume-panel">
                        <button class="control-btn" id="mute-btn" title="Mute/Unmute">
                            <svg viewBox="0 0 24 24" id="vol-high-icon"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
                            <svg viewBox="0 0 24 24" id="vol-mute-icon" style="display: none;"><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.21.05-.42.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/></svg>
                        </button>
                        <div class="volume-slider-wrapper">
                            <input type="range" class="volume-slider" id="volume-range" min="0" max="1" step="0.05" value="1">
                        </div>
                    </div>

                    <button class="control-btn" id="fullscreen-btn" title="Toggle Fullscreen">
                        <svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.8/dist/hls.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", () => {
            const container = document.getElementById('player-container');
            const video = document.getElementById('video-engine');
            const loader = document.getElementById('video-loader');
            
            // Custom UI Elements Map
            const playPauseBtn = document.getElementById('play-pause-btn');
            const playIcon = document.getElementById('play-icon');
            const pauseIcon = document.getElementById('pause-icon');
            const currentTimeStr = document.getElementById('current-time-string');
            const durationTimeStr = document.getElementById('duration-time-string');
            const timelineBox = document.getElementById('timeline-box');
            const progressLine = document.getElementById('progress-line');
            const muteBtn = document.getElementById('mute-btn');
            const volHighIcon = document.getElementById('vol-high-icon');
            const volMuteIcon = document.getElementById('vol-mute-icon');
            const volumeRange = document.getElementById('volume-range');
            const fullscreenBtn = document.getElementById('fullscreen-btn');

            /* ==========================================================================
               STREAM PROTOCOL CAPTURE ENGINE (HLS CONFIG)
               ========================================================================== */
            const manifestUrl = video.querySelector('source').src;
            
            if (Hls.isSupported() && manifestUrl.includes('manifest')) {
                const hls = new Hls({ maxBufferLength: 45 });
                hls.loadSource(manifestUrl);
                hls.attachMedia(video);
            } else if (video.canPlayType('application/x-mpegURL')) {
                // Native Safari fallback initialization configuration array
                video.src = manifestUrl;
            }

            // Remove loading matrix shroud shield as soon as media frame data matches pipeline pipeline
            video.addEventListener('canplay', () => {
                if(loader) {
                    loader.style.opacity = '0';
                    setTimeout(() => loader.remove(), 400);
                }
            });

            /* ==========================================================================
               CORE CORE INTERACTIVE FUNCTIONALITY MATRIX
               ========================================================================== */
            
            // Play/Pause Action Switches
            function togglePlay() {
                if (video.paused) {
                    video.play().catch(() => {
                        video.muted = true;
                        video.play();
                    });
                } else {
                    video.pause();
                }
            }

            video.addEventListener('click', togglePlay);
            playPauseBtn.addEventListener('click', togglePlay);

            video.addEventListener('play', () => {
                playIcon.style.display = 'none';
                pauseIcon.style.display = 'block';
            });

            video.addEventListener('pause', () => {
                playIcon.style.display = 'block';
                pauseIcon.style.display = 'none';
            });

            // Clean Time Value Conversions Tool
            function formatTimeCode(seconds) {
                if (isNaN(seconds)) return "0:00";
                const mins = Math.floor(seconds / 60);
                const secs = Math.floor(seconds % 60);
                return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
            }

            // Update Time Indicators and Timeline Line Progress Percentage Maps
            video.addEventListener('timeupdate', () => {
                currentTimeStr.textContent = formatTimeCode(video.currentTime);
                const progressPct = (video.currentTime / video.duration) * 100;
                progressLine.style.width = `${progressPct}%`;
            });

            video.addEventListener('loadedmetadata', () => {
                durationTimeStr.textContent = formatTimeCode(video.duration);
            });

            // Seek functionality through timeline track coordinates
            timelineBox.addEventListener('click', (e) => {
                const rect = timelineBox.getBoundingClientRect();
                const clickPosition = (e.clientX - rect.left) / rect.width;
                video.currentTime = clickPosition * video.duration;
            });

            // Volume Modulating Controls API
            volumeRange.addEventListener('input', (e) => {
                video.volume = e.target.value;
                video.muted = (e.target.value == 0);
                updateVolumeAppearance();
            });

            muteBtn.addEventListener('click', () => {
                video.muted = !video.muted;
                updateVolumeAppearance();
            });

            function updateVolumeAppearance() {
                if (video.muted || video.volume === 0) {
                    volHighIcon.style.display = 'none';
                    volMuteIcon.style.display = 'block';
                    volumeRange.value = 0;
                } else {
                    volHighIcon.style.display = 'block';
                    volMuteIcon.style.display = 'none';
                    volumeRange.value = video.volume;
                }
            }

            // High-Performance Fullscreen toggle module sequence array execution platform
            fullscreenBtn.addEventListener('click', () => {
                if (!document.fullscreenElement) {
                    container.requestFullscreen().catch(err => console.log(err));
                } else {
                    document.exitFullscreen();
                }
            });

            /* ==========================================================================
               SEAMLESS CONTROL PANEL AUTO-HIDING SYSTEM
               ========================================================================== */
            let activeTimer;
            function displayControlsTemporarily() {
                container.classList.remove('user-inactive');
                clearTimeout(activeTimer);
                if (!video.paused) {
                    activeTimer = setTimeout(() => {
                        container.classList.add('user-inactive');
                    }, 2500); // UI bar floats away cleanly after 2.5 seconds of immobility
                }
            }

            container.addEventListener('mousemove', displayControlsTemporarily);
            video.addEventListener('play', displayControlsTemporarily);
            video.addEventListener('pause', () => container.classList.remove('user-inactive'));
        });
    </script>
</body>
</html>
"""

import time  # Make sure to add this at the top of your starter.py file!

@app.route('/download', methods=['POST', 'GET'])
def render_player():
    user_input = request.form.get('id_or_url', '').strip() if request.method == 'POST' else request.args.get('id_or_url', '').strip()

    if not user_input:
        return "Missing 'id_or_url' parameter.", 400

    if "dailymotion.com" in user_input:
        target_url = user_input if user_input.startswith(("http://", "https://")) else f"https://{user_input}"
    else:
        target_url = f"https://www.dailymotion.com/video/{user_input}"

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'impersonate': ImpersonateTarget.from_str('chrome')
    }

    info = None
    m3u8_url = None

    # First Attempt
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            formats = info.get('formats', [])
            hls_streams = [f for f in formats if 'hls' in f.get('format_id', '') and f.get('url')]
            m3u8_url = hls_streams[-1].get('url') if hls_streams else (info.get('url') or formats[-1].get('url'))
    except Exception as first_error:
        print(f"First attempt failed: {first_error}. Retrying in 1 second...")
        time.sleep(1)  # Cool-down pause to clear temporary rate limits
        
        # Second Attempt (The Retry)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                formats = info.get('formats', [])
                hls_streams = [f for f in formats if 'hls' in f.get('format_id', '') and f.get('url')]
                m3u8_url = hls_streams[-1].get('url') if hls_streams else (info.get('url') or formats[-1].get('url'))
        except Exception as second_error:
            # Absolute Backup Fallback: Build the direct CDN link manually so it STILL plays
            print(f"Retry failed too: {second_error}. Using fallback template link.")
            video_id = user_input.split("/video/")[-1].split("?")[0] if "/video/" in user_input else user_input
            m3u8_url = f"https://www.dailymotion.com/cdn/manifest/video/{video_id}.m3u8"
            
            # Create a mock info dict so the page doesn't crash on title rendering
            info = {'title': 'Dailymotion Stream (Fallback Mode)'}

    # Final validation safety check
    if not m3u8_url:
        return "Failed to find manifest endpoint maps.", 500

    return render_template_string(
        PLAYER_TEMPLATE, 
        title=info.get('title', 'Dailymotion Stream') if info else 'Dailymotion Stream',
        target_url=m3u8_url
    )


@app.route('/manifest')
def proxy_m3u8():
    raw_m3u8_url = request.args.get('url')
    if not raw_m3u8_url:
        return "Missing target reference", 400

    raw_m3u8_url = urllib.parse.unquote(raw_m3u8_url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    resp = requests.get(raw_m3u8_url, headers=headers)

    base_url = raw_m3u8_url.rsplit('/', 1)[0] + '/'
    rewritten_lines = []

    for line in resp.text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # CRITICAL FIXED PIECE: Capture separate audio manifests hiding in attributes like:
        # #EXT-X-MEDIA:TYPE=AUDIO,...,URI="https://..."
        if 'URI=' in line_stripped:
            def replace_uri(match):
                rel_path = match.group(1).strip('"\'')
                abs_url = urllib.parse.urljoin(base_url, rel_path)
                proxy_route = "/manifest" if (".m3u8" in rel_path or "manifest" in rel_path) else "/segment"
                return f'URI="{proxy_route}?url={urllib.parse.quote_plus(abs_url)}"'

            line_stripped = re.sub(r'URI=(["\'].*?["\'])', replace_uri, line_stripped)
            rewritten_lines.append(line_stripped)

        elif not line_stripped.startswith('#'):
            if not line_stripped.startswith(('http://', 'https://')):
                full_url = urllib.parse.urljoin(base_url, line_stripped)
            else:
                full_url = line_stripped

            encoded_url = urllib.parse.quote_plus(full_url)

            if '.m3u8' in line_stripped or 'manifest' in line_stripped:
                rewritten_lines.append(f"/manifest?url={encoded_url}")
            else:
                rewritten_lines.append(f"/segment?url={encoded_url}")
        else:
            rewritten_lines.append(line_stripped)

    return Response("\n".join(rewritten_lines), content_type="application/x-mpegURL")


@app.route('/segment')
def proxy_ts_segment():
    raw_ts_url = request.args.get('url')
    if not raw_ts_url:
        return "Missing segment path", 400

    raw_ts_url = urllib.parse.unquote(raw_ts_url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    req = requests.get(raw_ts_url, headers=headers, stream=True)

    def stream_ts_data():
        for block in req.iter_content(chunk_size=1024 * 64):
            yield block

    content_type = req.headers.get('Content-Type', 'video/MP2T')
    return Response(stream_ts_data(), content_type=content_type)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
