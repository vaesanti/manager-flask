import os
import subprocess
from pathlib import Path
from flask import (
    Flask, render_template, request, redirect,
    url_for, Response, abort, flash
)

app = Flask(__name__)
app.secret_key = "change-me"

# Caminhos principais
SERVER_PATH = Path("/home/dayz/servers/2302")

# Scripts do servidor (ajuste se os nomes forem diferentes)
SCRIPTS = {
    "start": SERVER_PATH / "start.sh",
    "stop": SERVER_PATH / "stop.sh",
    "update": SERVER_PATH / "update.sh",
    "updatemods": SERVER_PATH / "update_mods.sh",
    "console": SERVER_PATH / "console.sh",
}

# Raízes que podem ser gerenciadas no painel (pastas/arquivos permitidos)
MANAGED_ROOTS = [
    SERVER_PATH / "mpmissions",
    SERVER_PATH / "serverDZ.cfg",
    SERVER_PATH / "profiles",            # opcional (logs/configs)
    SERVER_PATH / "mods",                # opcional
]

# ---------- util ----------

def is_allowed_path(p: Path) -> bool:
    """Garante que p esteja dentro de alguma raiz permitida (sem path traversal)."""
    p = p.resolve()
    for root in MANAGED_ROOTS:
        try:
            if p.is_relative_to(root.resolve()):
                return True
        except AttributeError:
            # Py<3.9 compat
            if str(p).startswith(str(root.resolve())):
                return True
    return p in [r.resolve() for r in MANAGED_ROOTS]

def build_tree(path: Path):
    """Retorna uma árvore simples para renderização."""
    path = path.resolve()
    node = {"name": path.name or str(path), "path": str(path), "type": "dir", "children": []}
    try:
        for entry in sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
            if entry.is_dir():
                node["children"].append(build_tree(entry))
            else:
                node["children"].append({"name": entry.name, "path": str(entry.resolve()), "type": "file"})
    except PermissionError:
        pass
    return node

def run_background(script_path: Path):
    subprocess.Popen(["bash", str(script_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---------- rotas ----------

@app.route("/")
def index():
    return render_template("index.html", server_path=str(SERVER_PATH))

@app.route("/action/<cmd>", methods=["POST"])
def action(cmd):
    if cmd not in SCRIPTS:
        abort(404)
    run_background(SCRIPTS[cmd])
    return ("", 204)

@app.route("/files")
def files():
    trees = []
    for root in MANAGED_ROOTS:
        if root.exists():
            trees.append(build_tree(root))
    return render_template("files.html", trees=trees)

@app.route("/edit")
def edit_redirect():
    return redirect(url_for("files"))

@app.route("/edit/<path:file_path>", methods=["GET", "POST"])
def edit_file(file_path):
    p = Path("/" + file_path).resolve()  # força absoluto
    if not is_allowed_path(p) or not p.exists() or p.is_dir():
        abort(404)

    if request.method == "POST":
        content = request.form.get("content", "")
        try:
            p.write_text(content, encoding="utf-8")
            flash("Arquivo salvo com sucesso.", "ok")
        except Exception as e:
            flash(f"Erro ao salvar: {e}", "err")
        return redirect(url_for("edit_file", file_path=str(p)[1:]))

    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = p.read_bytes().decode("latin-1", errors="replace")
    return render_template("edit_file.html", filename=str(p), content=content)

@app.route("/console-stream")
def console_stream():
    # Executa o script de console e transmite stdout em tempo real
    if not SCRIPTS["console"].exists():
        return Response("Console script não encontrado.\n", mimetype="text/plain")
    def generate():
        proc = subprocess.Popen(
            ["bash", str(SCRIPTS["console"])],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        try:
            for line in proc.stdout:
                yield line
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
    return Response(generate(), mimetype="text/plain")

if __name__ == "__main__":
    # debug=True opcional; em produção use um WSGI (gunicorn) por trás de um reverse proxy.
    app.run(host="0.0.0.0", port=5000, debug=True)
