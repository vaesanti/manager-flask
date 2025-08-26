import os
import subprocess
import threading
from flask import Flask, request, redirect, url_for, render_template_string
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

# Configurações
SCRIPTS_DIR = "scripts"   # onde ficam os start.sh, stop.sh, update.sh
FILES_DIRS = ["/home/dayz/servers/2302"]  # pastas que podem ser gerenciadas
LOG_FILE = "/home/dayz/servers/2302/server.log"


# -------- FUNÇÕES --------
def run_script(script):
    path = os.path.join(SCRIPTS_DIR, script)
    if os.path.exists(path):
        subprocess.Popen(["bash", path])


def tail_log():
    p = subprocess.Popen(["tail", "-f", LOG_FILE], stdout=subprocess.PIPE, text=True)
    for line in iter(p.stdout.readline, ''):
        socketio.emit("log_update", {"line": line.strip()})


# -------- ROTAS --------
@app.route("/")
def index():
    return render_template_string("""
    <h1>DayZ Control Panel</h1>
    <a href="{{ url_for('action', cmd='start') }}"><button>Start</button></a>
    <a href="{{ url_for('action', cmd='stop') }}"><button>Stop</button></a>
    <a href="{{ url_for('action', cmd='update') }}"><button>Update</button></a>
    <br><br>
    <a href="{{ url_for('files') }}"><button>Gerenciar Arquivos</button></a>
    <a href="{{ url_for('console') }}"><button>Console</button></a>
    """)


@app.route("/action/<cmd>")
def action(cmd):
    if cmd == "start":
        run_script("start.sh")
    elif cmd == "stop":
        run_script("stop.sh")
    elif cmd == "update":
        run_script("update.sh")
    return redirect(url_for("index"))


@app.route("/files")
def files():
    paths = []
    for base in FILES_DIRS:
        for root, _, files in os.walk(base):
            for f in files:
                paths.append(os.path.join(root, f))
    return render_template_string("""
    <h2>Arquivos do Servidor</h2>
    <ul>
      {% for f in files %}
        <li><a href="{{ url_for('edit', filename=f) }}">{{ f }}</a></li>
      {% endfor %}
    </ul>
    """, files=paths)


@app.route("/edit/<path:filename>", methods=["GET", "POST"])
def edit(filename):
    if request.method == "POST":
        with open(filename, "w") as f:
            f.write(request.form["content"])
        return redirect(url_for("files"))
    with open(filename, "r") as f:
        content = f.read()
    return render_template_string("""
    <h3>Editando: {{ filename }}</h3>
    <form method="post">
      <textarea name="content" style="width:100%;height:400px;">{{ content }}</textarea><br>
      <button type="submit">Salvar</button>
    </form>
    """, filename=filename, content=content)


@app.route("/console")
def console():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Console</title>
      <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    </head>
    <body>
      <h2>Console - Logs</h2>
      <pre id="console"></pre>
      <script>
        var socket = io();
        socket.emit("start_log", {});
        socket.on("log_update", function(data){
          var c = document.getElementById("console");
          c.innerText += data.line + "\\n";
          c.scrollTop = c.scrollHeight;
        });
      </script>
    </body>
    </html>
    """)


# -------- SOCKET --------
@socketio.on("start_log")
def start_log(_):
    threading.Thread(target=tail_log, daemon=True).start()


# -------- MAIN --------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
