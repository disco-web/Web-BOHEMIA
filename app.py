import os
import requests
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

# --- Carga las variables secretas del archivo .env ---
load_dotenv()

# --- Crea la aplicación Flask ---
app = Flask(__name__)

# --- Clave secreta para manejar sesiones (login) ---
app.secret_key = os.getenv('SECRET_KEY', 'clave_dev_por_defecto')

# --- Configuración de Cloudinary (servicio para guardar fotos) ---
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure = True
)

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
database_url = os.getenv('DATABASE_URL')
if database_url:
    # Corrección necesaria para que funcione en Render
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Si estás trabajando en tu PC, usa una base de datos local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ==================================================
# --- MODELOS (estructura de la base de datos) ---
# Cada clase es una tabla en la base de datos
# ==================================================

class RRPP(db.Model):
    # Cada atributo es una columna de la tabla
    id = db.Column(db.Integer, primary_key=True)      # ID único automático
    localidad = db.Column(db.String(100))              # Ciudad del RRPP
    nombre = db.Column(db.String(100))                 # Nombre del RRPP
    foto_url = db.Column(db.String(500))               # URL de la foto (Cloudinary)
    instagram = db.Column(db.String(200))              # Usuario de Instagram
    whatsapp = db.Column(db.String(200))               # Número de WhatsApp
    orden = db.Column(db.Integer, default=99)          # Orden de aparición en la página
    visible = db.Column(db.Boolean, default=True)      # Si se muestra o no

class Transporte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ciudad = db.Column(db.String(100))                 # Ciudad de origen
    nombre_taxi = db.Column(db.String(100))            # Nombre del servicio
    dueno = db.Column(db.String(100))                  # Nombre del dueño
    descripcion = db.Column(db.String(200))            # Descripción del servicio
    precio = db.Column(db.String(50))                  # Precio del viaje
    whatsapp = db.Column(db.String(200))               # Número de WhatsApp
    orden = db.Column(db.Integer, default=99)          # Orden de aparición
    visible = db.Column(db.Boolean, default=True)      # Si se muestra o no

class Configuracion(db.Model):
    # Tabla con los textos editables de la página
    id = db.Column(db.Integer, primary_key=True)
    texto_header = db.Column(db.String(200))           # Texto debajo del logo
    texto_footer = db.Column(db.String(200))           # Texto del pie de página
    texto_actualizacion = db.Column(db.String(200))    # Aviso en página transportes

# ==================================================
# --- RUTAS (cada @app.route es una URL) ---
# ==================================================

# Página principal - muestra los RRPP
@app.route('/')
def index():
    config = Configuracion.query.first()               # Trae la configuración
    rrpps = RRPP.query.filter_by(visible=True).order_by(RRPP.orden.asc()).all()  # Trae los RRPP visibles
    return render_template('index.html', rrpps=rrpps, config=config, page='rrpp')

# Página de transportes
@app.route('/transportes/')
def transportes():
    config = Configuracion.query.first()
    transportes_all = Transporte.query.filter_by(visible=True).order_by(Transporte.orden.asc()).all()
    
    # Arma la lista de ciudades sin repetir
    lista_ciudades = []
    ciudades_vistas = set()
    for t in transportes_all:
        nombre_ciudad = t.ciudad.strip()
        if nombre_ciudad not in ciudades_vistas:
            lista_ciudades.append(nombre_ciudad)
            ciudades_vistas.add(nombre_ciudad)
    
    return render_template('transportes.html', ciudades=lista_ciudades, transportes=transportes_all, config=config, page='transportes')

# Login del administrador
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Verifica usuario y contraseña contra las variables del .env
        if request.form['username'] == os.getenv('ADMIN_USER') and \
           request.form['password'] == os.getenv('ADMIN_PASS'):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        flash('Datos incorrectos')
    return render_template('login.html', config=Configuracion.query.first())

# Panel de administración
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # Si no está logueado, lo manda al login
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    config = Configuracion.query.first()
    
    if request.method == 'POST':
        tipo = request.form.get('tipo')

        # --- Agregar nuevo RRPP ---
        if tipo == 'add_rrpp':
            foto_final_url = request.form.get('foto_url')
            file = request.files.get('foto')
            if file and file.filename != '':
                # Sube la foto a Cloudinary y guarda la URL
                upload_result = cloudinary.uploader.upload(file)
                foto_final_url = upload_result['secure_url']
            nuevo = RRPP(
                localidad=request.form['localidad'],
                nombre=request.form['nombre'],
                foto_url=foto_final_url,
                instagram=request.form['instagram'],
                whatsapp=request.form['whatsapp'],
                orden=int(request.form.get('orden', 99))
            )
            db.session.add(nuevo)

        # --- Agregar nuevo Transporte ---
        elif tipo == 'add_transporte':
            nuevo = Transporte(
                ciudad=request.form['ciudad'],
                nombre_taxi=request.form['nombre_taxi'],
                dueno=request.form['dueno'],
                descripcion=request.form['descripcion'],
                precio=request.form['precio'],
                whatsapp=request.form['whatsapp'],
                orden=int(request.form.get('orden', 99))
            )
            db.session.add(nuevo)

        # --- Mostrar/Ocultar un RRPP o Transporte ---
        elif tipo == 'toggle':
            if request.form['tabla'] == 'rrpp':
                obj = RRPP.query.get(request.form['id'])
            else:
                obj = Transporte.query.get(request.form['id'])
            if obj:
                obj.visible = not obj.visible

        # --- Eliminar un RRPP o Transporte ---
        elif tipo == 'delete':
            if request.form['tabla'] == 'rrpp':
                RRPP.query.filter_by(id=request.form['id']).delete()
            else:
                Transporte.query.filter_by(id=request.form['id']).delete()

        # --- Guardar textos de configuración ---
        elif tipo == 'config_textos':
            if not config:
                config = Configuracion(texto_header="", texto_footer="", texto_actualizacion="")
                db.session.add(config)
            config.texto_actualizacion = request.form['texto_actualizacion']
            config.texto_footer = request.form['texto_footer']
            config.texto_header = request.form['texto_header']

        db.session.commit()                            # Guarda todos los cambios en la DB
        return redirect(url_for('admin'))

    rrpps = RRPP.query.order_by(RRPP.orden.asc()).all()
    transportes = Transporte.query.order_by(Transporte.orden.asc()).all()
    return render_template('admin.html', rrpps=rrpps, transportes=transportes, config=config)

# Botón publicar - dispara el GitHub Action
@app.route('/publicar', methods=['POST'])
def publicar():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    url = f"https://api.github.com/repos/{os.getenv('REPO_OWNER')}/{os.getenv('REPO_NAME')}/dispatches"
    headers = {
        "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github.v3+json"
    }
    res = requests.post(url, json={"event_type": "update_static_site"}, headers=headers)
    if res.status_code == 204:
        flash("🚀 ¡Publicación iniciada! En 1 minuto la web estará actualizada.")
    else:
        flash("Error al publicar")
    return redirect(url_for('admin'))

# Editar un RRPP existente
@app.route('/edit/rrpp/<int:id>', methods=['GET', 'POST'])
def edit_rrpp(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    rrpp = RRPP.query.get_or_404(id)
    if request.method == 'POST':
        rrpp.localidad = request.form['localidad']
        rrpp.nombre = request.form['nombre']
        rrpp.instagram = request.form['instagram']
        rrpp.whatsapp = request.form['whatsapp']
        rrpp.orden = int(request.form.get('orden', 99))
        file = request.files.get('foto')
        if file and file.filename != '':
            upload_result = cloudinary.uploader.upload(file)
            rrpp.foto_url = upload_result['secure_url']
        elif request.form.get('foto_url'):
            rrpp.foto_url = request.form.get('foto_url')
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_rrpp.html', rrpp=rrpp)

# Editar un Transporte existente
@app.route('/edit/transporte/<int:id>', methods=['GET', 'POST'])
def edit_transporte(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    t = Transporte.query.get_or_404(id)
    if request.method == 'POST':
        t.ciudad = request.form['ciudad']
        t.nombre_taxi = request.form['nombre_taxi']
        t.dueno = request.form['dueno']
        t.descripcion = request.form['descripcion']
        t.precio = request.form['precio']
        t.whatsapp = request.form['whatsapp']
        t.orden = int(request.form.get('orden', 99))
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_transporte.html', transporte=t)

# --- Crea las tablas en la base de datos si no existen ---
with app.app_context():
    db.create_all()

# --- Arranca el servidor ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)