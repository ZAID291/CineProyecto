from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from decimal import Decimal
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cinema_pro_dulceria"

# ==========================================================
# CONFIGURACIÓN DE LA BASE DE DATOS
# ==========================================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "cinema_pro_dulceria"
}


# ==========================================================
# CONEXIÓN A MYSQL
# ==========================================================

def get_connection():
    try:
        connection = mysql.connector.connect(
            **DB_CONFIG,
            connection_timeout=10
        )

        if connection.is_connected():
            return connection

    except Error as error:
        print(f"Error de conexión a MySQL: {error}")

    return None


# ==========================================================
# PÁGINA PRINCIPAL
# ==========================================================

@app.route("/")
@app.route("/pagina_principal")
def pagina_principal():

    connection = get_connection()

    if connection is None:
        return "No se pudo conectar con la base de datos."

    cursor = connection.cursor(dictionary=True)

    try:

        query = """
            SELECT
                p.id_producto,
                p.nombre,
                p.descripcion,
                c.nombre AS categoria,
                v.id_variante,
                v.nombre AS variante,
                v.tamano,
                v.sabor,
                v.presentacion,
                v.precio,
                i.existencia,
                i.stock_minimo
            FROM productos p

            INNER JOIN categorias c
                ON p.id_categoria = c.id_categoria

            INNER JOIN variantes_producto v
                ON p.id_producto = v.id_producto

            INNER JOIN inventario i
                ON v.id_variante = i.id_variante

            WHERE p.activo = TRUE
                AND v.activo = TRUE

            ORDER BY
                p.id_producto,
                v.id_variante
        """

        cursor.execute(query)

        productos = cursor.fetchall()

        # --------------------------------------------------
        # RESUMEN DE INVENTARIO
        # --------------------------------------------------

        productos_disponibles = 0
        productos_bajos = 0
        productos_agotados = 0

        for producto in productos:

            existencia = producto["existencia"]
            minimo = producto["stock_minimo"]

            if existencia <= 0:
                productos_agotados += 1

            elif existencia <= minimo:
                productos_bajos += 1

            else:
                productos_disponibles += 1

        # --------------------------------------------------
        # VENTAS DEL DÍA
        # --------------------------------------------------

        query_ventas = """
            SELECT
                COUNT(*) AS ventas_dia
            FROM ventas_dulceria
            WHERE DATE(fecha_hora) = CURDATE()
        """

        cursor.execute(query_ventas)

        resultado_ventas = cursor.fetchone()

        ventas_dia = resultado_ventas["ventas_dia"]

        return render_template(
            "pagina_principal.html",
            productos=productos,
            productos_disponibles=productos_disponibles,
            productos_bajos=productos_bajos,
            productos_agotados=productos_agotados,
            ventas_dia=ventas_dia
        )

    finally:

        cursor.close()
        connection.close()


# ==========================================================
# VENTA DE PRODUCTOS
# ==========================================================

@app.route("/venta_productos", methods=["GET"])
def venta_productos():

    connection = get_connection()

    if connection is None:
        return "No se pudo conectar con la base de datos."

    cursor = connection.cursor(dictionary=True)

    try:

        query_productos = """
            SELECT
                p.id_producto,
                p.nombre AS producto,
                p.descripcion,
                c.nombre AS categoria,

                v.id_variante,
                v.nombre AS variante,
                v.tamano,
                v.sabor,
                v.presentacion,
                v.precio,

                i.existencia,
                i.stock_minimo

            FROM productos p

            INNER JOIN categorias c
                ON p.id_categoria = c.id_categoria

            INNER JOIN variantes_producto v
                ON p.id_producto = v.id_producto

            INNER JOIN inventario i
                ON v.id_variante = i.id_variante

            WHERE p.activo = TRUE
                AND v.activo = TRUE
                AND i.existencia > 0

            ORDER BY
                p.id_producto,
                v.id_variante
        """

        cursor.execute(query_productos)

        productos = cursor.fetchall()

        return render_template(
            "venta_productos.html",
            productos=productos
        )

    finally:

        cursor.close()
        connection.close()

# ==========================================================
# COMPROBANTE - VISTA PREVIA
# ==========================================================
@app.route("/comprobante/preview", methods=["POST"])
def comprobante_preview():
    connection = None
    cursor = None

    try:
        connection = get_connection()

        if connection is None:
            flash(
                "No se pudo conectar con la base de datos.",
                "error"
            )
            return redirect(url_for("venta_productos"))

        cursor = connection.cursor(dictionary=True)

        # --------------------------------------------------
        # RECIBIR DATOS DEL FORMULARIO
        # --------------------------------------------------
        variantes = request.form.getlist("id_variante")
        cantidades = request.form.getlist("cantidad")
        metodo_pago = request.form.get("metodo_pago")

        # --------------------------------------------------
        # VALIDAR MÉTODO DE PAGO
        # --------------------------------------------------
        if metodo_pago not in ["EFECTIVO", "TARJETA"]:
            raise Exception(
                "Método de pago no válido."
            )

        # --------------------------------------------------
        # VALIDAR PRODUCTOS
        # --------------------------------------------------
        if not variantes:
            raise Exception(
                "No se seleccionaron productos."
            )

        if len(variantes) != len(cantidades):
            raise Exception(
                "Los productos y las cantidades no coinciden."
            )

        productos = []
        total = Decimal("0.00")

        # --------------------------------------------------
        # CONSULTAR PRODUCTOS SELECCIONADOS
        # --------------------------------------------------
        for posicion in range(len(variantes)):

            id_variante = int(
                variantes[posicion]
            )

            cantidad = int(
                cantidades[posicion]
            )

            # Ignorar productos con cantidad 0
            if cantidad <= 0:
                continue

            query = """
                SELECT
                    p.id_producto,
                    p.nombre AS producto,
                    p.descripcion,
                    c.nombre AS categoria,
                    v.id_variante,
                    v.nombre AS variante,
                    v.tamano,
                    v.sabor,
                    v.presentacion,
                    v.precio,
                    i.existencia,
                    i.stock_minimo
                FROM variantes_producto v
                INNER JOIN productos p
                    ON v.id_producto = p.id_producto
                INNER JOIN categorias c
                    ON p.id_categoria = c.id_categoria
                INNER JOIN inventario i
                    ON v.id_variante = i.id_variante
                WHERE v.id_variante = %s
                    AND v.activo = TRUE
                    AND p.activo = TRUE
            """

            cursor.execute(
                query,
                (id_variante,)
            )

            producto = cursor.fetchone()

            # --------------------------------------------------
            # VALIDAR EXISTENCIA DEL PRODUCTO
            # --------------------------------------------------
            if producto is None:
                raise Exception(
                    f"La variante con ID "
                    f"{id_variante} no existe."
                )

            existencia = producto["existencia"]

            if cantidad > existencia:
                raise Exception(
                    f"No hay suficiente inventario para "
                    f"{producto['producto']} - "
                    f"{producto['variante']}. "
                    f"Disponibles: {existencia}."
                )

            # --------------------------------------------------
            # CALCULAR SUBTOTAL
            # --------------------------------------------------
            precio = Decimal(
                str(producto["precio"])
            )

            subtotal = precio * cantidad

            total += subtotal

            # --------------------------------------------------
            # GUARDAR PRODUCTO
            # --------------------------------------------------
            productos.append(
                {
                    "id_producto":
                        producto["id_producto"],

                    "id_variante":
                        producto["id_variante"],

                    "producto":
                        producto["producto"],

                    "descripcion":
                        producto["descripcion"],

                    "categoria":
                        producto["categoria"],

                    "variante":
                        producto["variante"],

                    "tamano":
                        producto["tamano"],

                    "sabor":
                        producto["sabor"],

                    "presentacion":
                        producto["presentacion"],

                    "cantidad":
                        cantidad,

                    "precio":
                        precio,

                    "subtotal":
                        subtotal,

                    "existencia":
                        existencia
                }
            )

        # --------------------------------------------------
        # VALIDAR QUE HAYA AL MENOS UN PRODUCTO
        # --------------------------------------------------
        if not productos:
            raise Exception(
                "No seleccionaste ningún producto para vender."
            )

        # --------------------------------------------------
        # FECHA Y HORA
        # --------------------------------------------------
        fecha_hora = datetime.now()

        # --------------------------------------------------
        # CERRAR CONSULTA
        # --------------------------------------------------
        cursor.close()
        cursor = None

        connection.close()
        connection = None

        # --------------------------------------------------
        # MOSTRAR VISTA PREVIA
        # --------------------------------------------------
        return render_template(
            "comprobante.html",
            productos=productos,
            total=total,
            metodo_pago=metodo_pago,
            fecha_hora=fecha_hora,
            confirmado=False
        )

    except Exception as error:

        print(
            f"ERROR EN COMPROBANTE PREVIEW: {error}"
        )

        # --------------------------------------------------
        # CERRAR CURSOR SI SIGUE ABIERTO
        # --------------------------------------------------
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass

        # --------------------------------------------------
        # CERRAR CONEXIÓN SI SIGUE ABIERTA
        # --------------------------------------------------
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

        flash(
            f"No se pudo generar el comprobante: {error}",
            "error"
        )

        return redirect(
            url_for("venta_productos")
        )

# ==========================================================
# CONFIRMAR VENTA
# ==========================================================

@app.route("/confirmar_venta", methods=["POST"])
def confirmar_venta():

    connection = get_connection()

    if connection is None:
        return "No se pudo conectar con la base de datos."

    cursor = connection.cursor(dictionary=True)

    try:

        variantes = request.form.getlist("id_variante")
        cantidades = request.form.getlist("cantidad")
        metodo_pago = request.form.get("metodo_pago")

        # --------------------------------------------------
        # VALIDAR MÉTODO DE PAGO
        # --------------------------------------------------

        if metodo_pago not in ["EFECTIVO", "TARJETA"]:
            raise Exception(
                "Método de pago no válido."
            )

        # --------------------------------------------------
        # VALIDAR PRODUCTOS
        # --------------------------------------------------

        if not variantes:
            raise Exception(
                "No se seleccionaron productos."
            )

        productos_venta = []
        total = Decimal("0.00")

        # ==================================================
        # VALIDAR NUEVAMENTE EL INVENTARIO
        # ==================================================

        for posicion in range(len(variantes)):

            id_variante = int(variantes[posicion])
            cantidad = int(cantidades[posicion])

            if cantidad <= 0:
                continue

            query = """
                SELECT
                    v.id_variante,
                    p.nombre AS producto,
                    v.nombre AS variante,
                    v.precio,
                    i.existencia

                FROM variantes_producto v

                INNER JOIN productos p
                    ON v.id_producto = p.id_producto

                INNER JOIN inventario i
                    ON v.id_variante = i.id_variante

                WHERE v.id_variante = %s
                    AND v.activo = TRUE
                    AND p.activo = TRUE

                FOR UPDATE
            """

            cursor.execute(
                query,
                (id_variante,)
            )

            producto = cursor.fetchone()

            if producto is None:
                raise Exception(
                    "La variante seleccionada no existe."
                )

            existencia = producto["existencia"]

            if cantidad > existencia:
                raise Exception(
                    f"No hay suficiente inventario para "
                    f"{producto['producto']} - "
                    f"{producto['variante']}."
                )

            precio = Decimal(
                str(producto["precio"])
            )

            subtotal = precio * cantidad

            total += subtotal

            productos_venta.append(
                {
                    "id_variante": id_variante,
                    "cantidad": cantidad,
                    "precio": precio,
                    "subtotal": subtotal
                }
            )

        # ==================================================
        # VALIDAR VENTA
        # ==================================================

        if not productos_venta:
            raise Exception(
                "La venta no contiene productos."
            )

        # ==================================================
        # INSERTAR VENTA
        # ==================================================

        query_venta = """
            INSERT INTO ventas_dulceria
            (
                fecha_hora,
                metodo_pago,
                total
            )
            VALUES
            (
                NOW(),
                %s,
                %s
            )
        """

        cursor.execute(
            query_venta,
            (
                metodo_pago,
                total
            )
        )

        id_venta = cursor.lastrowid

        # ==================================================
        # INSERTAR DETALLE Y DESCONTAR INVENTARIO
        # ==================================================

        for producto in productos_venta:

            # --------------------------------------------------
            # INSERTAR DETALLE
            # --------------------------------------------------

            query_detalle = """
                INSERT INTO detalle_venta_dulceria
                (
                    id_venta,
                    id_variante,
                    cantidad,
                    precio_unitario,
                    subtotal
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """

            cursor.execute(
                query_detalle,
                (
                    id_venta,
                    producto["id_variante"],
                    producto["cantidad"],
                    producto["precio"],
                    producto["subtotal"]
                )
            )

            # --------------------------------------------------
            # DESCONTAR INVENTARIO
            # --------------------------------------------------

            query_inventario = """
                UPDATE inventario
                SET
                    existencia = existencia - %s,
                    ultima_actualizacion = NOW()
                WHERE id_variante = %s
            """

            cursor.execute(
                query_inventario,
                (
                    producto["cantidad"],
                    producto["id_variante"]
                )
            )

        # ==================================================
        # CONFIRMAR TRANSACCIÓN
        # ==================================================

        connection.commit()

        return redirect(
            url_for(
                "comprobante",
                id_venta=id_venta
            )
        )

    except Exception as error:

        connection.rollback()

        flash(
            f"No se pudo confirmar la venta: {error}",
            "error"
        )

        return redirect(
            url_for("venta_productos")
        )

    finally:

        cursor.close()
        connection.close()


# ==========================================================
# COMPROBANTE DE VENTA REALIZADA
# ==========================================================

@app.route("/comprobante/<int:id_venta>")
def comprobante(id_venta):

    connection = get_connection()

    if connection is None:
        return "No se pudo conectar con la base de datos."

    cursor = connection.cursor(dictionary=True)

    try:

        # ==================================================
        # DATOS GENERALES DE LA VENTA
        # ==================================================

        query_venta = """
            SELECT
                id_venta,
                fecha_hora,
                metodo_pago,
                total

            FROM ventas_dulceria

            WHERE id_venta = %s
        """

        cursor.execute(
            query_venta,
            (id_venta,)
        )

        venta = cursor.fetchone()

        if venta is None:
            return "Venta no encontrada.", 404

        # ==================================================
        # DETALLE DE LA VENTA
        # ==================================================

        query_detalle = """
            SELECT
                d.id_venta,
                d.id_variante,
                d.cantidad,
                d.precio_unitario,
                d.subtotal,

                p.nombre AS producto,
                p.descripcion,

                c.nombre AS categoria,

                v.nombre AS variante,
                v.tamano,
                v.sabor,
                v.presentacion

            FROM detalle_venta_dulceria d

            INNER JOIN variantes_producto v
                ON d.id_variante = v.id_variante

            INNER JOIN productos p
                ON v.id_producto = p.id_producto

            INNER JOIN categorias c
                ON p.id_categoria = c.id_categoria

            WHERE d.id_venta = %s

            ORDER BY d.id_variante
        """

        cursor.execute(
            query_detalle,
            (id_venta,)
        )

        detalles = cursor.fetchall()

        # ==================================================
        # MOSTRAR COMPROBANTE
        # ==================================================

        return render_template(
            "comprobante.html",
            venta=venta,
            detalles=detalles,
            total=venta["total"],
            confirmado=True
        )

    finally:

        cursor.close()
        connection.close()


# ==========================================================
# INVENTARIO
# ==========================================================

@app.route("/inventario")
def inventario():

    connection = get_connection()

    if connection is None:
        return "No se pudo conectar con la base de datos."

    cursor = connection.cursor(dictionary=True)

    try:

        query = """
            SELECT

                i.id_inventario,

                p.id_producto,
                p.nombre AS producto,

                c.nombre AS categoria,

                v.id_variante,
                v.nombre AS variante,
                v.tamano,
                v.sabor,
                v.presentacion,
                v.precio,

                i.existencia,
                i.stock_minimo,
                i.ultima_actualizacion

            FROM inventario i

            INNER JOIN variantes_producto v
                ON i.id_variante = v.id_variante

            INNER JOIN productos p
                ON v.id_producto = p.id_producto

            INNER JOIN categorias c
                ON p.id_categoria = c.id_categoria

            WHERE p.activo = TRUE
                AND v.activo = TRUE

            ORDER BY
                i.existencia ASC
        """

        cursor.execute(query)

        inventario_data = cursor.fetchall()

        # ==================================================
        # RESUMEN
        # ==================================================

        productos_disponibles = 0
        productos_bajos = 0
        productos_agotados = 0

        for producto in inventario_data:

            existencia = producto["existencia"]
            minimo = producto["stock_minimo"]

            if existencia <= 0:
                productos_agotados += 1

            elif existencia <= minimo:
                productos_bajos += 1

            else:
                productos_disponibles += 1

        return render_template(
            "inventario.html",
            inventario=inventario_data,
            productos_disponibles=productos_disponibles,
            productos_bajos=productos_bajos,
            productos_agotados=productos_agotados
        )

    finally:

        cursor.close()
        connection.close()


# ==========================================================
# CIERRE DE CAJA
# ==========================================================

@app.route("/cierre_caja")
def cierre_caja():

    connection = get_connection()

    if connection is None:
        return "No se pudo conectar con la base de datos."

    cursor = connection.cursor(dictionary=True)

    try:

        # ==================================================
        # RESUMEN DEL DÍA
        # ==================================================

        query_resumen = """
            SELECT
                COUNT(*) AS ventas_realizadas,

                COALESCE(
                    (
                        SELECT SUM(d.cantidad)
                        FROM detalle_venta_dulceria d
                        INNER JOIN ventas_dulceria v2
                            ON d.id_venta = v2.id_venta
                        WHERE DATE(v2.fecha_hora) = CURDATE()
                    ),
                    0
                ) AS productos_vendidos,

                COALESCE(
                    SUM(total),
                    0
                ) AS total_vendido

            FROM ventas_dulceria

            WHERE DATE(fecha_hora) = CURDATE()
        """

        cursor.execute(query_resumen)

        resumen = cursor.fetchone()

        # ==================================================
        # EFECTIVO
        # ==================================================

        query_efectivo = """
            SELECT
                COUNT(*) AS ventas,

                COALESCE(
                    SUM(total),
                    0
                ) AS total

            FROM ventas_dulceria

            WHERE DATE(fecha_hora) = CURDATE()
                AND metodo_pago = 'EFECTIVO'
        """

        cursor.execute(query_efectivo)

        efectivo = cursor.fetchone()

        # ==================================================
        # TARJETA
        # ==================================================

        query_tarjeta = """
            SELECT
                COUNT(*) AS ventas,

                COALESCE(
                    SUM(total),
                    0
                ) AS total

            FROM ventas_dulceria

            WHERE DATE(fecha_hora) = CURDATE()
                AND metodo_pago = 'TARJETA'
        """

        cursor.execute(query_tarjeta)

        tarjeta = cursor.fetchone()

        # ==================================================
        # FONDO INICIAL
        # ==================================================

        fondo_inicial = Decimal("1000.00")

        ventas_efectivo = Decimal(
            str(efectivo["total"])
        )

        efectivo_esperado = (
            fondo_inicial +
            ventas_efectivo
        )

        return render_template(
            "cierre_caja.html",
            resumen=resumen,
            efectivo=efectivo,
            tarjeta=tarjeta,
            fondo_inicial=fondo_inicial,
            efectivo_esperado=efectivo_esperado
        )

    finally:

        cursor.close()
        connection.close()


# ==========================================================
# EJECUTAR SERVIDOR
# ==========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )