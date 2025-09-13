from flask import Flask, request, redirect, session
import subprocess
import os

app = Flask(__name__)
app.secret_key = 'secret'

SERVER_PATH = "/home/dayz/servers/teste"
USERNAME = os.getenv('USER01')
PASSWORD = os.getenv('PASS01')
FILES = ['serverDZ.cfg', 'basic.cfg', 'types.xml']

def status():
    try: return subprocess.run(['pgrep', '-f', 'DayZServer'], capture_output=True).returncode == 0
    except: return False

def run(cmd):
    try: subprocess.run([f'./{cmd}.sh'], cwd=SERVER_PATH, timeout=10)
    except: pass

def get_log():
    try: return subprocess.run(['tail', '-n', '20', f'{SERVER_PATH}/server_console.log'], capture_output=True, text=True).stdout
    except: return ''

@app.route('/')
def index():
    if not session.get('login'):
        return '''
        <form method=post action=/login>
        <input name=u placeholder=user>
        <input type=password name=p placeholder=pass>
        <button>Login</button>
        '''
    
    return f'''
    <div>Server: {"ON" if status() else "OFF"}</div>
    <form method=post action=/cmd>
    <button name=c value=start>Start</button>
    <button name=c value=stop>Stop</button>
    <button name=c value=update>Update</button>
    </form>
    <pre style="background:#000;color:#0f0;height:150px;overflow:auto">{get_log()}</pre>
    <a href=/files>Files</a> | <a href=/logout>Logout</a>
    <script>setTimeout(()=>location.reload(),2000)</script>
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
    run(request.form.get('c'))
    return redirect('/')

@app.route('/files')
def files():
    if not session.get('login'): return redirect('/')
    links = ''.join([f'<div><a href=/edit?f={f}>{f}</a></div>' for f in FILES])
    return f'{links}<a href=/>Back</a>'

@app.route('/edit')
def edit():
    if not session.get('login'): return redirect('/')
    f = request.args.get('f')
    if f not in FILES: return redirect('/files')
    try: content = open(f'{SERVER_PATH}/{f}', 'r').read()
    except: content = ''
    return f'''
    <textarea name=c style="width:300px;height:200px">{content}</textarea>
    <form method=post action=/save>
    <input type=hidden name=f value={f}>
    <button>Save</button>
    </form>
    <a href=/files>Back</a>
    '''

@app.route('/save', methods=['POST'])
def save():
    f = request.form.get('f')
    if f in FILES:
        try:
            with open(f'{SERVER_PATH}/{f}', 'w') as file:
                file.write(request.form.get('c'))
        except: pass
    return redirect('/files')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

