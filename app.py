from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret_key'

# 👇 Importamos el script de inicialización
from init_db import init_db  

app = Flask(__name__)
app.secret_key = 'secret_key'

# 👇 Ejecutamos la inicialización de la BD apenas arranque la app
init_db()  

def get_db_connection():
    conn = sqlite3.connect('solicitudes.db')
    conn.row_factory = sqlite3.Row
    return conn

# Rutas de tu aplicación
@app.route('/')
def index():
    return redirect('/login')

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE nombre_usuario = ? AND contrasena = ?', (usuario, contrasena)).fetchone()
        conn.close()
        if user:
            session['usuario'] = user['nombre_usuario']
            session['rol'] = user['rol']
            if user['rol'] == 'solicitante':
                return redirect('/solicitud')
            else:
                return redirect('/admin')
        else:
            error = 'Credenciales incorrectas'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/solicitud', methods=['GET', 'POST'])
def solicitud():
    if 'usuario' not in session or session['rol'] != 'solicitante':
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        # Insertar la solicitud principal
        data = (
            request.form['sede'],
            request.form['fecha'],
            session['usuario'],
            request.form['proceso'],
            request.form['descripcion'],
            request.form['proyecto'],
            request.form['monto'],
            request.form['prioridad'],
            request.form['proveedor'],
            request.form['justificacion'],
            'pendiente',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        cursor.execute('''INSERT INTO solicitudes 
            (sede, fecha, nombre, proceso, descripcion, proyecto, monto, prioridad, proveedor, justificacion, estado, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)

        solicitud_id = cursor.lastrowid  # ID de la solicitud recién creada

        # Insertar ítems de l


@app.route('/admin', methods=['GET'])
def admin():
    if 'usuario' not in session or session['rol'] not in ['aprobador', 'administrador']:
        return redirect('/login')
    nombre = request.args.get('nombre', '')
    estado = request.args.get('estado', '')
    conn = get_db_connection()
    query = 'SELECT * FROM solicitudes WHERE 1=1'
    params = []
    if nombre:
        query += ' AND nombre LIKE ?'
        params.append(f'%{nombre}%')
    if estado:
        query += ' AND estado = ?'
        params.append(estado)
    solicitudes = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('admin.html', solicitudes=solicitudes, nombre=nombre, estado=estado)

@app.route('/cambiar_estado/<int:id>/<nuevo_estado>')
def cambiar_estado(id, nuevo_estado):
    if 'usuario' not in session or session['rol'] not in ['aprobador', 'administrador']:
        return redirect('/login')
    conn = get_db_connection()
    conn.execute('UPDATE solicitudes SET estado = ? WHERE id = ?', (nuevo_estado, id))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/usuarios', methods=['GET'])
def gestionar_usuarios():
    if 'usuario' not in session or session['rol'] != 'administrador':
        return redirect('/login')
    conn = get_db_connection()
    usuarios = conn.execute('SELECT * FROM usuarios').fetchall()
    conn.close()
    return render_template('gestionar_usuarios.html', usuarios=usuarios)

@app.route('/admin/crear_usuario', methods=['GET', 'POST'])
def crear_usuario():
    if 'usuario' not in session or session['rol'] != 'administrador':
        return redirect('/login')
    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario']
        contrasena = request.form['contrasena']
        rol = request.form['rol']
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO usuarios (nombre_usuario, contrasena, rol) VALUES (?, ?, ?)", (nombre_usuario, contrasena, rol))
            conn.commit()
        except sqlite3.IntegrityError:
            # Handle case where user already exists
            pass
        finally:
            conn.close()
        return redirect('/admin/usuarios')
    return render_template('crear_usuario.html')

@app.route('/admin/editar_usuario/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    if 'usuario' not in session or session['rol'] != 'administrador':
        return redirect('/login')
    conn = get_db_connection()
    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario']
        rol = request.form['rol']
        conn.execute("UPDATE usuarios SET nombre_usuario = ?, rol = ? WHERE id = ?", (nombre_usuario, rol, id))
        conn.commit()
        conn.close()
        return redirect('/admin/usuarios')
    
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (id,)).fetchone()
    conn.close()
    if usuario is None:
        return 'Usuario no encontrado', 404
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/admin/eliminar_usuario/<int:id>')
def eliminar_usuario(id):
    if 'usuario' not in session or session['rol'] != 'administrador':
        return redirect('/login')
    conn = get_db_connection()
    conn.execute("DELETE FROM usuarios WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin/usuarios')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
