import os
from pathlib import Path
from functools import wraps

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory,
)

from flask_wtf.csrf import CSRFProtect


# ==========================================
# CONFIGURACIÓN
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
DUENO_DIR = BASE_DIR / "dueño"
EMPLEADO_DIR = BASE_DIR / "empleado"

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not SECRET_KEY:
    raise RuntimeError("Falta configurar SECRET_KEY en .env")

if not DATABASE_URL:
    raise RuntimeError("Falta configurar DATABASE_URL en .env")

app = Flask(
    __name__,
    template_folder=str(BASE_DIR),
    static_folder=None,
)

app.config["SECRET_KEY"] = SECRET_KEY

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("COOKIE_SECURE", "0") == "1"
)

CSRFProtect(app)


# ==========================================
# CONEXIÓN A POSTGRESQL
# ==========================================

def conectar_db():
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10,
    )


# ==========================================
# CONTROL DE ACCESO POR ROL
# ==========================================

def requiere_login(*roles_permitidos):
    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):

            if not session.get("usuario_id"):
                flash("Inicia sesión para continuar.", "error")
                return redirect(url_for("inicio"))

            if session.get("rol") not in roles_permitidos:
                flash("No tienes permiso para acceder.", "error")
                return redirect(url_for("mi_vista"))

            return funcion(*args, **kwargs)

        return envoltura
    return decorador


# ==========================================
# LOGIN
# ==========================================

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def inicio():

    if request.method == "GET":
        return render_template("login.html")

    correo = request.form.get("correo", "").strip()
    password = request.form.get("password", "")

    if not correo or not password:
        flash("Ingresa tu correo y contraseña.", "error")
        return redirect(url_for("inicio"))

    try:
        with conectar_db() as conn:
            usuario = conn.execute(
                """
                SELECT id, nombre, correo, password_hash, rol
                FROM usuarios
                WHERE LOWER(correo) = LOWER(%s)
                  AND activo = TRUE
                LIMIT 1
                """,
                (correo,),
            ).fetchone()

    except psycopg.Error:
        app.logger.exception("Error consultando PostgreSQL")
        flash(
            "No fue posible conectar con el sistema. "
            "Inténtalo nuevamente.",
            "error",
        )
        return redirect(url_for("inicio"))

    # Validación directa, sin hashes
    if usuario is None or usuario["password_hash"] != password:
        flash("Correo o contraseña incorrectos.", "error")
        return redirect(url_for("inicio"))

    rol = usuario["rol"].strip().lower()

    if rol not in ("admin", "gerente", "operador"):
        flash("El rol de esta cuenta no es válido.", "error")
        return redirect(url_for("inicio"))

    # Crear una sesión nueva
    session.clear()
    session["usuario_id"] = usuario["id"]
    session["nombre"] = usuario["nombre"]
    session["correo"] = usuario["correo"]
    session["rol"] = rol

    return redirect(url_for("mi_vista"))


# ==========================================
# REDIRECCIÓN SEGÚN EL ROL
# ==========================================

@app.route("/mi-vista")
@requiere_login("admin", "gerente", "operador")
def mi_vista():

    rol = session["rol"]

    if rol in ("admin", "gerente"):
        return redirect(
            url_for(
                "dueno_archivo",
                archivo="pagina_principal.html",
            )
        )

    if rol == "operador":
        return redirect(
            url_for(
                "empleado_archivo",
                archivo="taquilla.html",
            )
        )

    session.clear()
    flash("No se pudo determinar tu panel.", "error")
    return redirect(url_for("inicio"))


# ==========================================
# PÁGINAS DEL DUEÑO Y GERENCIA
# ==========================================

PAGINAS_DUENO = {
    "pagina_principal.html",
    "alertas.html",
    "operaciones.html",
    "salas.html",
    "boletos.html",
    "cartelera.html",
    "dulceria.html",
    "inventario.html",
    "personal.html",
    "finanzas.html",
    "reportes.html",
    "configuracion.html",
}


@app.route("/dueno/<path:archivo>")
@requiere_login("admin", "gerente")
def dueno_archivo(archivo):

    # Permitir los CSS de la carpeta dueño
    if archivo.endswith(".css") and "/" not in archivo:
        ruta = DUENO_DIR / archivo

        if ruta.is_file():
            return send_from_directory(DUENO_DIR, archivo)

        return "Archivo CSS no encontrado", 404

    # Solo permitir páginas HTML registradas
    if archivo not in PAGINAS_DUENO:
        return "Página no encontrada", 404

    return render_template(f"dueño/{archivo}")


# ==========================================
# PÁGINAS DEL EMPLEADO
# ==========================================

PAGINAS_EMPLEADO = {
    "dulceria.html",
    "taquilla.html",
}


@app.route("/empleado/<path:archivo>")
@requiere_login("operador")
def empleado_archivo(archivo):

    # Permitir los CSS de la carpeta empleado
    if archivo.endswith(".css") and "/" not in archivo:
        ruta = EMPLEADO_DIR / archivo

        if ruta.is_file():
            return send_from_directory(EMPLEADO_DIR, archivo)

        return "Archivo CSS no encontrado", 404

    if archivo not in PAGINAS_EMPLEADO:
        return "Página no encontrada", 404

    return render_template(f"empleado/{archivo}")


# ==========================================
# CSS DEL LOGIN
# ==========================================

@app.route("/login.css")
def login_css():
    return send_from_directory(BASE_DIR, "login.css")


# ==========================================
# CERRAR SESIÓN
# ==========================================

@app.route("/cerrar-sesion", methods=["POST"])
def cerrar_sesion():

    session.clear()
    flash("Sesión cerrada correctamente.", "success")

    return redirect(url_for("inicio"))


# ==========================================
# EJECUTAR APLICACIÓN
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)
