"""
Remote Desktop Server
Relays screen frames from the PC agent to browser viewers,
and sends mouse/keyboard commands from viewers back to the agent.

Run with: python server.py
"""

import os
import json
import time
import threading
from flask import Flask, render_template, request
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

# Shared state
latest_frame = None
frame_lock = threading.Lock()
command_queue = []
command_lock = threading.Lock()
agent_connected = False

# Simple password protection (set via environment variable)
ACCESS_PASSWORD = os.environ.get("REMOTE_DESKTOP_PASSWORD", "changeme")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return {"status": "ok", "agent_connected": agent_connected}


# ─── Agent WebSocket ───────────────────────────────────────────────

@sock.route("/ws/agent")
def agent_ws(ws):
    """
    The PC agent connects here.
    It sends screen frames and receives mouse/keyboard commands.
    """
    global latest_frame, agent_connected

    # Authenticate
    try:
        auth_msg = ws.receive(timeout=10)
        auth_data = json.loads(auth_msg)
        if auth_data.get("password") != ACCESS_PASSWORD:
            ws.send(json.dumps({"type": "error", "message": "Invalid password"}))
            return
        ws.send(json.dumps({"type": "auth_ok"}))
    except Exception:
        return

    agent_connected = True
    print("[+] Agent connected")

    try:
        while True:
            # Receive frame from agent
            data = ws.receive(timeout=30)
            if data is None:
                break

            msg = json.loads(data)
            if msg.get("type") == "frame":
                with frame_lock:
                    latest_frame = msg["data"]  # base64-encoded JPEG

            # Send any queued commands back to the agent
            commands_to_send = []
            with command_lock:
                commands_to_send = command_queue.copy()
                command_queue.clear()

            ws.send(json.dumps({"type": "commands", "commands": commands_to_send}))

    except Exception as e:
        print(f"[-] Agent disconnected: {e}")
    finally:
        agent_connected = False
        print("[-] Agent disconnected")


# ─── Viewer WebSocket ──────────────────────────────────────────────

@sock.route("/ws/viewer")
def viewer_ws(ws):
    """
    Browser viewers connect here.
    They receive screen frames and send mouse/keyboard input.
    """
    # Authenticate
    try:
        auth_msg = ws.receive(timeout=10)
        auth_data = json.loads(auth_msg)
        if auth_data.get("password") != ACCESS_PASSWORD:
            ws.send(json.dumps({"type": "error", "message": "Invalid password"}))
            return
        ws.send(json.dumps({"type": "auth_ok"}))
    except Exception:
        return

    print("[+] Viewer connected")
    last_frame = None

    try:
        while True:
            # Send latest frame if it's new
            with frame_lock:
                current_frame = latest_frame

            if current_frame and current_frame != last_frame:
                ws.send(json.dumps({
                    "type": "frame",
                    "data": current_frame
                }))
                last_frame = current_frame

            # Check for input from viewer (non-blocking)
            try:
                input_msg = ws.receive(timeout=0.05)
                if input_msg:
                    cmd = json.loads(input_msg)
                    if cmd.get("type") in ("click", "key", "move", "scroll", "rightclick", "doubleclick", "keydown", "keyup"):
                        with command_lock:
                            command_queue.append(cmd)
            except Exception:
                pass

            time.sleep(0.03)  # ~30 FPS max

    except Exception as e:
        print(f"[-] Viewer disconnected: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[*] Server starting on port {port}")
    print(f"[*] Password: {ACCESS_PASSWORD}")
    print(f"[*] Agent endpoint: ws://localhost:{port}/ws/agent")
    print(f"[*] Viewer endpoint: ws://localhost:{port}/ws/viewer")
    app.run(host="0.0.0.0", port=port, debug=False)
