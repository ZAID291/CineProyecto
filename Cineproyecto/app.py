from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)


# LOGIN ----------------------------------------------------


@app.route("/")
def inicio():
    return render_template("login.html")


# DUEÑO --------------------------------------------------- 


@app.route("/dueno")
def dueno():
    return redirect(url_for("pagina_principal_dueno"))


@app.route("/dueno/pagina-principal")
def pagina_principal_dueno():
    return render_template("dueño/pagina_principal.html")


@app.route("/dueno/alertas")
def alertas():
    return render_template("dueño/alertas.html")


@app.route("/dueno/boletos")
def boletos():
    return render_template("dueño/boletos.html")


@app.route("/dueno/cartelera")
def cartelera():
    return render_template("dueño/cartelera.html")


@app.route("/dueno/dulceria")
def dulceria_dueno():
    return render_template("dueño/dulceria.html")


@app.route("/dueno/finanzas")
def finanzas():
    return render_template("dueño/finanzas.html")


@app.route("/dueno/inventario")
def inventario():
    return render_template("dueño/inventario.html")


@app.route("/dueno/operaciones")
def operaciones():
    return render_template("dueño/operaciones.html")


@app.route("/dueno/personal")
def personal():
    return render_template("dueño/personal.html")


@app.route("/dueno/salas")
def salas():
    return render_template("dueño/salas.html")

# empleado --------------------------------------

@app.route("/empleado")
def empleado():
    return redirect(url_for("pagina_principal_empleado"))


@app.route("/empleado/pagina-principal")
def pagina_principal_empleado():
    return render_template("empleado/pagina_principal.html")


@app.route("/empleado/dulceria")
def dulceria_empleado():
    return render_template("empleado/dulceria.html")


@app.route("/empleado/taquilla")
def taquilla():
    return render_template("empleado/taquilla.html")


if __name__ == "__main__":
    app.run(debug=True,host="127.0.0.1",port=5000)