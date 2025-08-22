from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'secret'

def get_db_connection():
    conn = sqlite3.connect('solicitudes.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE nombre_usuario = ? AND contrasena = ?', (usuario, contrasena)).fetchone()
        conn.close()
        if user:
            session['usuario'] = user['nombre_usuario']
            session['rol'] = user['rol']
            return redirect('/solicitud' if user['rol'] == 'solicitante' else '/admin')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/solicitud', methods=['GET', 'POST'])
def solicitud():
    if 'usuario' not in session or session['rol'] != 'solicitante':
        return redirect('/login')
    if request.method == 'POST':
        data = (
            request.form['sede'], request.form['fecha'], session['usuario'], request.form['proceso'],
            request.form['descripcion'], request.form['proyecto'], float(request.form['monto']),
            request.form['prioridad'], request.form['proveedor'], request.form['justificacion'],
            'pendiente', request.form['fecha']
        )
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO solicitudes (
                sede, fecha, nombre, proceso, descripcion, proyecto,
                monto, prioridad, proveedor, justificacion, estado, fecha_creacion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        conn.commit()
        conn.close()
        return redirect('/solicitud')
    return render_template('solicitud.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'usuario' not in session or session['rol'] not in ['aprobador', 'administrador']:
        return redirect('/login')
    conn = get_db_connection()
    query = "SELECT * FROM solicitudes WHERE 1=1"
    params = []
    if request.method == 'POST':
        if request.form['nombre']:
            query += " AND nombre LIKE ?"
            params.append(f"%{request.form['nombre']}%")
        if request.form['estado']:
            query += " AND estado = ?"
            params.append(request.form['estado'])
    solicitudes = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('admin.html', solicitudes=solicitudes)

@app.route('/cambiar_estado/<int:id>/<estado>')
def cambiar_estado(id, estado):
    if 'usuario' not in session or session['rol'] not in ['aprobador', 'administrador']:
        return redirect('/login')
    conn = get_db_connection()
    conn.execute("UPDATE solicitudes SET estado = ? WHERE id = ?", (estado, id))
    conn.commit()
    conn.close()
    return redirect('/admin')

if __name__ == '__main__':
   import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)

