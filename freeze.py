import os
from app import app, db, RRPP, Transporte, Configuracion
from flask_frozen import Freezer

app.config['FREEZER_RELATIVE_URLS'] = True

# --- Freezer convierte la app Flask en archivos HTML estáticos ---
freezer = Freezer(app)

# Le decimos a Freezer dónde guardar los archivos generados
app.config['FREEZER_DESTINATION'] = 'docs'

# Importante: no redirigir URLs sin barra al final
app.config['FREEZER_REDIRECT_POLICY'] = 'ignore'

# --- Le decimos a Freezer qué URLs tiene que generar ---
@freezer.register_generator
def transportes():
    # Genera la página de transportes
    yield {}

if __name__ == '__main__':
    # Creamos la carpeta docs si no existe
    os.makedirs('docs', exist_ok=True)
    
    with app.app_context():
        freezer.freeze()
        print("✅ Sitio generado en la carpeta /docs")