import os
import subprocess
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, url_for, Response, abort

app = Flask(__name__)
app.secret_key = "change-me"

# Paths
SERVER_PATH = Path("/home/dayz/servers/2302")
SCRIPTS = {
    "start": SERVER_PATH / "start.sh",
    "stop": SERVER_PATH / "stop.sh",
    "update": SERVER_PATH / "update.sh",
    "updatemods": SERVER_PATH / "update_mods.sh",
    "console": SERVER_PATH / "console.sh",
}
MANAGED_ROOTS = [
    SERVER_PATH / "mpmissions",
    SERVER_PATH / "serverDZ.cfg",
    SERVER_PATH / "profiles",
    SERVER_PATH / "mods",
]

# HTML Templates
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DayZ Server Control</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 font-sans">
    <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold mb-4">DayZ Server Control</h1>
        <div class="grid grid-cols-2 gap-2 mb-4">
            {% for cmd in ['start', 'stop', 'update', 'updatemods'] %}
            <form action="{{ url_for('action', cmd=cmd) }}" method="POST">
                <button type="submit" class="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600">
                    {{ cmd.capitalize() }}
                </button>
            </form>
            {% endfor %}
        </div>
        <a href="{{ url_for('files') }}" class="text-blue-500 hover:underline">Manage Files</a> |
        <a href="{{ url_for('console_stream') }}" class="text-blue-500 hover:underline">View Console</a>
    </div>
</body>
</html>
"""

FILES_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Manager</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 font-sans">
    <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold mb-4">File Manager</h1>
        <a href="{{ url_for('index') }}" class="text-blue-500 hover:underline mb-4 inline-block">Back to Home</a>
        {% for tree in trees %}
        <div class="mb-4">
            <h2 class="text-lg font-semibold">{{ tree.name }}</h2>
            <ul class="ml-4">
                {% for child in tree.children %}
                <li>
                    {% if child.type == 'dir' %}
                    <span class="text-gray-700">{{ child.name }}/</span>
                    <ul class="ml-4">
                        {% for subchild in child.children %}
                        <li>
                            {% if subchild.type == 'file' %}
                            <a href="{{ url_for('edit_file', file_path=subchild.path[1:]) }}" class="text-blue-500 hover:underline">{{ subchild.name }}</a>
                            {% else %}
                            <span class="text-gray-700">{{ subchild.name }}/</span>
                            {% endif %}
                        </li>
                        {% endfor %}
                    </ul>
                    {% else %}
                    <a href="{{ url_for('edit_file', file_path=child.path[1:]) }}" class="text-blue-500 hover:underline">{{ child.name }}</a>
                    {% endif %}
                </li>
                {% endfor %}
            </ul>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

EDIT_FILE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit {{ filename }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 font-sans">
    <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold mb-4">Edit {{ filename }}</h1>
        <a href="{{ url_for('files') }}" class="text-blue-500 hover:underline mb-4 inline-block">Back to Files</a>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        {% for category, message in messages %}
        <p class="text-{{ 'green' if category == 'ok' else 'red' }}-500">{{ message }}</p>
        {% endfor %}
        {% endif %}
        {% endwith %}
        <form method="POST">
            <textarea name="content" class="w-full h-96 p-2 border rounded">{{ content }}</textarea>
            <button type="submit" class="mt-2 bg-blue-500 text-white p-2 rounded hover:bg-blue-600">Save</button>
        </form>
    </div>
</body>
</html>
"""

CONSOLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Console</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        async function streamConsole() {
            const output = document.getElementById('console-output');
            const response = await fetch('{{ url_for('console_stream') }}');
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                output.textContent += decoder.decode(value);
                output.scrollTop = output.scrollHeight;
            }
        }
        window.onload = streamConsole;
    </script>
</head>
<body class="bg-gray-100 font-sans">
    <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold mb-4">Server Console</h1>
        <a href="{{ url_for('index') }}" class="text-blue-500 hover:underline mb-4 inline-block">Back to Home</a>
        <pre id="console-output" class="bg-black text-white p-4 rounded h-96 overflow-auto"></pre>
    </div>
</body>
</html>
"""

# Utilities
def is_allowed_path(p: Path) -> bool:
    p = p.resolve()
    return any(str(p).startswith(str(root.resolve())) for root in MANAGED_ROOTS)

def build_tree(path: Path):
    path = path.resolve()
    node = {"name": path.name or str(path), "path": str(path), "type": "dir", "children": []}
    try:
        for entry in sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
            node["children"].append(
                {"name": entry.name, "path": str(entry.resolve()), "type": "file"}
                if entry.is_file() else build_tree(entry)
            )
    except PermissionError:
        pass
    return node

def run_background(script_path: Path):
    subprocess.Popen(["bash", str(script_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Routes
@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/action/<cmd>", methods=["POST"])
def action(cmd):
    if cmd not in SCRIPTS or not SCRIPTS[cmd].exists():
        abort(404)
    run_background(SCRIPTS[cmd])
    return ("", 204)

@app.route("/files")
def files():
    trees = [build_tree(root) for root in MANAGED_ROOTS if root.exists()]
    return render_template_string(FILES_HTML, trees=trees)

@app.route("/edit/<path:file_path>", methods=["GET", "POST"])
def edit_file(file_path):
    p = Path("/" + file_path).resolve()
    if not is_allowed_path(p) or not p.exists() or p.is_dir():
        abort(404)

    if request.method == "POST":
        content = request.form.get("content", "")
        try:
            p.write_text(content, encoding="utf-8")
            app.logger.info(f"File {p} saved successfully")
        except Exception as e:
            app.logger.error(f"Error saving file {p}: {e}")
        return redirect(url_for("edit_file", file_path=str(p)[1:]))

    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = p.read_bytes().decode("latin-1", errors="replace")
    return render_template_string(EDIT_FILE_HTML, filename=str(p), content=content)

@app.route("/console")
def console():
    return render_template_string(CONSOLE_HTML)

@app.route("/console-stream")
def console_stream():
    if not SCRIPTS["console"].exists():
        return Response("Console script not found.\n", mimetype="text/plain")
    def generate():
        proc = subprocess.Popen(
            ["bash", str(SCRIPTS["console"])],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        try:
            for line in proc.stdout:
                yield line
        finally:
            proc.terminate()
    return Response(generate(), mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
