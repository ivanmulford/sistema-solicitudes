from flask import Flask, render_template, request, redirect, session, flash, jsonify
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    conn = sqlite3.connect('solicitudes.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL,
            rol TEXT NOT NULL,
            nombre_completo TEXT,
            email TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sede TEXT NOT NULL,
            fecha DATE NOT NULL,
            nombre TEXT NOT NULL,
            proceso TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            proyecto TEXT NOT NULL,
            monto REAL NOT NULL,
            prioridad TEXT NOT NULL,
            proveedor TEXT NOT NULL,
            justificacion TEXT NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_aprobacion TIMESTAMP,
            aprobado_por TEXT,
            comentarios TEXT
        )
    ''')
    
    # Insertar usuarios de prueba si no existen
    try:
        conn.execute('''
            INSERT INTO usuarios (nombre_usuario, contrasena, rol, nombre_completo, email)
            VALUES 
                ('admin', 'admin123', 'administrador', 'Administrador Sistema', 'admin@empresa.com'),
                ('aprobador', 'aprob123', 'aprobador', 'Juan Pérez', 'juan.perez@empresa.com'),
                ('solicitante', 'solic123', 'solicitante', 'María García', 'maria.garcia@empresa.com')
        ''')
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Los usuarios ya existen
    
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('solicitudes.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'usuario' in session:
        if session['rol'] == 'solicitante':
            return redirect('/mis-solicitudes')
        else:
            return redirect('/admin')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM usuarios WHERE nombre_usuario = ? AND contrasena = ?', 
            (usuario, contrasena)
        ).fetchone()
        conn.close()
        
        if user:
            session['usuario'] = user['nombre_usuario']
            session['rol'] = user['rol']
            session['nombre_completo'] = user['nombre_completo']
            flash('¡Bienvenido al sistema!', 'success')
            
            if user['rol'] == 'solicitante':
                return redirect('/mis-solicitudes')
            else:
                return redirect('/admin')
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect('/login')

@app.route('/solicitud', methods=['GET', 'POST'])
def nueva_solicitud():
    if 'usuario' not in session or session['rol'] != 'solicitante':
        return redirect('/login')
    
    if request.method == 'POST':
        try:
            data = (
                request.form['sede'],
                request.form['fecha'],
                session['usuario'],
                request.form['proceso'],
                request.form['descripcion'],
                request.form['proyecto'],
                float(request.form['monto']),
                request.form['prioridad'],
                request.form['proveedor'],
                request.form['justificacion'],
                'pendiente'
            )
            
            conn = get_db_connection()
            conn.execute("""
                INSERT INTO solicitudes (
                    sede, fecha, nombre, proceso, descripcion, proyecto,
                    monto, prioridad, proveedor, justificacion, estado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            conn.commit()
            conn.close()
            
            flash('Solicitud creada exitosamente', 'success')
            return redirect('/mis-solicitudes')
            
        except Exception as e:
            flash(f'Error al crear la solicitud: {str(e)}', 'error')
    
    return render_template('solicitud.html')

@app.route('/mis-solicitudes')
def mis_solicitudes():
    if 'usuario' not in session or session['rol'] != 'solicitante':
        return redirect('/login')
    
    conn = get_db_connection()
    solicitudes = conn.execute(
        'SELECT * FROM solicitudes WHERE nombre = ? ORDER BY fecha_creacion DESC',
        (session['usuario'],)
    ).fetchall()
    conn.close()
    
    return render_template('mis_solicitudes.html', solicitudes=solicitudes)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'usuario' not in session or session['rol'] not in ['aprobador', 'administrador']:
        return redirect('/login')
    
    conn = get_db_connection()
    query = "SELECT * FROM solicitudes WHERE 1=1"
    params = []
    
    if request.method == 'POST':
        if request.form.get('nombre'):
            query += " AND nombre LIKE ?"
            params.append(f"%{request.form['nombre']}%")
        if request.form.get('estado'):
            query += " AND estado = ?"
            params.append(request.form['estado'])
        if request.form.get('fecha_desde'):
            query += " AND fecha >= ?"
            params.append(request.form['fecha_desde'])
        if request.form.get('fecha_hasta'):
            query += " AND fecha <= ?"
            params.append(request.form['fecha_hasta'])
    
    query += " ORDER BY fecha_creacion DESC"
    solicitudes = conn.execute(query, params).fetchall()
    
    # Estadísticas
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN estado = 'pendiente' THEN 1 END) as pendientes,
            COUNT(CASE WHEN estado = 'aprobada' THEN 1 END) as aprobadas,
            COUNT(CASE WHEN estado = 'rechazada' THEN 1 END) as rechazadas,
            COALESCE(SUM(CASE WHEN estado = 'aprobada' THEN monto END), 0) as monto_aprobado
        FROM solicitudes
    ''').fetchone()
    
    conn.close()
    return render_template('admin.html', solicitudes=solicitudes, stats=stats)

@app.route('/solicitud/<int:id>')
def ver_solicitud(id):
    if 'usuario' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    solicitud = conn.execute('SELECT * FROM solicitudes WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if not solicitud:
        flash('Solicitud no encontrada', 'error')
        return redirect('/admin' if session['rol'] in ['aprobador', 'administrador'] else '/mis-solicitudes')
    
    # Verificar permisos
    if session['rol'] == 'solicitante' and solicitud['nombre'] != session['usuario']:
        flash('No tienes permisos para ver esta solicitud', 'error')
        return redirect('/mis-solicitudes')
    
    return render_template('detalle_solicitud.html', solicitud=solicitud)

@app.route('/cambiar_estado/<int:id>/<estado>', methods=['POST'])
def cambiar_estado(id, estado):
    if 'usuario' not in session or session['rol'] not in ['aprobador', 'administrador']:
        return redirect('/login')
    
    if estado not in ['aprobada', 'rechazada']:
        flash('Estado inválido', 'error')
        return redirect('/admin')
    
    comentarios = request.form.get('comentarios', '')
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE solicitudes 
        SET estado = ?, fecha_aprobacion = ?, aprobado_por = ?, comentarios = ?
        WHERE id = ?
    ''', (estado, datetime.now(), session['usuario'], comentarios, id))
    conn.commit()
    conn.close()
    
    flash(f'Solicitud {estado} correctamente', 'success')
    return redirect('/admin')

@app.route('/api/stats')
def api_stats():
    if 'usuario' not in session or session['rol'] not in ['aprobador', 'administrador']:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    stats = conn.execute('''
        SELECT 
            estado,
            COUNT(*) as cantidad,
            COALESCE(SUM(monto), 0) as monto_total
        FROM solicitudes
        GROUP BY estado
    ''').fetchall()
    conn.close()
    
    result = {}
    for stat in stats:
        result[stat['estado']] = {
            'cantidad': stat['cantidad'],
            'monto_total': stat['monto_total']
        }
    
    return jsonify(result)

if __name__ == '__main__':
    init_db()  # Inicializar la base de datos
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
