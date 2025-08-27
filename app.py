from flask import Flask, request, jsonify, redirect, session
import subprocess
import os

app = Flask(__name__)
app.secret_key = 'secret'

SERVER_PATH = "/home/dayz/servers/teste"
USERNAME = "2302"
PASSWORD = "12345"
FILES = {
    'server.cfg': f'{SERVER_PATH}/serverDZ.cfg',
    'basic.cfg': f'{SERVER_PATH}/basic.cfg', 
    'types.xml': f'{SERVER_PATH}/mpmissions/dayzOffline.chernarusplus/db/types.xml'
}

def status():
    try: return subprocess.run(['pgrep', '-f', 'DayZServer'], capture_output=True).returncode == 0
    except: return False

def run(cmd):
    try:
        result = subprocess.run([f'./{cmd}.sh'], cwd=SERVER_PATH, capture_output=True, text=True, timeout=30)
        return {'ok': True, 'out': result.stdout}
    except Exception as e: return {'ok': False, 'err': str(e)}

def log():
    try: return subprocess.run(['tail', '-n', '20', f'{SERVER_PATH}/server_console.log'], capture_output=True, text=True).stdout
    except: return 'Erro log'

@app.route('/')
def index():
    if not session.get('login'): return '''
    <form method=post action=/login>
    User:<input name=u><br>
    Pass:<input type=password name=p><br>
    <button>Login</button></form>
    '''
    
    return f'''
    <h3>Server: {"ON" if status() else "OFF"} | Players: 0/60</h3>
    <form method=post action=/cmd>
    <button name=c value=start>Start</button>
    <button name=c value=stop>Stop</button>
    <button name=c value=update>Update</button>
    </form>
    <pre>{log()}</pre>
    <a href=/files>Files</a> | <a href=/logout>Logout</a>
    <script>setTimeout(()=>location.reload(),5000)</script>
    '''

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('u') == USERNAME and request.form.get('p') == PASSWORD:
        session['login'] = True
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/cmd', methods=['POST'])
def cmd():
    result = run(request.form.get('c'))
    return redirect('/')

@app.route('/files')
def files():
    if not session.get('login'): return redirect('/')
    links = ''.join([f'<div><a href=/edit?f={name}>{name}</a></div>' for name in FILES])
    return f'{links}<a href=/>Back</a>'

@app.route('/edit')
def edit():
    if not session.get('login'): return redirect('/')
    f = request.args.get('f')
    if f not in FILES: return redirect('/files')
    try: content = open(FILES[f], 'r').read()
    except: content = 'Error'
    return f'''
    <form method=post action=/save>
    <input type=hidden name=f value={f}>
    <textarea name=c style="width:100%;height:300px">{content}</textarea>
    <br><button>Save</button>
    </form>
    <a href=/files>Back</a>
    '''

@app.route('/save', methods=['POST'])
def save():
    f = request.form.get('f')
    if f in FILES:
        try:
            with open(FILES[f], 'w') as file:
                file.write(request.form.get('c'))
        except: pass
    return redirect('/files')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
