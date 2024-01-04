from flask import Flask, render_template_string, request
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chatting Platform</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
</head>
<body>

<div id="chat-container">
    <ul id="messages"></ul>
    <input id="message-input" autocomplete="off" /><button onclick="sendMessage()">Send</button>
</div>

<script>
    var socket = io.connect('http://' + document.domain + ':' + location.port);

    socket.on('message', function(msg) {
        var ul = document.getElementById('messages');
        var li = document.createElement('li');
        li.appendChild(document.createTextNode(msg));
        ul.appendChild(li);
    });

    function sendMessage() {
        var input = document.getElementById('message-input');
        var message = input.value;
        input.value = '';
        socket.emit('message', message);
    }
</script>

</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html_content)

@socketio.on('message')
def handle_message(msg):
    print('Received message:', msg)
    socketio.emit('message', msg)

if __name__ == '__main__':
    socketio.run(app, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)
