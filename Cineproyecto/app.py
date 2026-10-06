import os

from flask import Flask, render_template, redirect, url_for, abort
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from empleado.dulceria.app import app as dulceria_app
from empleado.taquilla.app import app as taquilla_app

app = Flask(__name__)

TEMPLATES_DIR = os.path.join(app.root_path, "templates")


def paginas_de(carpeta):
    """Nombres (sin .html) de las páginas que existen en templates/<carpeta>."""
    ruta = os.path.join(TEMPLATES_DIR, carpeta)
    return {f[:-5] for f in os.listdir(ruta) if f.endswith(".html")}


PAGINAS_DUENO = paginas_de("dueno")
PAGINAS_DUENO_EMPLEADOS = paginas_de("dueno/empleados")
PAGINAS_GERENCIA = paginas_de("gerencia")


# LOGIN ----------------------------------------------------


@app.route("/")
def inicio():
    return render_template("login.html")


# DUEÑO ---------------------------------------------------


@app.route("/dueno")
@app.route("/dueno/")
def dueno():
    return redirect(url_for("pagina_dueno", pagina="pagina_principal"))


@app.route("/dueno/<pagina>")
def pagina_dueno(pagina):
    if pagina not in PAGINAS_DUENO:
        abort(404)
    return render_template(f"dueno/{pagina}.html")


@app.route("/dueno/empleados/<pagina>")
def pagina_dueno_empleados(pagina):
    if pagina not in PAGINAS_DUENO_EMPLEADOS:
        abort(404)
    return render_template(f"dueno/empleados/{pagina}.html")


# GERENCIA ------------------------------------------------


@app.route("/gerencia")
@app.route("/gerencia/")
def gerencia():
    return redirect(url_for("pagina_gerencia", pagina="pagina_principal"))


@app.route("/gerencia/<pagina>")
def pagina_gerencia(pagina):
    if pagina not in PAGINAS_GERENCIA:
        abort(404)
    return render_template(f"gerencia/{pagina}.html")


# EMPLEADO ------------------------------------------------
# Dulcería y Taquilla son apps Flask independientes montadas
# bajo /empleado/dulceria y /empleado/taquilla.

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    "/empleado/dulceria": dulceria_app,
    "/empleado/taquilla": taquilla_app,
})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
