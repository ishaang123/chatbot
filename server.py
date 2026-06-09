import os
import re
import sys
import subprocess
import threading
import time
import urllib.parse
import requests
from flask import Flask, request, Response, render_template_string
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

# Global lock to prevent multiple update processes from running at the exact same time
update_lock = threading.Lock()

def run_pip_update():
    """Helper function to execute the pip upgrade safely within a lock."""
    if update_lock.locked():
        print("[Engine Lifecycle] Update already in progress, skipping duplicate request.")
        return
        
    with update_lock:
        try:
            print("[Engine Lifecycle] Running extraction framework update check...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("[Engine Lifecycle] Engine package update routine completed successfully.")
        except Exception as e:
            print(f"[Engine Lifecycle] Upgrade execution deferred: {e}")

# --- CONTINUOUS BACKGROUND UPDATE LOOP ---
def upgrade_extractor_engine_loop():
    """Runs continuously. Checks and updates yt-dlp on startup, then every 2 hours."""
    time.sleep(5)  # Short pause to let Flask bind its ports smoothly
    while True:
        run_pip_update()
        time.sleep(7200)  # Sleep for 2 hours (7200 seconds)

# Start the continuous 2-hour background loop thread
threading.Thread(target=upgrade_extractor_engine_loop, daemon=True).start()


app = Flask(__name__)

# Streamlined persistent network pool for proxy operations
http_pool = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=200, pool_maxsize=200, pool_block=False)
http_pool.mount('http://', adapter)
http_pool.mount('https://', adapter)

INTERNAL_INFRASTRUCTURE_HOST = "cggames.pythonanywhere.com"

# --- UI TEMPLATES ---

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NebulaView Core</title>
    <style>
        body {
            background: radial-gradient(circle at center, #0c0a0f 0%, #050506 100%);
            color: #f4f4f5;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            max-width: 420px;
            text-align: center;
            padding: 40px;
            background: rgba(10, 10, 12, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 24px;
            backdrop-filter: blur(40px);
            box-shadow: 0 30px 60px rgba(0, 0, 0, 0.8);
        }
        h1 {
            font-size: 2rem;
            margin: 0 0 12px 0;
            background: linear-gradient(135deg, #a855f7, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }
        p { color: #71717a; line-height: 1.6; font-size: 0.95rem; margin: 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NebulaView Mobile</h1>
        <p>Pure Native Extraction Engine Active.</p>
    </div>
</body>
</html>
"""
PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - NebulaView Premium</title>
    <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
    <style>
        /* --- CORE DESIGN SYSTEM --- */
        :root {
            --bg-base: #040406;
            --bg-surface: #0b0b0f;
            --bg-surface-elevated: #12121a;
            --accent-primary: #a855f7;
            --accent-secondary: #6366f1;
            --text-primary: #f4f4f5;
            --text-secondary: #a1a1aa;
            --text-muted: #71717a;
            --border-glow: rgba(168, 85, 247, 0.15);
            --border-subtle: rgba(255, 255, 255, 0.06);
            --sidebar-width: 400px;
            --header-height: 56px;
        }

        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            overflow-x: hidden;
        }

        /* Custom Scrollbar Styles */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-base); }
        ::-webkit-scrollbar-thumb { background: var(--bg-surface-elevated); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

        /* --- APPLICATION LAYOUT --- */
        .app-container {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            width: 100%;
        }

        /* Global Dynamic Header Navigation */
        .app-header {
            height: var(--header-height);
            background: rgba(11, 11, 15, 0.8);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            position: sticky;
            top: 0;
            z-index: 1000;
        }

        .header-left, .header-right { display: flex; align-items: center; gap: 16px; }
        
        .brand-logo {
            font-size: 1.25rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-decoration: none;
            letter-spacing: -0.5px;
        }

        .search-bar-container {
            flex: 0 1 600px;
            display: flex;
            background: var(--bg-surface-elevated);
            border: 1px solid var(--border-subtle);
            border-radius: 40px;
            padding: 4px 4px 4px 16px;
            transition: border-color 0.2s;
        }
        .search-bar-container:focus-within {
            border-color: var(--accent-primary);
            box-shadow: 0 0 10px var(--border-glow);
        }
        .search-input {
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-primary);
            width: 100%;
            font-size: 0.95rem;
        }
        .search-btn {
            background: rgba(255, 255, 255, 0.03);
            border: none;
            border-left: 1px solid var(--border-subtle);
            padding: 6px 20px;
            border-radius: 0 40px 40px 0;
            cursor: pointer;
            color: var(--text-secondary);
        }
        .search-btn:hover { color: var(--text-primary); background: rgba(255, 255, 255, 0.06); }

        .user-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: linear-gradient(135deg, #3b82f6, #ec4899);
            cursor: pointer;
        }

        /* --- THE STAGE (MAIN CONTENT GRID) --- */
        .stage-layout {
            display: grid;
            grid-template-columns: 1fr;
            max-width: 1750px;
            width: 100%;
            margin: 0 auto;
            padding: 24px;
            box-sizing: border-box;
            gap: 24px;
        }

        @media (min-width: 1200px) {
            .stage-layout {
                grid-template-columns: 1fr var(--sidebar-width);
            }
        }

        /* Primary Stream Column */
        .stream-column {
            display: flex;
            flex-direction: column;
            min-width: 0; /* Prevents flex items from breaking layout boundaries */
        }

        .video-player-canvas {
            position: relative;
            width: 100%;
            aspect-ratio: 16 / 9;
            background-color: #000;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.6);
            border: 1px solid var(--border-subtle);
        }

        .video-js {
            width: 100% !important;
            height: 100% !important;
        }

        /* Async Processing Matrix Loader Layer */
        #video-loader {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--bg-base);
            z-index: 999;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            transition: opacity 0.4s cubic-bezier(0.25, 1, 0.5, 1);
        }
        .spinner {
            box-sizing: border-box;
            width: 56px;
            height: 56px;
            border: 4px solid rgba(168, 85, 247, 0.08);
            border-top: 4px solid var(--accent-primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loader-text {
            margin-top: 20px;
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--text-secondary);
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        /* --- VIDEO INTERACTIVE INFRASTRUCTURE --- */
        .video-meta-card {
            margin-top: 16px;
            padding: 4px 0;
        }

        .video-title {
            font-size: 1.35rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.4;
            margin: 0 0 12px 0;
            word-wrap: break-word;
        }

        .interact-row {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-subtle);
        }

        .channel-profile-block {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .channel-logo {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: var(--bg-surface-elevated);
            border: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: var(--accent-primary);
        }
        .channel-name-meta { display: flex; flex-direction: column; }
        .channel-title { font-weight: 600; font-size: 1rem; color: var(--text-primary); }
        .channel-subs { font-size: 0.8rem; color: var(--text-secondary); }

        .action-button-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .action-btn {
            background: var(--bg-surface-elevated);
            border: 1px solid var(--border-subtle);
            color: var(--text-primary);
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.88rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: background 0.2s, transform 0.1s;
        }
        .action-btn:hover { background: rgba(255, 255, 255, 0.08); }
        .action-btn:active { transform: scale(0.98); }
        .action-btn.accented {
            background: var(--text-primary);
            color: var(--bg-base);
            border: none;
        }
        .action-btn.accented:hover { background: #e4e4e7; }

        /* Dynamic Description Panel Section */
        .description-expansion-panel {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 16px;
            margin-top: 16px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .description-expansion-panel:hover { background-color: var(--bg-surface-elevated); }
        .desc-metrics { font-weight: 700; font-size: 0.9rem; margin-bottom: 8px; display: flex; gap: 12px; }
        .desc-text-body { font-size: 0.92rem; line-height: 1.5; color: #e4e4e7; margin: 0; white-space: pre-wrap; }

        /* --- ENGAGEMENT AND COMMENTS SYSTEMS --- */
        .comments-module { margin-top: 24px; }
        .comments-header-row { font-size: 1.25rem; font-weight: 700; margin-bottom: 20px; display: flex; gap: 32px; }
        
        .comment-input-block { display: flex; gap: 16px; margin-bottom: 32px; }
        .comment-composer-wrapper { flex: 1; }
        .comment-box {
            width: 100%;
            background: transparent;
            border: none;
            border-bottom: 1px solid var(--text-muted);
            color: var(--text-primary);
            padding: 4px 0;
            font-size: 0.92rem;
            resize: none;
            outline: none;
            transition: border-color 0.2s;
        }
        .comment-box:focus { border-color: var(--text-primary); }
        .comment-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; display: none; }

        .comment-thread-list { display: flex; flex-direction: column; gap: 24px; }
        .comment-node { display: flex; gap: 16px; }
        .comment-node-content { display: flex; flex-direction: column; gap: 4px; }
        .commenter-meta { font-size: 0.82rem; font-weight: 600; color: var(--text-primary); display: flex; gap: 8px; }
        .comment-timestamp { color: var(--text-secondary); font-weight: 400; }
        .comment-text { font-size: 0.92rem; line-height: 1.4; color: #f4f4f5; margin: 0; }
        .comment-interact { display: flex; gap: 12px; margin-top: 4px; color: var(--text-secondary); font-size: 0.78rem; align-items: center; }

        /* --- COMPANION COLUMN (SIDEBAR ENGINE) --- */
        .sidebar-column {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .feed-filter-shelf {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            white-scroll-behavior: contain;
            padding-bottom: 4px;
        }
        .feed-filter-shelf::-webkit-scrollbar { display: none; }
        .chip {
            background: var(--bg-surface-elevated);
            border: 1px solid var(--border-subtle);
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            white-space: nowrap;
            cursor: pointer;
        }
        .chip.active { background: var(--text-primary); color: var(--bg-base); border: none; }

        .recommendation-pipeline { display: flex; flex-direction: column; gap: 12px; }
        
        /* Premium Compact Media Card Objects */
        .media-card-horizontal {
            display: flex;
            gap: 12px;
            text-decoration: none;
            color: inherit;
            cursor: pointer;
            border-radius: 8px;
            padding: 4px;
            transition: background 0.2s;
        }
        .media-card-horizontal:hover { background: rgba(255,255,255,0.03); }
        
        .thumb-wrapper {
            position: relative;
            width: 168px;
            height: 94px;
            border-radius: 8px;
            overflow: hidden;
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            flex-shrink: 0;
        }
        .thumb-image { width: 100%; height: 100%; object-fit: cover; opacity: 0.85; }
        .card-duration {
            position: absolute;
            bottom: 4px;
            right: 4px;
            background: rgba(0,0,0,0.8);
            padding: 2px 4px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 700;
            font-family: monospace;
        }

        .card-metadata-payload {
            display: flex;
            flex-direction: column;
            min-width: 0;
        }
        .card-title-string {
            font-size: 0.88rem;
            font-weight: 600;
            line-height: 1.3;
            color: var(--text-primary);
            margin: 0 0 4px 0;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .card-author-string, .card-metrics-string {
            font-size: 0.78rem;
            color: var(--text-secondary);
            margin: 0;
            line-height: 1.4;
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
        }

        /* --- PLAYER CONTROL BAR SPECIFIC CUSTOM OVERRIDES --- */
        :root {
            --bar-bg: rgba(11, 11, 15, 0.85);
        }
        .video-js .vjs-big-play-button {
            background: linear-gradient(135deg, rgba(168, 85, 247, 0.95), rgba(99, 102, 241, 0.95)) !important;
            border: none !important;
            border-radius: 50% !important;
            width: 72px !important;
            height: 72px !important;
            line-height: 72px !important;
            margin-top: -36px !important;
            margin-left: -36px !important;
            box-shadow: 0 15px 35px rgba(168, 85, 247, 0.5);
            transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        }
        .video-js:hover .vjs-big-play-button { transform: scale(1.1); }
        
        .video-js .vjs-control-bar {
            background: var(--bar-bg) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid var(--border-subtle);
            border-radius: 12px !important;
            width: calc(100% - 24px) !important;
            height: 48px !important;
            bottom: 12px !important;
            left: 12px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        
        .video-js .vjs-progress-control {
            position: absolute !important;
            width: calc(100% - 24px) !important;
            height: 6px !important;
            top: -5px !important;
            left: 12px !important;
            transition: height 0.15s;
        }
        .video-js .vjs-progress-control:hover { height: 10px !important; top: -9px !important; }
        .video-js .vjs-play-progress { background: linear-gradient(90deg, var(--accent-secondary), var(--accent-primary)) !important; }
        .video-js .vjs-play-progress:before { display: none !important; }
        .video-js .vjs-time-control { line-height: 48px !important; }
        
        /* Download/Source Controller Injection Styling */
        .vjs-download-control { cursor: pointer; display: flex; align-items: center; justify-content: center; width: 42px; height: 100%; order: 99; }
        .vjs-download-control svg { width: 20px; height: 20px; fill: var(--text-secondary); transition: fill 0.2s, transform 0.2s; }
        .vjs-download-control:hover svg { fill: var(--text-primary); transform: translateY(1px); }
    </style>
</head>
<body>

    <div class="app-container">
        <header class="app-header">
            <div class="header-left">
                <a href="/" class="brand-logo">NebulaView Premium</a>
            </div>
            
            <div class="search-bar-container">
                <input type="text" class="search-input" placeholder="Search downstream indices..." value="{{ title }}">
                <button class="search-btn">
                    <svg style="width:18px;height:18px;fill:currentColor" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                </button>
            </div>
            
            <div class="header-right">
                <button class="action-btn" style="padding: 6px 12px;">
                    <svg style="width:18px;height:18px;fill:currentColor" viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                </button>
                <div class="user-avatar"></div>
            </div>
        </header>

        <main class="stage-layout">
            
            <section class="stream-column">
                <div class="video-player-canvas">
                    <div id="video-loader">
                        <div class="spinner"></div>
                        <div class="loader-text">Configuring Matrix Stream</div>
                    </div>
                    
                    <video id="my-video" class="video-js vjs-default-skin vjs-big-play-centered" controls playsinline>
                        <source src="/manifest?url={{ target_url | urlencode }}&priority={{ priority }}" type="application/x-mpegURL">
                    </video>
                </div>

                <div class="video-meta-card">
                    <h1 class="video-title">{{ title }}</h1>
                    
                    <div class="interact-row">
                        <div class="channel-profile-block">
                            <div class="channel-logo">NV</div>
                            <div class="channel-name-meta">
                                <span class="channel-title">Native Pipeline Core</span>
                                <span class="channel-subs">Automated Cluster Cluster</span>
                            </div>
                            <button class="action-btn accented" style="margin-left: 12px;">Subscribe</button>
                        </div>
                        
                        <div class="action-button-group">
                            <button class="action-btn">
                                <svg style="width:18px;height:18px;fill:currentColor" viewBox="0 0 24 24"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.58 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.75 0 1.41-.41 1.75-1.03l3.58-8.35c.09-.23.14-.48.14-.73v-2z"/></svg>
                                <span>3.4K</span>
                            </button>
                            <button class="action-btn">
                                <svg style="width:18px;height:18px;fill:currentColor" viewBox="0 0 24 24"><path d="M17 3H7c-1.1 0-1.99.9-1.99 2L5 21l7-3 7 3V5c0-1.1-.9-2-2-2z"/></svg>
                                <span>Save</span>
                            </button>
                            <button class="action-btn" id="custom-share-trigger">
                                <svg style="width:18px;height:18px;fill:currentColor" viewBox="0 0 24 24"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.8 2.04.8 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg>
                                <span>Share</span>
                            </button>
                        </div>
                    </div>
                </div>

                <div class="description-expansion-panel" id="desc-panel">
                    <div class="desc-metrics">
                        <span>124,512 views</span>
                        <span>Jun 9, 2026</span>
                        <span style="color:var(--accent-primary)">#NativeStreaming</span>
                    </div>
                    <p class="desc-text-body" id="desc-text">This dynamic pipeline entry establishes an immutable high-performance proxy bridge directly to edge manifest vectors. Real-time HLS fragment reconstruction guarantees adaptive bitrates without persistent buffering sequences. 

Click to read full documentation index regarding architecture topologies, dynamic CORS validation hooks, and custom Video.js runtime event loops.</p>
                </div>

                <div class="comments-module">
                    <div class="comments-header-row">
                        <span>42 Comments</span>
                        <span style="font-size:0.9rem;color:var(--text-secondary);cursor:pointer;display:flex;align-items:center;gap:4px">
                            <svg style="width:18px;height:18px;fill:currentColor" viewBox="0 0 24 24"><path d="M3 18h6v-2H3v2zM3 6v2h18V6H3zm0 7h12v-2H3v2z"/></svg> Sort by
                        </span>
                    </div>

                    <div class="comment-input-block">
                        <div class="channel-logo" style="width:36px;height:36px;font-size:0.85rem">U</div>
                        <div class="comment-composer-wrapper">
                            <textarea class="comment-box" id="comment-box-field" rows="1" placeholder="Add a public comment..."></textarea>
                            <div class="comment-actions" id="comment-actions-row">
                                <button class="action-btn" id="comment-cancel-btn" style="background:transparent;border:none">Cancel</button>
                                <button class="action-btn accented" id="comment-submit-btn" style="padding:6px 12px;font-size:0.8rem">Comment</button>
                            </div>
                        </div>
                    </div>

                    <div class="comment-thread-list">
                        <div class="comment-node">
                            <div class="channel-logo" style="width:36px;height:36px;font-size:0.85rem;color:#3b82f6">DX</div>
                            <div class="comment-node-content">
                                <div class="commenter-meta">@dev_matrix_x <span class="comment-timestamp">2 hours ago</span></div>
                                <p class="comment-text">The segment routing throughput optimization on this endpoint is completely flawless. Dropping the cache boundaries down to 3 seconds practically neutralized live stream skipping errors entirely.</p>
                                <div class="comment-interact">
                                    <svg style="width:14px;height:14px;fill:currentColor;cursor:pointer" viewBox="0 0 24 24"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.58 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.75 0 1.41-.41 1.75-1.03l3.58-8.35c.09-.23.14-.48.14-.73v-2z"/></svg> <span>142</span>
                                    <svg style="width:14px;height:14px;fill:currentColor;cursor:pointer" viewBox="0 0 24 24"><path d="M15 3H6c-.75 0-1.41.41-1.75 1.03l-3.58 8.35c-.09.23-.14.48-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"/></svg>
                                    <span style="font-weight:700;cursor:pointer;margin-left:8px">Reply</span>
                                </div>
                            </div>
                        </div>

                        <div class="comment-node">
                            <div class="channel-logo" style="width:36px;height:36px;font-size:0.85rem;color:#10b981">H</div>
                            <div class="comment-node-content">
                                <div class="commenter-meta">@hls_packet_master <span class="comment-timestamp">5 hours ago</span></div>
                                <p class="comment-text">Is there any plan to support alternative audio descriptive multi-tracks natively through the manifest proxy compiler pipeline later on?</p>
                                <div class="comment-interact">
                                    <svg style="width:14px;height:14px;fill:currentColor;cursor:pointer" viewBox="0 0 24 24"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.58 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.75 0 1.41-.41 1.75-1.03l3.58-8.35c.09-.23.14-.48.14-.73v-2z"/></svg> <span>19</span>
                                    <svg style="width:14px;height:14px;fill:currentColor;cursor:pointer" viewBox="0 0 24 24"><path d="M15 3H6c-.75 0-1.41.41-1.75 1.03l-3.58 8.35c-.09.23-.14.48-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"/></svg>
                                    <span style="font-weight:700;cursor:pointer;margin-left:8px">Reply</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <aside class="sidebar-column">
                <div class="feed-filter-shelf">
                    <div class="chip active">All</div>
                    <div class="chip">From this pipe</div>
                    <div class="chip">Related indices</div>
                    <div class="chip">Live Streams</div>
                </div>

                <div class="recommendation-pipeline">
                    <div class="media-card-horizontal" onclick="injectAlternativeIndex('x7tgv4a')">
                        <div class="thumb-wrapper">
                            <div class="thumb-image" style="background:linear-gradient(45deg, #1e1b4b, #311042)"></div>
                            <span class="card-duration">14:22</span>
                        </div>
                        <div class="card-metadata-payload">
                            <h4 class="card-title-string">High Throughput HLS Optimization Layout Patterns</h4>
                            <p class="card-author-string">Nebula Architecture</p>
                            <p class="card-metrics-string">45K views &bull; 3 days ago</p>
                        </div>
                    </div>

                    <div class="media-card-horizontal" onclick="injectAlternativeIndex('x80kh31')">
                        <div class="thumb-wrapper">
                            <div class="thumb-image" style="background:linear-gradient(45deg, #022c22, #111827)"></div>
                            <span class="card-duration">08:05</span>
                        </div>
                        <div class="card-metadata-payload">
                            <h4 class="card-title-string">Bypassing Multi-Origin Sandbox Blockades Safely</h4>
                            <p class="card-author-string">CORS Security Node</p>
                            <p class="card-metrics-string">120K views &bull; 1 week ago</p>
                        </div>
                    </div>

                    <div class="media-card-horizontal" onclick="injectAlternativeIndex('x9zbkt6')">
                        <div class="thumb-wrapper">
                            <div class="thumb-image" style="background:linear-gradient(45deg, #3b0764, #030712)"></div>
                            <span class="card-duration">22:40</span>
                        </div>
                        <div class="card-metadata-payload">
                            <h4 class="card-title-string">Decoding Segment TS Packets with Custom Array Buffers</h4>
                            <p class="card-author-string">Binary Stream Dev</p>
                            <p class="card-metrics-string">8.9K views &bull; 24 hours ago</p>
                        </div>
                    </div>

                    <div class="media-card-horizontal" onclick="injectAlternativeIndex('x7w239b')">
                        <div class="thumb-wrapper">
                            <div class="thumb-image" style="background:linear-gradient(45deg, #4c0519, #1c1917)"></div>
                            <span class="card-duration">11:14</span>
                        </div>
                        <div class="card-metadata-payload">
                            <h4 class="card-title-string">Dynamic Chunk Allocations and Edge Execution Overheads</h4>
                            <p class="card-author-string">Infrastructure Team</p>
                            <p class="card-metrics-string">92K views &bull; 5 days ago</p>
                        </div>
                    </div>
                </div>
            </aside>

        </main>
    </div>

    <script src="https://vjs.zencdn.net/8.10.0/video.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            // Instantiate complex player settings engine
            const player = videojs('my-video', {
                preload: 'auto',
                autoplay: true,
                controls: true,
                fluid: false,
                html5: {
                    vhs: {
                        overrideNative: true,
                        maxBufferLength: 45,
                        enableLowInitialPlaylist: true,
                        fastStart: true,
                        allowCrossDomains: true
                    }
                }
            });

            // Append customizable button architecture once ready
            player.ready(function() {
                const controlBar = player.getChild('controlBar');
                const downloadBtn = document.createElement('div');
                downloadBtn.className = 'vjs-download-control vjs-control vjs-button';
                downloadBtn.title = 'Access Native Manifest Path';
                downloadBtn.innerHTML = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 20h14v-2H5v2zM19 9h-4V3H9v6H5l7 7 7-7z"/></svg>`;
                
                downloadBtn.addEventListener('click', function() {
                    const currentSrc = player.src();
                    const urlParams = new URLSearchParams(currentSrc.split('?')[1]);
                    const targetM3u8Url = urlParams.get('url');
                    window.open(targetM3u8Url ? decodeURIComponent(targetM3u8Url) : currentSrc, '_blank');
                });
                controlBar.el().appendChild(downloadBtn);
            });

            // Handle transition drop-off of video loading envelope masks
            player.on('canplay', function() {
                const loader = document.getElementById('video-loader');
                if (loader) {
                    loader.style.opacity = '0';
                    setTimeout(() => loader.remove(), 400);
                }
                player.play().catch(() => {
                    player.muted(true);
                    player.play();
                });
            });

            /* --- INTERACTIVE REACTION HANDLERS --- */
            // Description Expand/Collapse Panel Engine
            const descPanel = document.getElementById('desc-panel');
            const descText = document.getElementById('desc-text');
            let isExpanded = false;
            
            descPanel.addEventListener('click', function() {
                if(!isExpanded) {
                    descText.style.maxHeight = 'none';
                    descPanel.style.backgroundColor = 'var(--bg-surface-elevated)';
                    isExpanded = true;
                } else {
                    descPanel.style.backgroundColor = 'var(--bg-surface)';
                    isExpanded = false;
                }
            });

            // Active Input Area Comment Field States
            const commentBox = document.getElementById('comment-box-field');
            const commentActions = document.getElementById('comment-actions-row');
            const cancelComment = document.getElementById('comment-cancel-btn');

            commentBox.addEventListener('focus', function() {
                commentActions.style.display = 'flex';
            });

            cancelComment.addEventListener('click', function() {
                commentBox.value = '';
                commentActions.style.display = 'none';
            });

            // Native Share Endpoint Interface Simulator
            document.getElementById('custom-share-trigger').addEventListener('click', function() {
                if (navigator.share) {
                    navigator.share({
                        title: document.title,
                        url: window.location.href
                    }).catch(console.error);
                } else {
                    navigator.clipboard.writeText(window.location.href);
                    alert("App endpoint vector copied directly to user clipboard payload.");
                }
            });
        });

        // Alternative Recommendation Ingestion Routing Helper
        function injectAlternativeIndex(targetMediaIdentifier) {
            window.location.href = '/download?id_or_url=' + encodeURIComponent(targetMediaIdentifier);
        }
    </script>
</body>
</html>
"""

# --- ROUTE HANDLERS ---

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

    if "dailymotion.com" in user_input:
        target_url = user_input if user_input.startswith(("http://", "https://")) else f"https://{user_input}"
    else:
        target_url = f"https://www.dailymotion.com/video/{user_input}"

    ydl_opts = {
        'format': 'best/any', 
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,              
        'check_formats': 'cached',          
        'extract_flat': False,
        'impersonate': ImpersonateTarget.from_str('chrome'),
        'socket_timeout': 5,                
        'extractor_args': {
            'dailymotion': {
                'pubkey': [''],             
            }
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            
            if not info:
                return "yt_dlp failed to extract a valid metadata envelope.", 500
                
            formats = info.get('formats', [])
            hls_streams = [f for f in formats if 'm3u8' in str(f.get('url','')) or 'hls' in str(f.get('format_id','')).lower()]
            m3u8_url = hls_streams[-1].get('url') if hls_streams else info.get('url')

            if not m3u8_url and formats:
                m3u8_url = formats[-1].get('url')

            if not m3u8_url:
                return "No playable stream paths found within the yt_dlp response object.", 404

            return render_template_string(
                PLAYER_TEMPLATE, 
                title=info.get('title', 'Native Stream Source'),
                target_url=m3u8_url,
                priority=priority_flag
            )
            
    except Exception as error:
        # --- CRITICAL FALLBACK TRIGGER ---
        # If extraction drops an error, we immediately fire a separate update check 
        # in a thread so the current visitor doesn't get blocked by an entirely frozen process loop.
        print(f"[Extraction Failure] Forcing emergency update check due to error: {error}")
        threading.Thread(target=run_pip_update).start()
        
        return f"Extraction Pipeline Exception Error: {str(error)}. A critical engine patch check has been initiated.", 500


@app.route('/manifest')
def proxy_m3u8():
    raw_m3u8_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_m3u8_url:
        return "Missing proxy reference targets", 400

    raw_m3u8_url = urllib.parse.unquote(raw_m3u8_url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        resp = http_pool.get(raw_m3u8_url, headers=headers, timeout=4)
    except Exception:
        return "Edge latency timeout during proxy resolution", 504

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

    response = Response("\n".join(rewritten_lines), content_type="application/x-mpegURL")
    response.headers["Cache-Control"] = "public, max-age=3"
    return response


@app.route('/segment')
def proxy_ts_segment():
    raw_ts_url = request.args.get('url')
    priority = request.args.get('priority', 'standard')
    if not raw_ts_url:
        return "Missing segment sequence indices", 400

    raw_ts_url = urllib.parse.unquote(raw_ts_url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    timeout_val = 4 if priority == "high" else 5
    
    try:
        req = http_pool.get(raw_ts_url, headers=headers, stream=True, timeout=timeout_val)
        content_type = req.headers.get('Content-Type', 'video/MP2T')
        
        def stream_ts_data():
            for block in req.iter_content(chunk_size=1024 * 256):
                yield block

        response = Response(stream_ts_data(), content_type=content_type)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
    except Exception:
        return "Segment connection dropped", 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
