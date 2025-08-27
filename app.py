from flask import Flask, request, redirect, session
import subprocess

app = Flask(__name__)
app.secret_key = 'secret'

SERVER_PATH = "/home/dayz/servers/teste"
USERNAME = "2302"
PASSWORD = "@12345"
FILES = {'server.cfg': f'{SERVER_PATH}/serverDZ.cfg'}

def status():
    return subprocess.run(['pgrep', '-f', 'DayZServer'], capture_output=True).returncode == 0

def run(cmd):
    subprocess.run([f'./{cmd}.sh'], cwd=SERVER_PATH, timeout=30)

@app.route('/')
def index():
    if not session.get('login'):
        return '''
        <form method=post action=/login>
        User:<input name=u><br>
        Pass:<input type=password name=p><br>
        <button>Login</button>
        </form>
        '''
    return f'''
    <h3>Server: {"ON" if status() else "OFF"}</h3>
    <form method=post action=/cmd>
    <button name=c value=start>Start</button>
    <button name=c value=stop>Stop</button>
    </form>
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
    return '<br>'.join([f'<a href=/edit?f={name}>{name}</a>' for name in FILES]) + '<br><a href=/>Back</a>'

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
    <textarea name=c>{content}</textarea><br>
    <button>Save</button>
    </form>
    <a href=/files>Back</a>
    '''

@app.route('/save', methods=['POST'])
def save():
    f = request.form.get('f')
    if f in FILES:
        with open(FILES[f], 'w') as file:
            file.write(request.form.get('c'))
    return redirect('/files')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
