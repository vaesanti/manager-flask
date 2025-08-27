from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit
import subprocess
import os
import threading
import time
from functools import wraps
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dayz_server_secret_key_change_this'
socketio = SocketIO(app, cors_allowed_origins="*")

# ========== CONFIGURAÇÕES ==========
SERVER_PATH = "/home/dayz/servers/teste"
LOG_FILE = f"{SERVER_PATH}/server_console.log"
MANAGED_FOLDERS = {
    "mpmissions": f"{SERVER_PATH}/mpmissions/dayzOffline.chernarusplus",
    "serverDZ": f"{SERVER_PATH}",
    "profiles": f"{SERVER_PATH}/profiles"
}

# Configurações do servidor
#SERVER_NAME = subprocess.Popen("curl -s 'https://dayzsalauncher.com/api/v1/query/147.79.110.201/27016' | jq -r '.result.name'", shell=True, stdout=subprocess.PIPE, text=True).communicate()[0].strip()
SERVER_NAME = "Meu DayZ Server"
SERVER_IP = subprocess.Popen("curl -s 'https://dayzsalauncher.com/api/v1/query/147.79.110.201/27036' | jq -r '.result.endpoint.ip'", shell=True, stdout=subprocess.PIPE, text=True).communicate()[0].strip()
result = subprocess.Popen("curl -s 'https://dayzsalauncher.com/api/v1/query/147.79.110.201/27036' | jq -r '.result.gamePort'", shell=True, stdout=subprocess.PIPE, text=True).communicate()[0].strip()
# Trata o resultado
if result == "null" or not result:
    SERVER_PORT = "-"
else:
    SERVER_PORT = result
MAX_PLAYERS = subprocess.Popen("curl -s 'https://dayzsalauncher.com/api/v1/query/147.79.110.201/27036' | jq -r '.result.maxPlayers'", shell=True, stdout=subprocess.PIPE, text=True).communicate()[0].strip()

# Configurações de login
LOGIN_USERNAME = "2302"
LOGIN_PASSWORD = "xM@n2012x"

# ========== TEMPLATES HTML ==========
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - {{ server_name }}</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1a1a1a, #2c3e50); color: #fff; margin: 0; padding: 0; height: 100vh; display: flex; align-items: center; justify-content: center; }
        .login-container { background: rgba(44, 62, 80, 0.9); padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); width: 100%; max-width: 400px; }
        .login-header { text-align: center; margin-bottom: 30px; }
        .login-header h1 { margin: 0; font-size: 28px; color: #3498db; }
        .login-header p { margin: 10px 0 0 0; color: #bdc3c7; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: bold; color: #ecf0f1; }
        .form-group input { width: 100%; padding: 12px; border: none; border-radius: 8px; background: #34495e; color: #fff; font-size: 16px; box-sizing: border-box; }
        .form-group input:focus { outline: none; background: #3498db; }
        .btn-login { width: 100%; padding: 15px; background: linear-gradient(45deg, #27ae60, #2ecc71); color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: all 0.3s ease; }
        .btn-login:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .error-message { background: #e74c3c; padding: 10px; border-radius: 5px; margin-bottom: 20px; text-align: center; display: none; }
        .game-icon { font-size: 48px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <div class="game-icon">🎮</div>
            <h1>{{ server_name }}</h1>
            <p>Painel de Controle</p>
        </div>
        
        <div id="error-message" class="error-message"></div>
        
        <form id="login-form">
            <div class="form-group">
                <label for="username">Usuário:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Senha:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit" class="btn-login">🔐 Entrar</button>
        </form>
    </div>

    <script>
        document.getElementById('login-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('error-message');
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                
                const result = await response.json();
                
                if (result.success) {
                    window.location.href = '/';
                } else {
                    errorDiv.textContent = result.error;
                    errorDiv.style.display = 'block';
                    setTimeout(() => errorDiv.style.display = 'none', 3000);
                }
            } catch (error) {
                errorDiv.textContent = 'Erro de conexão';
                errorDiv.style.display = 'block';
            }
        });
    </script>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ server_name }} - Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a1a; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(45deg, #2c3e50, #34495e); border-radius: 10px; }
        .header-left h1 { margin: 0; }
        .header-left p { margin: 5px 0 0 0; color: #bdc3c7; }
        .logout-btn { background: #e74c3c; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; }
        .server-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .info-card { background: #34495e; padding: 15px; border-radius: 8px; text-align: center; border-left: 4px solid #3498db; }
        .info-card.online { border-left-color: #27ae60; }
        .info-card.offline { border-left-color: #e74c3c; }
        .info-value { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
        .info-label { font-size: 14px; color: #bdc3c7; }
        .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
        .status-dot.online { background: #27ae60; }
        .status-dot.offline { background: #e74c3c; }
        .controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .btn { padding: 15px 20px; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: all 0.3s ease; text-decoration: none; text-align: center; display: inline-block; }
        .btn-start { background: linear-gradient(45deg, #27ae60, #2ecc71); color: white; }
        .btn-stop { background: linear-gradient(45deg, #e74c3c, #c0392b); color: white; }
        .btn-update { background: linear-gradient(45deg, #3498db, #2980b9); color: white; }
        .btn-files { background: linear-gradient(45deg, #f39c12, #e67e22); color: white; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .console { background: #000; border: 2px solid #333; border-radius: 8px; padding: 15px; height: 400px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 14px; }
        .console-line { margin: 2px 0; color: #00ff00; }
        .status { background: #2c3e50; padding: 10px; border-radius: 5px; margin: 10px 0; text-align: center; }
        .loading { display: none; color: #f39c12; font-weight: bold; }
        #updateModal { display: none; position: fixed; z-index: 1; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4); }
        .modal-content { background-color: #2c3e50; margin: 15% auto; padding: 20px; border: 1px solid #888; width: 80%; max-width: 400px; border-radius: 10px; }
        .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; }
        .close:hover, .close:focus { color: white; text-decoration: none; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h1>🎮 {{ server_name }}</h1>
                <p>Painel de Controle do Servidor DayZ</p>
            </div>
            <a href="/logout" class="logout-btn">🚪 Sair</a>
        </div>
        
        <div class="server-info">
            <div class="info-card {% if server_online %}online{% else %}offline{% endif %}">
                <div class="info-value">
                    <span class="status-dot {% if server_online %}online{% else %}offline{% endif %}"></span>
                    {% if server_online %}ONLINE{% else %}OFFLINE{% endif %}
                </div>
                <div class="info-label">Status do Servidor</div>
            </div>
            
            <div class="info-card">
                <div class="info-value">{{ player_count }}/{{ max_players }}</div>
                <div class="info-label">Jogadores Conectados</div>
            </div>
            
            <div class="info-card">
                <div class="info-value">{{ server_ip }}</div>
                <div class="info-label">Endereço IP</div>
            </div>
            
            <div class="info-card">
                <div class="info-value">{{ server_port }}</div>
                <div class="info-label">Porta</div>
            </div>
        </div>

        <div class="controls">
            <button class="btn btn-start" onclick="serverAction('start')">▶️ Iniciar Servidor</button>
            <button class="btn btn-stop" onclick="serverAction('stop')">⏹️ Parar Servidor</button>
            <button class="btn btn-update" onclick="openUpdateModal()">🔄 Atualizar Servidor</button>
            <a href="/files" class="btn btn-files">📁 Gerenciar Arquivos</a>
        </div>
        <div class="status" id="status">Status: Aguardando comando...</div>
        <div class="loading" id="loading">Executando comando...</div>
        <div class="console" id="console">
            <div class="console-line"></div>
            <div class="console-line"></div>
        </div>
    </div>

    <!-- Modal para credenciais Steam -->
    <div id="updateModal">
        <div class="modal-content">
            <span class="close" onclick="closeUpdateModal()">&times;</span>
            <h2>Credenciais Steam</h2>
            <form id="updateForm">
                <div class="form-group">
                    <label for="steamUser">Usuário Steam:</label>
                    <input type="text" id="steamUser" required>
                </div>
                <div class="form-group">
                    <label for="steamPass">Senha Steam:</label>
                    <input type="password" id="steamPass" required>
                </div>
                <div class="form-group">
                    <label for="steamGuard">Steam Guard (opcional):</label>
                    <input type="text" id="steamGuard">
                </div>
                <button type="submit" class="btn btn-update">Atualizar</button>
            </form>
        </div>
    </div>

    <script>
        const socket = io();
        const console_div = document.getElementById('console');
        const status_div = document.getElementById('status');
        const loading_div = document.getElementById('loading');
        socket.emit('start_log_monitor');
        socket.on('log_update', function(data) {
            const line = document.createElement('div');
            line.className = 'console-line';
            line.textContent = new Date().toLocaleTimeString() + ' - ' + data.data;
            console_div.appendChild(line);
            console_div.scrollTop = console_div.scrollHeight;
        });

        setInterval(updateServerStatus, 10000);
        
        function updateServerStatus() {
            fetch('/server_status')
                .then(response => response.json())
                .then(data => {
                    const statusCard = document.querySelector('.info-card.online, .info-card.offline');
                    const statusValue = statusCard.querySelector('.info-value');
                    const statusDot = statusCard.querySelector('.status-dot');
                    
                    if (data.online) {
                        statusCard.className = 'info-card online';
                        statusDot.className = 'status-dot online';
                        statusValue.innerHTML = '<span class="status-dot online"></span>ONLINE';
                    } else {
                        statusCard.className = 'info-card offline';
                        statusDot.className = 'status-dot offline';
                        statusValue.innerHTML = '<span class="status-dot offline"></span>OFFLINE';
                    }
                    
                    const playersCard = document.querySelectorAll('.info-card')[1];
                    playersCard.querySelector('.info-value').textContent = data.players + '/' + data.max_players;
                })
                .catch(error => console.log('Erro ao atualizar status:', error));
        }

        function openUpdateModal() {
            document.getElementById('updateModal').style.display = 'block';
        }

        function closeUpdateModal() {
            document.getElementById('updateModal').style.display = 'none';
        }

        document.getElementById('updateForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const user = document.getElementById('steamUser').value;
            const pass = document.getElementById('steamPass').value;
            const guard = document.getElementById('steamGuard').value;
            closeUpdateModal();
            await serverAction('update', {steam_user: user, steam_pass: pass, steam_guard: guard});
        });

        async function serverAction(action, data = null) {
            loading_div.style.display = 'block';
            status_div.textContent = `Executando ${action}...`;
            try {
                const options = {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                };
                if (data) {
                    options.body = JSON.stringify(data);
                }
                const response = await fetch(`/${action}_server`, options);
                const result = await response.json();
                if (result.success) {
                    status_div.textContent = `${action} executado com sucesso!`;
                    status_div.style.background = '#27ae60';
                    if (result.output) {
                        const line = document.createElement('div');
                        line.className = 'console-line';
                        line.textContent = `[${action.toUpperCase()}] ${result.output}`;
                        console_div.appendChild(line);
                    }
                } else {
                    status_div.textContent = `Erro ao executar ${action}: ${result.error}`;
                    status_div.style.background = '#e74c3c';
                    const line = document.createElement('div');
                    line.className = 'console-line';
                    line.style.color = '#ff0000';
                    line.textContent = `[ERRO] ${result.error}`;
                    console_div.appendChild(line);
                }
                setTimeout(() => { status_div.style.background = '#2c3e50'; }, 3000);
            } catch (error) {
                status_div.textContent = `Erro de conexão: ${error.message}`;
                status_div.style.background = '#e74c3c';
            }
            loading_div.style.display = 'none';
            console_div.scrollTop = console_div.scrollHeight;
        }
    </script>
</body>
</html>
'''

FILE_MANAGER_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gerenciador de Arquivos - {{ server_name }}</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a1a; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; padding: 20px; background: linear-gradient(45deg, #2c3e50, #34495e); border-radius: 10px; margin-bottom: 20px; }
        .breadcrumb { background: #2c3e50; padding: 10px 15px; border-radius: 5px; margin-bottom: 20px; word-break: break-all; }
        .folder-nav { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 20px; }
        .folder-btn { padding: 10px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; text-align: center; transition: all 0.3s ease; }
        .folder-btn:hover { background: #2980b9; transform: translateY(-1px); }
        .file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .file-item, .folder-item { background: #2c3e50; padding: 15px; border-radius: 8px; border-left: 4px solid; transition: all 0.3s ease; }
        .folder-item { border-left-color: #f39c12; cursor: pointer; }
        .file-item { border-left-color: #27ae60; }
        .file-item:hover, .folder-item:hover { background: #34495e; transform: translateY(-2px); }
        .file-name { font-weight: bold; margin-bottom: 5px; display: flex; align-items: center; gap: 8px; }
        .file-actions { margin-top: 10px; }
        .btn { padding: 8px 12px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 5px; font-size: 12px; transition: all 0.3s ease; }
        .btn-edit { background: #3498db; color: white; }
        .btn-back { background: #95a5a6; color: white; text-decoration: none; padding: 10px 15px; border-radius: 5px; }
        .btn:hover { opacity: 0.8; transform: translateY(-1px); }
        .empty { text-align: center; padding: 40px; color: #95a5a6; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📁 Gerenciador de Arquivos</h1>
            <a href="/" class="btn-back">← Voltar ao Dashboard</a>
        </div>
        <div class="breadcrumb"><strong>Pasta atual:</strong> {{ current_folder_name }}</div>
        <div class="folder-nav">
            {% for folder_id, folder_path in managed_folders.items() %}
            <a href="/files/{{ folder_id }}" class="folder-btn">📂 {{ folder_id }}</a>
            {% endfor %}
        </div>
        <div class="file-grid">
            {% for folder in folders %}
            <div class="folder-item" onclick="window.location.href='/files/{{ current_folder_id }}{% if current_subpath %}/{{ current_subpath }}{% endif %}/{{ folder }}'">
                <div class="file-name">📁 {{ folder }}</div>
                <small>Pasta</small>
            </div>
            {% endfor %}
            {% for file in files %}
            <div class="file-item">
                <div class="file-name">📄 {{ file }}</div>
                <small>{{ file }}</small>
                <div class="file-actions">
                    <a href="/edit/{{ current_folder_id }}{% if current_subpath %}/{{ current_subpath }}{% endif %}/{{ file }}" class="btn btn-edit">✏️ Editar</a>
                </div>
            </div>
            {% endfor %}
        </div>
        {% if not folders and not files %}
        <div class="empty"><p>Pasta vazia ou sem permissão de leitura</p></div>
        {% endif %}
    </div>
</body>
</html>
'''

EDIT_FILE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Editor - {{ filename }}</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a1a; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; padding: 20px; background: linear-gradient(45deg, #2c3e50, #34495e); border-radius: 10px; margin-bottom: 20px; }
        .file-path { background: #2c3e50; padding: 10px 15px; border-radius: 5px; margin-bottom: 20px; word-break: break-all; font-family: monospace; }
        .editor-container { position: relative; }
        #file-editor { width: 100%; min-height: 600px; background: #1e1e1e; color: #d4d4d4; border: 2px solid #333; border-radius: 8px; padding: 15px 15px 15px 65px; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.4; resize: vertical; tab-size: 4; }
        .actions { display: flex; gap: 10px; margin-top: 15px; }
        .btn { padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; transition: all 0.3s ease; text-decoration: none; display: inline-block; }
        .btn-save { background: linear-gradient(45deg, #27ae60, #2ecc71); color: white; }
        .btn-back { background: linear-gradient(45deg, #95a5a6, #7f8c8d); color: white; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .status { position: fixed; top: 20px; right: 20px; padding: 15px 25px; border-radius: 8px; font-weight: bold; z-index: 1000; display: none; }
        .status.success { background: #27ae60; color: white; }
        .status.error { background: #e74c3c; color: white; }
        .line-numbers { position: absolute; left: 0; top: 0; bottom: 0; width: 50px; background: #2d2d30; border-right: 1px solid #3e3e42; color: #858585; font-family: monospace; font-size: 14px; line-height: 1.4; padding: 15px 5px; overflow: hidden; user-select: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✏️ Editor de Arquivo</h1>
            <div class="actions">
                <button class="btn btn-save" onclick="saveFile()">💾 Salvar</button>
                <a href="/files" class="btn btn-back">← Voltar</a>
            </div>
        </div>
        <div class="file-path"><strong>Arquivo:</strong> {{ filename }}</div>
        <div class="editor-container">
            <div class="line-numbers" id="line-numbers">1</div>
            <textarea id="file-editor">{{ content }}</textarea>
        </div>
    </div>
    <div class="status" id="status"></div>
    <script>
        const editor = document.getElementById('file-editor');
        const lineNumbers = document.getElementById('line-numbers');
        const status = document.getElementById('status');
        function updateLineNumbers() {
            const lines = editor.value.split('\\n').length;
            let lineNumbersText = '';
            for (let i = 1; i <= lines; i++) { lineNumbersText += i + '\\n'; }
            lineNumbers.textContent = lineNumbersText;
        }
        editor.addEventListener('input', updateLineNumbers);
        editor.addEventListener('scroll', () => { lineNumbers.scrollTop = editor.scrollTop; });
        editor.addEventListener('keydown', function(e) {
            if (e.key === 'Tab') {
                e.preventDefault();
                const start = this.selectionStart;
                const end = this.selectionEnd;
                this.value = this.value.substring(0, start) + "    " + this.value.substring(end);
                this.selectionStart = this.selectionEnd = start + 4;
                updateLineNumbers();
            }
        });
        async function saveFile() {
            const formData = new FormData();
            formData.append('filepath', '{{ filepath }}');
            formData.append('content', editor.value);
            try {
                const response = await fetch('/save_file', { method: 'POST', body: formData });
                const result = await response.json();
                if (result.success) { showStatus('Arquivo salvo com sucesso!', 'success'); }
                else { showStatus('Erro ao salvar: ' + result.error, 'error'); }
            } catch (error) { showStatus('Erro de conexão: ' + error.message, 'error'); }
        }
        function showStatus(message, type) {
            status.textContent = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
            setTimeout(() => { status.style.display = 'none'; }, 3000);
        }
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 's') { e.preventDefault(); saveFile(); }
        });
        updateLineNumbers();
    </script>
</body>
</html>
'''

# ========== FUNÇÕES DE SEGURANÇA ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# ========== FUNÇÕES AUXILIARES ==========
def get_server_status():
    """Verifica se o servidor DayZ está rodando na porta 2302"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', r'DayZServer.*port=2302\b'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Erro ao verificar status do servidor: {e}")
        return False

def run_shell_script(script_name, args=None):
    """Executa um script shell no diretório do servidor com argumentos opcionais"""
    if args is None:
        args = []
    try:
        result = subprocess.run(
            [f"./{script_name}.sh"] + args,
            cwd=SERVER_PATH,
            capture_output=True,
            text=True,
            timeout=300  # Aumentado timeout para update
        )
        return {"success": result.returncode == 0, "output": result.stdout, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def tail_log_file():
    """Monitora o arquivo de log em tempo real"""
    try:
        process = subprocess.Popen(
            ['tail', '-f', LOG_FILE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        for line in iter(process.stdout.readline, ''):
            if line:
                socketio.emit('log_update', {'data': line.strip()})
    except Exception as e:
        socketio.emit('log_update', {'data': f'Erro ao ler log: {str(e)}'})

# ========== ROTAS DE LOGIN ==========
@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_TEMPLATE, server_name=SERVER_NAME)

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username == LOGIN_USERNAME and password == LOGIN_PASSWORD:
        session['logged_in'] = True
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Usuário ou senha incorretos"})

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login_page'))

# ========== ROTAS PRINCIPAIS ==========
@app.route('/')
@login_required
def dashboard():
    server_online = get_server_status()
    
    # Busca contagem de jogadores da API
    try:
        result = subprocess.Popen(
            "curl -s 'https://dayzsalauncher.com/api/v1/query/147.79.110.201/27036' | jq -r '.result'",
            shell=True,
            stdout=subprocess.PIPE,
            text=True
        ).communicate()[0].strip()
        
        if result and result != "null":
            data = json.loads(result)
            player_count = data.get('players', 0)
            max_players = data.get('maxPlayers', MAX_PLAYERS)
        else:
            player_count = 0
            max_players = MAX_PLAYERS
    except Exception as e:
        print(f"Erro ao buscar dados da API: {e}")
        player_count = 0
        max_players = MAX_PLAYERS

    return render_template_string(DASHBOARD_TEMPLATE, 
                                server_name=SERVER_NAME,
                                server_ip=SERVER_IP,
                                server_port=SERVER_PORT,
                                server_online=server_online,
                                player_count=player_count,
                                max_players=max_players)

@app.route('/start_server', methods=['POST'])
@login_required
def start_server():
    result = run_shell_script('start')
    return jsonify(result)

@app.route('/stop_server', methods=['POST'])
@login_required
def stop_server():
    result = run_shell_script('stopServer2302')
    return jsonify(result)

@app.route('/update_server', methods=['POST'])
@login_required
def update_server():
    data = request.get_json()
    user = data.get('steam_user')
    passw = data.get('steam_pass')
    guard = data.get('steam_guard', '')
    args = [user, passw]
    if guard:
        args.append(guard)
    result = run_shell_script('update', args)
    return jsonify(result)

@app.route('/server_status')
@login_required
def server_status():
    """Endpoint para atualizar status via AJAX"""
    try:
        server_online = get_server_status()
        
        result = subprocess.Popen(
            "curl -s 'https://dayzsalauncher.com/api/v1/query/147.79.110.201/27036' | jq -r '.result'",
            shell=True,
            stdout=subprocess.PIPE,
            text=True
        ).communicate()[0].strip()

        if result and result != "null":
            data = json.loads(result)
            player_count = data.get('players', 0)
            max_players = data.get('maxPlayers', MAX_PLAYERS)
        else:
            player_count = 0
            max_players = MAX_PLAYERS

        return jsonify({
            'online': server_online,
            'players': player_count,
            'max_players': max_players
        })
    except Exception as e:
        print(f"Erro ao buscar status: {e}")
        return jsonify({
            'online': get_server_status(),
            'players': 0,
            'max_players': MAX_PLAYERS
        })

@app.route('/files')
@app.route('/files/<folder_id>')
@app.route('/files/<folder_id>/<path:subpath>')
@login_required
def file_manager(folder_id=None, subpath=None):
    if not folder_id:
        folder_id = list(MANAGED_FOLDERS.keys())[0]
    
    if folder_id in MANAGED_FOLDERS:
        base_path = MANAGED_FOLDERS[folder_id]
        current_path = os.path.join(base_path, subpath) if subpath else base_path
    else:
        folder_id = list(MANAGED_FOLDERS.keys())[0]
        current_path = MANAGED_FOLDERS[folder_id]
    
    allowed = any(current_path.startswith(path) for path in MANAGED_FOLDERS.values())
    
    if not allowed or not os.path.exists(current_path):
        folder_id = list(MANAGED_FOLDERS.keys())[0]
        current_path = MANAGED_FOLDERS[folder_id]
        subpath = None
    
    files = []
    folders = []
    
    try:
        for item in os.listdir(current_path):
            item_path = os.path.join(current_path, item)
            if os.path.isdir(item_path):
                folders.append(item)
            elif os.path.isfile(item_path):
                files.append(item)
    except Exception as e:
        print(f"Erro ao listar arquivos: {e}")
    
    return render_template_string(FILE_MANAGER_TEMPLATE, 
                                server_name=SERVER_NAME,
                                current_folder_id=folder_id,
                                current_subpath=subpath,
                                current_folder_name=folder_id if not subpath else f"{folder_id}/{subpath}",
                                folders=folders,
                                files=files,
                                managed_folders=MANAGED_FOLDERS)

@app.route('/edit/<folder_id>/<filename>')
@app.route('/edit/<folder_id>/<path:subpath>/<filename>')
@login_required
def edit_file(folder_id, filename, subpath=None):
    if folder_id in MANAGED_FOLDERS:
        base_path = MANAGED_FOLDERS[folder_id]
        filepath = os.path.join(base_path, subpath, filename) if subpath else os.path.join(base_path, filename)
    else:
        return redirect('/files')
    
    allowed = any(filepath.startswith(path) for path in MANAGED_FOLDERS.values())
    
    if not allowed or not os.path.exists(filepath):
        return redirect('/files')
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        content = f"Erro ao ler arquivo: {str(e)}"
    
    return render_template_string(EDIT_FILE_TEMPLATE, 
                                filepath=filepath, 
                                filename=filename,
                                content=content)

@app.route('/save_file', methods=['POST'])
@login_required
def save_file():
    filepath = request.form.get('filepath')
    content = request.form.get('content')
    
    allowed = any(filepath.startswith(path) for path in MANAGED_FOLDERS.values()) if filepath else False
    
    if not allowed:
        return jsonify({"success": False, "error": "Acesso negado a este arquivo"})
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"success": True, "message": "Arquivo salvo com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@socketio.on('start_log_monitor')
def start_log_monitor():
    if not session.get('logged_in'):
        return False
    thread = threading.Thread(target=tail_log_file)
    thread.daemon = True
    thread.start()

@app.before_request
def check_login():
    if request.endpoint and request.endpoint not in ['login_page', 'login', 'static']:
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

