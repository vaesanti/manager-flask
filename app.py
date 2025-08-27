from flask import Flask, request, jsonify, redirect, session, render_template_string
import subprocess
import os
import threading
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = None  # Removido SocketIO para simplificar

# Configurações
SERVER_PATH = "/home/dayz/servers/teste"
LOGIN_USERNAME = "2302"
LOGIN_PASSWORD = "xM@n2012x"
EDITABLE_FILES = {
    "server.cfg": f"{SERVER_PATH}/serverDZ.cfg",
    "basic.cfg": f"{SERVER_PATH}/basic.cfg",
    "types.xml": f"{SERVER_PATH}/mpmissions/dayzOffline.chernarusplus/db/types.xml"
}

# Templates mínimos
LOGIN_TEMPLATE = '''
<form method=post onsubmit="login(event)">
    <h3>Login</h3>
    <input name=username placeholder=Usuário required>
    <input type=password name=password placeholder=Senha required>
    <button>Entrar</button>
    <div id=error style=color:red></div>
</form>
<script>
async function login(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const response = await fetch('/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: formData.get('username'), password: formData.get('password')})
    });
    const result = await response.json();
    if (result.success) window.location.href = '/';
    else document.getElementById('error').textContent = result.error;
}
</script>
'''

DASHBOARD_TEMPLATE = '''
<h3>Servidor DayZ</h3>
<div>Status: {{ "ONLINE" if online else "OFFLINE" }} | Jogadores: 0/60</div>
<div>
    <button onclick="action('start')">Iniciar</button>
    <button onclick="action('stop')">Parar</button>
    <button onclick="action('update')">Atualizar</button>
    <button onclick="location.href='/files'">Arquivos</button>
</div>
<div id=status></div>
<pre id=log style=height:200px;overflow:auto;background:#000;color:#0f0></pre>
<script>
function action(cmd) {
    fetch('/' + cmd + '_server', {method: 'POST'})
    .then(r => r.json())
    .then(data => document.getElementById('status').textContent = data.success ? 'Sucesso' : 'Erro: ' + data.error);
}
setInterval(() => fetch('/log').then(r => r.text()).then(t => document.getElementById('log').textContent = t), 1000);
</script>
<a href=/logout>Sair</a>
'''

FILES_TEMPLATE = '''
<h3>Arquivos</h3>
{% for name, path in files.items() %}
<div><a href=/edit/{{ name }}>{{ name }}</a></div>
{% endfor %}
<a href=/>Voltar</a>
'''

EDIT_TEMPLATE = '''
<h3>Editando {{ name }}</h3>
<textarea style="width:100%;height:300px" name=content>{{ content }}</textarea>
<br>
<button onclick="save()">Salvar</button>
<a href=/files>Voltar</a>
<script>
function save() {
    const formData = new FormData();
    formData.append('path', '{{ path }}');
    formData.append('content', document.querySelector('textarea').value);
    fetch('/save', {method: 'POST', body: formData})
    .then(r => r.json())
    .then(data => alert(data.success ? 'Salvo' : 'Erro: ' + data.error));
}
</script>
'''

# Funções auxiliares
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'): return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def get_status():
    try: return subprocess.run(['pgrep', '-f', 'DayZServer'], capture_output=True).returncode == 0
    except: return False

def run_cmd(cmd):
    try:
        result = subprocess.run([f"./{cmd}.sh"], cwd=SERVER_PATH, capture_output=True, text=True, timeout=30)
        return {"success": True, "output": result.stdout, "error": result.stderr}
    except Exception as e: return {"success": False, "error": str(e)}

def read_log():
    try: return subprocess.run(['tail', '-n', '50', f"{SERVER_PATH}/server_console.log"], capture_output=True, text=True).stdout
    except: return "Erro ao ler log"

# Rotas
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET': return render_template_string(LOGIN_TEMPLATE)
    data = request.get_json()
    if data.get('username') == LOGIN_USERNAME and data.get('password') == LOGIN_PASSWORD:
        session['logged_in'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Credenciais inválidas"})

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/')
@login_required
def dashboard(): return render_template_string(DASHBOARD_TEMPLATE, online=get_status())

@app.route('/start_server', methods=['POST'])
@login_required
def start_server(): return jsonify(run_cmd('start'))

@app.route('/stop_server', methods=['POST'])
@login_required
def stop_server(): return jsonify(run_cmd('stopServer'))

@app.route('/update_server', methods=['POST'])
@login_required
def update_server(): return jsonify(run_cmd('update'))

@app.route('/log')
@login_required
def get_log(): return read_log()

@app.route('/files')
@login_required
def files(): return render_template_string(FILES_TEMPLATE, files=EDITABLE_FILES)

@app.route('/edit/<name>')
@login_required
def edit(name):
    if name not in EDITABLE_FILES: return redirect('/files')
    path = EDITABLE_FILES[name]
    try: content = open(path, 'r').read()
    except: content = "Erro ao ler arquivo"
    return render_template_string(EDIT_TEMPLATE, name=name, path=path, content=content)

@app.route('/save', methods=['POST'])
@login_required
def save():
    path, content = request.form.get('path'), request.form.get('content')
    if path not in EDITABLE_FILES.values(): return jsonify({"success": False, "error": "Acesso negado"})
    try:
        with open(path, 'w') as f: f.write(content)
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
