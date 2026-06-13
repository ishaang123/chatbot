import os
import re
import sys
import threading
import time
import urllib.parse
import requests
from flask import Flask, request, Response, render_template_string 
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

app = Flask(__name__)

# Highly optimized connection pool for immediate data passthrough
http_pool = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=500,       # Bumped for high-concurrency scrubbing/seeking
    pool_maxsize=500, 
    pool_block=False
)
http_pool.mount('http://', adapter)
http_pool.mount('https://', adapter)

INTERNAL_INFRASTRUCTURE_HOST = "cggames.pythonanywhere.com"

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NebulaView Core</title>
    <style>
        body {
            background: radial-gradient(circle at center, #0c0a0f 0%, #050506 100%);
            color: #f4f4f5;
            font-family: sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
    </style>
</head>
<body>
    <h1>NebulaView Mobile Active</h1>
</body>
</html>
"""

PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>{{ title }}</title>
    <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
    <style>
        :root {
            --accent-primary: #ff0000;
            --bg-base: #0f0f0f;
            --text-primary: #f1f1f1;
            --text-secondary: #aaaaaa;
            --gradient-top: linear-gradient(to bottom, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
        }

        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: "Roboto", Arial, sans-serif;
            overflow: hidden;
            user-select: none;
        }

        .viewport-player-hero {
            position: absolute;
            top: 0;
            left: 0;
            width: 100vw !important;
            height: 100vh !important;
            max-width: 100vw !important;
            max-height: 100vh !important;
            background-color: #000;
            z-index: 1;
            overflow: hidden;
        }

        .video-js {
            width: 100% !important;
            height: 100% !important;
            background-color: #000 !important;
        }

        .vjs-poster {
            background-size: contain !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-color: #000 !important;
        }

        .video-js video { 
            object-fit: contain !important; 
            width: 100% !important;
            height: 100% !important;
        }

        .embed-floating-header {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            padding: 24px 24px 48px 24px;
            background: var(--gradient-top);
            z-index: 10;
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            box-sizing: border-box;
            pointer-events: none;
            opacity: 1;
            transition: opacity 0.25s ease;
        }

        .video-js.vjs-user-inactive ~ #embed-header { 
            opacity: 0; 
            pointer-events: none;
        }
        .video-js.vjs-user-active ~ #embed-header,
        .video-js.vjs-paused ~ #embed-header { 
            opacity: 1; 
            pointer-events: auto;
        }

        .embed-header-left { display: flex; align-items: center; gap: 12px; pointer-events: auto; min-width: 0; flex: 1; }

        .embed-channel-icon-container {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            background: #272727;
            font-weight: 700;
            color: #fff;
        }
        .embed-channel-icon-container img { width: 100%; height: 100%; object-fit: cover; }

        .embed-meta-text { display: flex; flex-direction: column; min-width: 0; }
        .embed-video-title { color: var(--text-primary); font-size: 1.1rem; font-weight: 500; margin: 0; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; text-shadow: 0 1px 3px rgba(0,0,0,0.9); }
        .embed-channel-name { color: var(--text-secondary); font-size: 0.85rem; margin-top: 2px; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; }
         
        .embed-header-actions {
            display: flex;
            align-items: center;
            gap: 16px;
            pointer-events: auto;
            flex-shrink: 0;
        }

        /* 🌌 NEBULAVIEW BRANDING STYLES */
        .nebulaview-branding-tag {
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(15, 15, 15, 0.65);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            padding: 6px 12px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            font-weight: 700;
            font-size: 0.85rem;
            letter-spacing: 0.8px;
            color: #ffffff;
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .nebulaview-branding-tag span {
            color: var(--accent-primary);
        }

        .embed-icon-btn {
            background: transparent; border: none; color: var(--text-primary); cursor: pointer; padding: 8px;
            filter: drop-shadow(0px 1px 3px rgba(0,0,0,0.9)); display: flex; align-items: center; justify-content: center;
        }

        .player-endscreen-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.92);
            z-index: 12; 
            display: none; 
            flex-direction: column;
            justify-content: center;
            align-items: center;
            box-sizing: border-box;
            padding: 32px 24px;
        }

        .endscreen-title {
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 20px;
            align-self: flex-start;
            width: 100%;
            max-width: 720px;
            margin-left: auto;
            margin-right: auto;
            letter-spacing: 0.5px;
        }

        .endscreen-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            width: 100%;
            max-width: 720px;
            overflow-y: auto;
        }

        @media (max-width: 560px) {
            .endscreen-grid { grid-template-columns: 1fr; gap: 14px; }
            .endscreen-title { font-size: 1.1rem; margin-bottom: 14px; }
            .nebulaview-branding-tag { padding: 5px 10px; font-size: 0.75rem; }
        }

        .endscreen-card {
            display: flex;
            gap: 14px;
            background: rgba(255, 255, 255, 0.04);
            padding: 10px;
            border-radius: 12px;
            text-decoration: none;
            color: inherit;
            align-items: center;
            border: 1px solid rgba(255,255,255,0.02);
            transition: background 0.2s ease, transform 0.2s ease;
        }
        .endscreen-card:hover { 
            background: rgba(255, 255, 255, 0.12);
            transform: translateY(-2px);
        }

        .endscreen-thumb-container {
            position: relative;
            width: 130px;
            height: 74px;
            flex-shrink: 0;
            border-radius: 6px;
            overflow: hidden;
            background: #111;
        }
        .endscreen-thumb-container img { width: 100%; height: 100%; object-fit: cover; }

        .endscreen-duration {
            position: absolute; bottom: 4px; right: 4px; background: rgba(0,0,0,0.85);
            color: #fff; padding: 2px 4px; border-radius: 3px; font-size: 0.68rem; font-weight: 600;
        }

        .endscreen-meta { display: flex; flex-direction: column; min-width: 0; }
        .endscreen-v-title {
            font-size: 0.88rem; font-weight: 500; line-height: 1.35; color: var(--text-primary);
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 4px;
        }
        .endscreen-v-creator { font-size: 0.78rem; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        .video-js .vjs-big-play-button {
            background-color: rgba(20, 20, 20, 0.85) !important; border: none !important; border-radius: 12px !important;
            width: 68px !important; height: 48px !important; line-height: 48px !important; margin-top: -24px !important; margin-left: -34px !important; z-index: 11;
        }
        .video-js:hover .vjs-big-play-button { background-color: var(--accent-primary) !important; }
        .video-js .vjs-control-bar { display: flex !important; background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0) 100%) !important; height: 48px !important; z-index: 11; }
        .video-js .vjs-progress-control { position: absolute !important; width: calc(100% - 24px) !important; height: 6px !important; top: -6px !important; left: 12px !important; display: flex !important; visibility: visible !important;}
        .video-js .vjs-play-progress { background: var(--accent-primary) !important; }
        .video-js .vjs-slider { background-color: rgba(255,255,255,0.2) !important; }
        
        .video-js .vjs-fullscreen-control { display: none !important; }
        
        .vjs-download-control, .vjs-custom-fullscreen-control { cursor: pointer; display: flex; align-items: center; justify-content: center; width: 40px; height: 100%; order: 99; }
        .vjs-download-control svg, .vjs-custom-fullscreen-control svg { width: 18px; height: 18px; fill: var(--text-primary); opacity: 0.8; }
        .vjs-download-control svg:hover, .vjs-custom-fullscreen-control svg:hover { opacity: 1; }

        .video-js .vjs-loading-spinner {
            border: 3px solid rgba(255, 255, 255, 0.1) !important;
            border-top: 3px solid var(--accent-primary) !important;
            border-radius: 50% !important;
            width: 50px !important;
            height: 50px !important;
            margin: -25px 0 0 -25px !important;
            animation: vjs-spinner-spin 0.8s linear infinite !important;
            background: none !important;
        }
        .video-js .vjs-loading-spinner:before, 
        .video-js .vjs-loading-spinner:after {
            display: none !important;
        }
        @keyframes vjs-spinner-spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .nebula-interstitial-loader {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: var(--bg-base);
            z-index: 99999; 
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 20px;
        }

        .loader-ring {
            width: 54px;
            height: 54px;
            border: 4px solid rgba(255, 255, 255, 0.08);
            border-top: 4px solid var(--accent-primary);
            border-radius: 50%;
            animation: vjs-spinner-spin 0.7s cubic-bezier(0.4, 0, 0.2, 1) infinite;
        }

        .loader-text {
            color: var(--text-primary);
            font-size: 0.95rem;
            font-weight: 500;
            letter-spacing: 0.5px;
            opacity: 0.85;
        }

        /* 👤 ANIMATED CREATOR VIDEOS MODAL STYLES */
        .creator-modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(5, 5, 6, 0.96);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            z-index: 100000; 
            display: none;
            justify-content: center;
            align-items: center;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .creator-modal-overlay.active {
            display: flex;
            opacity: 1;
        }

        .creator-modal-content {
            background: #121214;
            border: 1px solid rgba(255, 255, 255, 0.08);
            width: 90%;
            max-width: 760px;
            height: 75vh;
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transform: scale(0.92);
            transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        .creator-modal-overlay.active .creator-modal-content {
            transform: scale(1);
        }

        .creator-modal-header {
            padding: 20px 24px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .creator-modal-profile {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .creator-modal-avatar {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            overflow: hidden;
            background: #272727;
        }

        .creator-modal-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .creator-modal-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin: 0;
        }

        .creator-modal-subtitle {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        .creator-close-btn {
            background: rgba(255, 255, 255, 0.05);
            border: none;
            color: #fff;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }

        .creator-close-btn:hover {
            background: rgba(255, 255, 255, 0.15);
        }

        .creator-video-body {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
        }

        .creator-video-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
        }

        @media (max-width: 560px) {
            .creator-video-grid { grid-template-columns: 1fr; gap: 12px; }
            .creator-modal-content { height: 85vh; width: 95%; }
            .creator-video-body { padding: 16px; }
        }
    </style>
</head>
<body>

    <div class="nebula-interstitial-loader" id="page-interstitial-screen">
        <div class="loader-ring"></div>
        <div class="loader-text">Extracting High Priority Stream...</div>
    </div>

    <div class="viewport-player-hero" id="player-view-wrapper">
        
        <video id="my-video" class="video-js vjs-default-skin vjs-big-play-centered" controls playsinline webkit-playsinline></video>

        <div class="embed-floating-header" id="embed-header">
            <div class="embed-header-left" id="creator-hud-trigger" style="cursor: pointer; pointer-events: auto;">
                <div class="embed-channel-icon-container" id="avatar-container-hud"></div>
                <div class="embed-meta-text">
                    <span class="embed-video-title">{{ title }}</span>
                    <span class="embed-channel-name">{{ author_name if author_name else "Verified Creator" }}</span>
                </div>
            </div>
            
            <div class="embed-header-actions">
                <div class="nebulaview-branding-tag">
                    Nebula<span>View</span>
                </div>
                <button class="embed-icon-btn" id="embed-share-btn">
                    <svg style="width:22px;height:22px;fill:currentColor" viewBox="0 0 24 24"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.8 2.04.8 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg>
                </button>
            </div>
        </div>

        <div class="player-endscreen-overlay" id="endscreen-display">
            <div class="endscreen-title">Up Next</div>
            <div class="endscreen-grid" id="endscreen-grid-items"></div>
        </div>
        
    </div>

    <div class="creator-modal-overlay" id="creator-profile-modal">
        <div class="creator-modal-content">
            <div class="creator-modal-header">
                <div class="creator-modal-profile">
                    <div class="creator-modal-avatar" id="modal-avatar-slot"></div>
                    <div>
                        <h3 class="creator-modal-title" id="modal-creator-title">Creator Profile</h3>
                        <div class="creator-modal-subtitle">More uploads from this station</div>
                    </div>
                </div>
                <button class="creator-close-btn" id="modal-close-trigger">
                    <svg style="width:20px;height:20px;fill:currentColor" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                </button>
            </div>
            <div class="creator-video-body">
                <div class="creator-video-grid" id="modal-grid-items">
                    <div style="color:var(--text-secondary);grid-column:1/-1;text-align:center;padding:20px;">Gathering content data index metadata...</div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://vjs.zencdn.net/8.10.0/video.js"></script>
    <script>
        const targetVideoId = "{{ current_video_id }}";
        let player;

        if ('mediaSession' in navigator) {
            navigator.mediaSession.metadata = new MediaMetadata({
                title: "{{ title }}",
                artist: "{{ author_name if author_name else 'Verified Creator' }}",
                artwork: [{ src: "{{ forced_poster }}", sizes: '512x512', type: 'image/jpeg' }]
            });
        }

        function resolveMediaAssets() {
            let posterUrl = "{{ forced_poster }}".trim();
            if (!posterUrl || posterUrl === "None" || posterUrl === "") {
                posterUrl = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1920";
            }
            document.getElementById('my-video').setAttribute('poster', posterUrl);

            const creatorName = "{{ author_name }}".trim() || "Verified Creator";
            const passedAvatar = "{{ author_avatar_url }}".trim();
            const hudIconContainer = document.getElementById('avatar-container-hud');

            if (passedAvatar && passedAvatar !== "None" && passedAvatar !== "") {
                hudIconContainer.innerHTML = `<img src="${passedAvatar}">`;
            } else {
                const firstLetter = creatorName.charAt(0).toUpperCase();
                const colors = ['#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3'];
                hudIconContainer.style.backgroundColor = colors[firstLetter.charCodeAt(0) % colors.length];
                hudIconContainer.textContent = firstLetter;
            }
        }

        async function runLazyEndscreenGeneration() {
            if(!targetVideoId) return;
            try {
                const response = await fetch(`https://api.dailymotion.com/video/${targetVideoId}/related?fields=id,title,owner,thumbnail_240_url,duration&limit=4`);
                const data = await response.json();
                if(data && data.list) {
                    const gridContainer = document.getElementById('endscreen-grid-items');
                    gridContainer.innerHTML = '';
                    
                    data.list.forEach(item => {
                        const mins = Math.floor(item.duration / 60);
                        const secs = String(item.duration % 60).padStart(2, '0');
                        
                        const uploaderUsername = (item.owner && item.owner.username) ? item.owner.username : 'Creator';
                        
                        const element = document.createElement('a');
                        element.className = 'endscreen-card';
                        element.href = `/download?id_or_url=${item.id}`;
                        element.innerHTML = `
                            <div class="endscreen-thumb-container">
                                <img src="${item.thumbnail_240_url}">
                                <div class="endscreen-duration">${mins}:${secs}</div>
                            </div>
                            <div class="endscreen-meta">
                                <div class="endscreen-v-title">${item.title}</div>
                                <div class="endscreen-v-creator">${uploaderUsername}</div>
                            </div>
                        `;

                        element.addEventListener('click', function() {
                            document.getElementById('page-interstitial-screen').style.display = 'flex';
                        });

                        gridContainer.appendChild(element);
                    });
                    
                    document.getElementById('endscreen-display').style.display = 'flex';
                }
            } catch(e) {
                console.error("Delayed endscreen engine exception:", e);
            }
        }

        document.addEventListener("DOMContentLoaded", function() {
            resolveMediaAssets();
            player = videojs('my-video', {
                preload: 'auto', 
                autoplay: false, 
                controls: true,
                fluid: false, 
                playsinline: true, 
                webkitPlaysinline: true,
                preferFullWindow: false, 
                
                html5: {
                    vhs: {
                        maxBufferLength: 12,
                        forwardBufferLength: 6,
                        backBufferLength: 0
                    }
                },
                controlBar: {
                    progressControl: { enableTouchPoints: true }
                }
            });

            player.src({
                src: "/manifest?url={{ stream_url | urlencode }}&priority={{ priority }}",
                type: 'application/x-mpegURL',
                exact_seeking: true 
            });

            player.on('ended', function() {
                runLazyEndscreenGeneration();
            });

            player.on('play', function() {
                document.getElementById('endscreen-display').style.display = 'none';
            });

            player.ready(function() {
                const controlBar = player.getChild('controlBar');

                // 1. DOWNLOAD INTERACTION BUTTON
                const downloadBtn = document.createElement('div');
                downloadBtn.className = 'vjs-download-control vjs-control vjs-button';
                downloadBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M5 20h14v-2H5v2zM19 9h-4V3H9v6H5l7 7 7-7z"/></svg>`;
                
                const currentSrc = player.src();
                const urlParams = new URLSearchParams(currentSrc.split('?')[1]);
                const targetM3u8Url = urlParams.get('url');
                const decodedUrl = targetM3u8Url ? decodeURIComponent(targetM3u8Url) : currentSrc;
                downloadBtn.addEventListener('click', function() { window.open(decodedUrl, '_blank'); });
                controlBar.el().appendChild(downloadBtn);

                // 2. UNRESTRICTED DIRECT HARDWARE MOBILE FULLSCREEN BYPASS
                const fsBtn = document.createElement('div');
                fsBtn.className = 'vjs-custom-fullscreen-control vjs-control vjs-button';
                fsBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>`;
                
                fsBtn.addEventListener('click', function() {
                    const videoEl = document.getElementById('my-video_html5_api') || player.tech({ IWillNotUseThisInPlugins: true }).el();

                    if (videoEl) {
                        if (videoEl.webkitEnterFullscreen) {
                            videoEl.webkitEnterFullscreen();
                        } 
                        else if (videoEl.requestFullscreen) {
                            videoEl.requestFullscreen();
                        } else if (videoEl.msRequestFullscreen) {
                            videoEl.msRequestFullscreen();
                        } else if (videoEl.mozRequestFullScreen) {
                            videoEl.mozRequestFullScreen();
                        } else {
                            player.requestFullscreen();
                        }

                        if (screen.orientation && screen.orientation.lock) {
                            screen.orientation.lock('landscape').catch(() => {});
                        }
                    }
                });
                controlBar.el().appendChild(fsBtn);
            });
            document.getElementById('embed-share-btn').addEventListener('click', function() {
    // Fallback to current URL if the player isn't loaded inside an iframe
    const shareUrl = document.referrer || window.location.href;

    if (navigator.share) {
        navigator.share({ 
            title: document.title, 
            url: shareUrl 
        }).catch(console.error);
    } else {
        navigator.clipboard.writeText(shareUrl);
        alert("Link copied to clipboard memory.");
    }
});

            // --- 👤 CREATOR POPUP CONTROLLER LOGIC ENGINE ---
            const creatorTrigger = document.getElementById('creator-hud-trigger');
            const modalOverlay = document.getElementById('creator-profile-modal');
            const modalClose = document.getElementById('modal-close-trigger');
            let hasLoadedCreatorVideos = false;

            async function presentCreatorModal() {
                if (player && !player.paused()) {
                    player.pause();
                }

                modalOverlay.style.display = 'flex';
                setTimeout(() => modalOverlay.classList.add('active'), 10);

                if (hasLoadedCreatorVideos) return; 

                try {
                    if(!targetVideoId) return;

                    const contextRes = await fetch(`https://api.dailymotion.com/video/${targetVideoId}?fields=owner,owner.screenname,owner.avatar_120_url`);
                    const contextData = await contextRes.json();
                    
                    if (contextData && contextData.owner) {
                        const ownerId = contextData.owner;
                        const screenName = contextData['owner.screenname'] || "Verified Creator";
                        const avatarUrl = contextData['owner.avatar_120_url'] || "";

                        document.getElementById('modal-creator-title').textContent = screenName;
                        const modalAvatarSlot = document.getElementById('modal-avatar-slot');
                        
                        if (avatarUrl) {
                            modalAvatarSlot.innerHTML = `<img src="${avatarUrl}">`;
                        } else {
                            const initial = screenName.charAt(0).toUpperCase();
                            modalAvatarSlot.innerHTML = `<div style="width:100%;height:100%;background:#ff0000;display:flex;align-items:center;justify-content:center;font-weight:bold;color:#fff">${initial}</div>`;
                        }

                        const listRes = await fetch(`https://api.dailymotion.com/user/${ownerId}/videos?fields=id,title,thumbnail_240_url,duration&limit=6`);
                        const listData = await listRes.json();

                        if (listData && listData.list) {
                            const gridContainer = document.getElementById('modal-grid-items');
                            gridContainer.innerHTML = '';

                            listData.list.forEach(item => {
                                const mins = Math.floor(item.duration / 60);
                                const secs = String(item.duration % 60).padStart(2, '0');

                                const element = document.createElement('a');
                                element.className = 'endscreen-card';
                                element.href = `/download?id_or_url=${item.id}`;
                                element.innerHTML = `
                                    <div class="endscreen-thumb-container">
                                        <img src="${item.thumbnail_240_url}">
                                        <div class="endscreen-duration">${mins}:${secs}</div>
                                    </div>
                                    <div class="endscreen-meta">
                                        <div class="endscreen-v-title">${item.title}</div>
                                        <div class="endscreen-v-creator">${screenName}</div>
                                    </div>
                                `;

                                element.addEventListener('click', function() {
                                    document.getElementById('page-interstitial-screen').style.display = 'flex';
                                });

                                gridContainer.appendChild(element);
                            });
                            hasLoadedCreatorVideos = true;
                        }
                    }
                } catch (err) {
                    console.error("Popup engine request lifecycle exception:", err);
                    document.getElementById('modal-grid-items').innerHTML = '<div style="color:var(--text-secondary);grid-column:1/-1;text-align:center;padding:20px;">Could not fetch profile channel records.</div>';
                }
            }

            function dismissCreatorModal() {
                modalOverlay.classList.remove('active');
                setTimeout(() => {
                    modalOverlay.style.display = 'none';
                }, 300);
            }

            creatorTrigger.addEventListener('click', presentCreatorModal);
            modalClose.addEventListener('click', dismissCreatorModal);
            modalOverlay.addEventListener('click', function(e) {
                if (e.target === modalOverlay) dismissCreatorModal();
            });
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(INDEX_TEMPLATE)

@app.route('/download', methods=['POST', 'GET'])
def render_player():
    user_input = request.form.get('id_or_url', '').strip() if request.method == 'POST' else request.args.get('id_or_url', '').strip()

    if not user_input:
        return "Missing identity context parameter.", 400

    referer = request.headers.get("Referer", "")
    priority_flag = "high" if INTERNAL_INFRASTRUCTURE_HOST in referer else "standard"

    video_id_match = re.search(r'(?:dailymotion\.com\/video\/|dai\.ly\/)([a-zA-Z0-9]+)', user_input)
    clean_video_id = video_id_match.group(1) if video_id_match else user_input

    if "dailymotion.com" in user_input or "dai.ly" in user_input:
        target_url = user_input if user_input.startswith(("http://", "https://")) else f"https://{user_input}"
    else:
        target_url = f"https://www.dailymotion.com/video/{clean_video_id}"

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best', 
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,              
        'check_formats': 'cached',          
        'extract_flat': False,
        'socket_timeout': 10,  
        'nocheckcertificate': True,
        'geo_bypass': True,  
        'http_headers': {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if not info:
                return "Extraction failed.", 500
                
            formats = info.get('formats', [])
            
            hls_streams = [f for f in formats if 'm3u8' in str(f.get('url','')) or 'hls' in str(f.get('format_id','')).lower()]
            
            if hls_streams:
                m3u8_url = hls_streams[-1].get('url')
            else:
                m3u8_url = info.get('url') or (formats[-1].get('url') if formats else None)

            if not m3u8_url:
                return "No playable stream paths found.", 404

            video_thumbnail = info.get('thumbnail') or (info.get('thumbnails') and info.get('thumbnails')[-1].get('url')) or ""
            creator_name = info.get('uploader') or info.get('channel') or "Verified Creator"
            creator_avatar = info.get('uploader_url') or "" 
            
            return render_template_string(
                PLAYER_TEMPLATE, 
                title=info.get('title', 'Native Stream Source'),
                current_video_id=clean_video_id,
                target_url=target_url, 
                stream_url=m3u8_url,   
                priority=priority_flag,
                author_name=creator_name,
                author_avatar_url=creator_avatar,
                forced_poster=video_thumbnail 
            )
            
    except Exception as error:
        return f"Extraction Pipeline Exception Error: {str(error)}", 500

@app.route('/manifest')
def proxy_m3u8():
    raw_m3u8_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_m3u8_url:
        return "Missing proxy targets", 400

    raw_m3u8_url = urllib.parse.unquote(raw_m3u8_url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
        'Accept': '*/*',
    }
    
    try:
        resp = http_pool.get(raw_m3u8_url, headers=headers, timeout=5)
    except Exception:
        return "Timeout during proxy resolution", 504

    base_url = raw_m3u8_url.rsplit('/', 1)[0] + '/'
    rewritten_lines = []

    for line in resp.text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if 'URI=' in line_stripped:
            def replace_uri(match):
                rel_path = match.group(1).strip('"\'')
                abs_url = urllib.parse.urljoin(base_url, rel_path)
                proxy_route = "/manifest" if (".m3u8" in rel_path or "manifest" in rel_path) else "/segment"
                return f'URI="{proxy_route}?url={urllib.parse.quote_plus(abs_url)}&priority={priority}"'
            line_stripped = re.sub(r'URI=(["\'].*?["\'])', replace_uri, line_stripped)
            rewritten_lines.append(line_stripped)

        elif not line_stripped.startswith('#'):
            full_url = line_stripped if line_stripped.startswith(('http://', 'https://')) else urllib.parse.urljoin(base_url, line_stripped)
            encoded_url = urllib.parse.quote_plus(full_url)
            if '.m3u8' in line_stripped or 'manifest' in line_stripped:
                rewritten_lines.append(f"/manifest?url={encoded_url}&priority={priority}")
            else:
                rewritten_lines.append(f"/segment?url={encoded_url}&priority={priority}")
        else:
            rewritten_lines.append(line_stripped)

    response = Response("\n".join(rewritten_lines), content_type="application/vnd.apple.mpegurl")
    response.headers["Cache-Control"] = "public, max-age=2"
    return response

@app.route('/segment')
def proxy_ts_segment():
    raw_ts_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_ts_url:
        return "Missing segment sequence indices", 400

    raw_ts_url = urllib.parse.unquote(raw_ts_url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }
    timeout_val = 5 if priority == "high" else 7
    
    try:
        req = http_pool.get(raw_ts_url, headers=headers, stream=True, timeout=timeout_val)
        
        content_type = req.headers.get('Content-Type')
        if not content_type or content_type == 'text/plain':
            if '.mp4' in raw_ts_url or '/fmp4/' in raw_ts_url:
                content_type = 'video/mp4'
            else:
                content_type = 'video/MP2T'
        
        content_length = req.headers.get('Content-Length')

        def stream_ts_data():
            for block in req.iter_content(chunk_size=1024 * 16):
                if block:
                    yield block

        response = Response(stream_ts_data(), content_type=content_type)
        if content_length:
            response.headers['Content-Length'] = content_length
            
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
    except Exception:
        return "Segment connection dropped", 502

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
