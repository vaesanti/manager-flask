from flask import Flask, request, render_template_string, redirect
from flask_socketio import SocketIO
import subprocess
import os
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Configurações: Ajuste esses caminhos e informações
LOG_FILE = '/home/santi/scripts/python/flask/monitor/5/ping.log'  # Caminho do ping.log
ALLOWED_DIRS = ['/path/to/dayz/server/folder1', '/path/to/dayz/server/folder2']  # Pastas permitidas
SERVER_IP = '192.168.1.100'
SERVER_PORT = '2302'
PLAYERS_ONLINE = '20/60'
SERVER_STATUS = 'Online'
SERVER_VERSION = '1.25'

# Função para monitorar o log com tail -f
def tail_log():
    process = subprocess.Popen(['tail', '-f', LOG_FILE], stdout=subprocess.PIPE, text=True)
    while True:
        line = process.stdout.readline()
        if line:
            socketio.emit('console_update', {'data': line.strip() + '<br>'}, namespace='/console')
        time.sleep(0.1)

@socketio.on('connect', namespace='/console')
def handle_connect():
    threading.Thread(target=tail_log, daemon=True).start()

# Template HTML com Tailwind CSS e SocketIO
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>DayZ Server Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.min.js"></script>
</head>
<body class="bg-gray-900 text-white font-sans">
    <div class="min-h-screen flex p-6">
        <div class="w-1/4 pr-6">
            <h1 class="text-3xl font-bold text-purple-400 mb-6">DayZ Server</h1>
            <div class="space-y-4">
                <form action="/start" method="post">
                    <button class="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded w-full">Iniciar Servidor</button>
                </form>
                <form action="/stop" method="post">
                    <button class="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded w-full">Parar Servidor</button>
                </form>
                <form action="/update_server" method="post">
                    <button class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded w-full">Atualizar Servidor</button>
                </form>
                <form action="/update_mods" method="post">
                    <button class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded w-full">Atualizar Mods</button>
                </form>
                <form action="/files" method="get">
                    <button class="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded w-full">Gerenciar Arquivos</button>
                </form>
                <div class="mt-8">
                    <h2 class="text-xl font-semibold text-purple-400 mb-4">Informações do Servidor</h2>
                    <p><strong>IP:Porta:</strong> {{ server_ip }}:{{ server_port }}</p>
                    <p><strong>Jogadores Online:</strong> {{ players_online }}</p>
                    <p><strong>Status:</strong> {{ server_status }}</p>
                    <p><strong>Versão:</strong> {{ server_version }}</p>
                </div>
            </div>
        </div>
        <div class="w-3/4">
            <h2 class="text-2xl font-semibold text-purple-400 mb-4">Console</h2>
            <div id="console" class="w-full h-[80vh] bg-gray-800 text-white p-4 rounded overflow-auto"></div>
        </div>
    </div>
    <script>
        var socket = io('/console');
        socket.on('console_update', function(msg) {
            var consoleDiv = document.getElementById('console');
            consoleDiv.innerHTML += msg.data;
            consoleDiv.scrollTop = consoleDiv.scrollHeight;
        });
    </script>
</body>
</html>
'''

FILES_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Gerenciador de Arquivos</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white font-sans">
    <div class="min-h-screen p-6">
        <h1 class="text-3xl font-bold text-purple-400 mb-6">Gerenciador de Arquivos</h1>
        {% if current_dir %}
            <h2 class="text-xl font-semibold text-gray-300 mb-4">{{ current_dir.split('/')[-1] }}</h2>
            <ul class="ml-4 space-y-2">
                {% for subdir in subdirs %}
                <li><a href="/files?dir={{ current_dir }}/{{ subdir }}" class="text-blue-400 hover:underline">{{ subdir }}/</a></li>
                {% endfor %}
                {% for file in files %}
                <li><a href="/edit?file={{ current_dir }}/{{ file }}" class="text-blue-400 hover:underline">{{ file }}</a></li>
                {% endfor %}
            </ul>
        {% else %}
            <ul class="ml-4 space-y-2">
                {% for dir in dirs %}
                <li><a href="/files?dir={{ dir }}" class="text-blue-400 hover:underline">{{ dir.split('/')[-1] }}/</a></li>
                {% endfor %}
            </ul>
        {% endif %}
        <a href="/" class="mt-4 inline-block text-purple-400 hover:underline">Voltar</a>
    </div>
</body>
</html>
'''

EDIT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Editar Arquivo</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white font-sans">
    <div class="min-h-screen p-6">
        <h1 class="text-3xl font-bold text-purple-400 mb-6">Editar Arquivo: {{ file.split('/')[-1] }}</h1>
        <form method="post">
            <textarea name="content" class="w-full h-96 bg-gray-800 text-white p-4 rounded" rows="20">{{ content }}</textarea>
            <button class="mt-4 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Salvar</button>
        </form>
        <a href="/files" class="mt-4 inline-block text-purple-400 hover:underline">Voltar</a>
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def home():
    return render_template_string(HOME_TEMPLATE, 
                                 server_ip=SERVER_IP, 
                                 server_port=SERVER_PORT, 
                                 players_online=PLAYERS_ONLINE, 
                                 server_status=SERVER_STATUS, 
                                 server_version=SERVER_VERSION)

@app.route('/start', methods=['POST'])
def start():
    try:
        subprocess.Popen(["/home/santi/scripts/python/flask/monitor/5/start.sh"], shell=True)
        return redirect('/')
    except Exception as e:
        return str(e)

@app.route('/stop', methods=['POST'])
def stop():
    try:
        subprocess.Popen(["/home/santi/scripts/python/flask/monitor/5/stop.sh"], shell=True)
        return redirect('/')
    except Exception as e:
        return str(e)

@app.route('/update_server', methods=['POST'])
def update_server():
    try:
        subprocess.Popen(["/home/santi/scripts/python/flask/monitor/5/update.sh"], shell=True)
        return redirect('/')
    except Exception as e:
        return str(e)

@app.route('/update_mods', methods=['POST'])
def update_mods():
    try:
        subprocess.Popen(["/home/santi/scripts/python/flask/monitor/5/update_mods.sh"], shell=True)
        return redirect('/')
    except Exception as e:
        return str(e)

@app.route('/files', methods=['GET'])
def files():
    current_dir = request.args.get('dir')
    if current_dir and any(current_dir.startswith(d) for d in ALLOWED_DIRS):
        subdirs = next(os.walk(current_dir))[1]
        files = next(os.walk(current_dir))[2]
        return render_template_string(FILES_TEMPLATE, current_dir=current_dir, subdirs=subdirs, files=files)
    return render_template_string(FILES_TEMPLATE, dirs=ALLOWED_DIRS)

@app.route('/edit', methods=['GET', 'POST'])
def edit():
    file_path = request.args.get('file') or request.form.get('file')
    if not any(file_path.startswith(d) for d in ALLOWED_DIRS):
        return "Acesso negado", 403
    if request.method == 'POST':
        content = request.form['content']
        with open(file_path, 'w') as f:
            f.write(content)
        return redirect('/files')
    with open(file_path, 'r') as f:
        content = f.read()
    return render_template_string(EDIT_TEMPLATE, file=file_path, content=content)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
