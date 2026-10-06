from flask import Flask, render_template

app = Flask(__name__)

# ==========================================================
# TAQUILLA
# Aún no tiene conexión a base de datos: las páginas se
# muestran con datos vacíos hasta implementar las consultas.
# ==========================================================

EMPLEADO_DEMO = {"nombre": "Empleado", "apellido": "Taquilla"}


@app.route("/")
@app.route("/pagina_principal")
def pagina_principal():
    return render_template(
        "pagina_principal.html",
        empleado=EMPLEADO_DEMO,
        proximas_funciones=[],
        funciones_dia=[]
    )


@app.route("/venta_boletos")
@app.route("/venta_boletos/<int:id_funcion>")
def venta_boletos(id_funcion=None):
    return "Venta de boletos en desarrollo: falta conectar la base de datos.", 501


@app.route("/cierre_caja")
def cierre_caja():
    return render_template("cierre_caja.html")


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
