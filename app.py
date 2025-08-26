import os
import subprocess
from pathlib import Path
from flask import Flask, request, redirect, url_for, abort, render_template_string, Response

app = Flask(__name__)
app.secret_key = "changeme"

# Caminhos principais
SERVER_PATH = Path("/home/dayz/servers/2302")
SCRIPTS = {
    "start": SERVER_PATH / "start.sh",
    "stop": SERVER_PATH / "stop.sh",
    "update": SERVER_PATH / "update.sh",
}
LOG_FILE = SERVER_PATH / "server.log"

# Pastas/arquivos permitidos para edição
MANAGED = [
    SERVER_PATH / "mpmissions",
    SERVER_PATH / "serverDZ.cfg",
]

# ---------- utils ----------
def is_allowed(p: Path) -> bool:
    p = p.resolve()
    for root in MANAGED:
        try:
            if p.is_relative_to(root.resolve()):
                return True
        except AttributeError:
            if str(p).startswith(str(root.resolve())):
                return True
    return p in [r.resolve() for r in MANAGED]

# ---------- rotas ----------
@app.route("/")
def index():
    return render_template_string("""
    <h1>DayZ Panel</h1>
    <form action="{{ url_for('action', cmd='start') }}" method="post"><button>Start</button></form>
    <form action="{{ url_for('action', cmd='stop') }}" method="post"><button>Stop</button></form>
    <form action="{{ url_for('action', cmd='update') }}" method="post"><button>Update</button></form>
    <br>
    <a href="{{ url_for('files') }}">Gerenciar Arquivos</a> |
    <a href="{{ url_for('console') }}">Console</a>
    """)

@app.route("/action/<cmd>", methods=["POST"])
def action(cmd):
    if cmd not in SCRIPTS: abort(404)
    subprocess.Popen(["bash", str(SCRIPTS[cmd])])
    return redirect(url_for("index"))

@app.route("/files")
def files():
    all_files = []
    for root in MANAGED:
        if root.exists():
            if root.is_file():
                all_files.append(root)
            else:
                for r, _, fs in os.walk(root):
                    for f in fs:
                        all_files.append(Path(r)/f)
    return render_template_string("""
    <h2>Arquivos</h2>
    <ul>
    {% for f in files %}
      <li><a href="{{ url_for('edit', file_path=str(f)) }}">{{ f }}</a></li>
    {% endfor %}
    </ul>
    """, files=all_files)

@app.route("/edit/<path:file_path>", methods=["GET","POST"])
def edit(file_path):
    p = Path("/"+file_path).resolve()
    if not is_allowed(p) or not p.exists(): abort(404)

    if request.method=="POST":
        p.write_text(request.form["content"], encoding="utf-8")
        return redirect(url_for("files"))

    try:
        content = p.read_text(encoding="utf-8")
    except:
        content = p.read_bytes().decode("latin-1","replace")
    return render_template_string("""
    <h3>Editando: {{filename}}</h3>
    <form method="post">
      <textarea name="content" style="width:100%;height:400px;">{{content}}</textarea><br>
      <button type="submit">Salvar</button>
    </form>
    """, filename=p, content=content)

@app.route("/console")
def console():
    return render_template_string("""
    <h2>Console</h2>
    <pre id="log"></pre>
    <script>
      var src = new EventSource("{{ url_for('console_stream') }}");
      src.onmessage = function(e){
        document.getElementById("log").innerText += e.data + "\\n";
      }
    </script>
    """)

@app.route("/console-stream")
def console_stream():
    def generate():
        proc = subprocess.Popen(
            ["tail","-f",str(LOG_FILE)],
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True
        )
        for line in proc.stdout:
            yield f"data: {line.strip()}\n\n"
    return Response(generate(), mimetype="text/event-stream")

# ---------- main ----------
if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
