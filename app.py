from werkzeug.security import check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash
from functools import wraps
import sqlite3
import os
import zipfile, tempfile, os
from flask import send_file
import crea_designa
import json
import correu
from google.genai import types
from google import genai
import CDD.rellenar_cuestionario_cdd as cdd
import time
import pandas as pd
from io import BytesIO
import shutil
from Signar_autofirma.signar import *  

import eventos.eventos as eventos


import task

from threading import Event
import uuid
from datetime import datetime

app = Flask(__name__)

# Directory Configurations
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SIGNED_FOLDER = os.path.join(BASE_DIR, 'signed_files')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SIGNED_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# App Configuration
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SIGNED_FOLDER'] = SIGNED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # Max size limit: 32 MB


# Usar SQLite en lugar de MySQL
db_path = os.path.join(os.path.dirname(__file__), "miapp.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.row_factory = sqlite3.Row

control = conn.cursor().execute("select * from control").fetchone()

# Configuración de Mail (definida en correo.py)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = control['username']  # tu correo
app.config['MAIL_PASSWORD'] = control['apimail']  # tu contraseña o app password    
app.config['MAIL_DEFAULT_SENDER'] = control['email']

# Inicializar Mail y scheduler definidos en correo.py
correu.init_mail_and_scheduler(app, conn)

app.secret_key = control['appsecret']  # Cambia esto por una clave secreta segura en producción



def enviar_arxiu(buffer, save_path):
    return send_file(
        buffer,
        as_attachment=True,
        download_name=save_path,  # Ej: 'mi_documento.docx'
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        current_user = conn.cursor().execute(
            "SELECT username FROM users WHERE id = ?",
            (session.get("user_id"),)
        ).fetchone()
        if not current_user or current_user["username"] not in ["alfredo", "alviboi", "gmunoz"]:
            return jsonify({"error": "No estás autorizado"}), 403
        return f(*args, **kwargs)
    return decorated_function


def enviar_archivos_o_zip(result, default_zip_name):
    if result is None:
        return jsonify({"error": "Procesamiento falló: on_process devolvió None"}), 400
    files = list(result)
    if not files:
        return jsonify({"error": "No se generaron archivos"}), 400
    if len(files) == 1:
        buffer, path = files[0]
        return send_file(buffer, as_attachment=True, download_name=path)

    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_zip.close()
    try:
        with zipfile.ZipFile(tmp_zip.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for buffer, path in files:
                if isinstance(buffer, str) and os.path.isfile(buffer):
                    zf.write(buffer, arcname=path)
                elif isinstance(buffer, (bytes, bytearray)):
                    zf.writestr(path, buffer)
                elif hasattr(buffer, "read"):
                    try:
                        buffer.seek(0)
                    except Exception:
                        pass
                    zf.writestr(path, buffer.read())
                else:
                    zf.writestr(path, bytes(buffer))
        return send_file(tmp_zip.name, as_attachment=True, download_name=default_zip_name)
    except Exception as e:
        return jsonify({"error": f"Error al generar ZIP: {e}"}), 500


def generar_zip_de_carpeta(ruta_crea_carpeta, codigo, asesor):
    root_folder = f"{codigo}_{asesor}"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    try:
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for archivo in os.listdir(ruta_crea_carpeta):
                ruta_completa = os.path.join(ruta_crea_carpeta, archivo)
                if os.path.isfile(ruta_completa):
                    nuevo_nombre = f"{codigo}_{archivo}"
                    arcname = os.path.join(root_folder, nuevo_nombre)
                    zf.write(ruta_completa, arcname=arcname)
                else:
                    if os.path.isdir(ruta_completa):
                        if archivo.endswith("-Tec"):
                            new_dir = f"{codigo}-Tec"
                            for root, _, files in os.walk(ruta_completa):
                                for fname in files:
                                    full = os.path.join(root, fname)
                                    nuevo_nombre = f"{codigo}_{os.path.basename(fname)}"
                                    arcname = os.path.join(root_folder, new_dir, nuevo_nombre)
                                    zf.write(full, arcname=arcname)
                        else:
                            base = os.path.abspath(os.path.join(ruta_crea_carpeta))
                            for root, _, files in os.walk(ruta_completa):
                                for fname in files:
                                    full = os.path.join(root, fname)
                                    rel = os.path.relpath(full, base)
                                    arcname = os.path.join(root_folder, rel)
                                    zf.write(full, arcname=arcname)
        return send_file(tmp.name, as_attachment=True, download_name=f"{root_folder}.zip")
    except Exception as e:
        return jsonify({"error": f"Error al generar ZIP de carpeta: {e}"}), 500



@app.route("/")
def inicio():
    # Si ya está logueado, puedes mandarlo directo a /privado si quieres:
    # if session.get("logged_in"):
    #     return redirect(url_for("privado"))
    return render_template("index.html")

@app.route("/registro")
def registro():
    # Si ya está logueado, puedes mandarlo directo a /privado si quieres:
    # if session.get("logged_in"):
    #     return redirect(url_for("privado"))
    # return render_template("registro.html")
    return render_template("prohibido.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    msg = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        # Only check password if a user was found
        if user and check_password_hash(user["password"], password):
            session["logged_in"] = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["nombre"] = user["nombre"]
            session["apellidos"] = user["apellidos"]
            session["email"] = user["email"]
            return redirect(url_for("privado"))
        else:
            msg = "Usuario o contraseña incorrectos"
    return render_template("login.html", msg=msg)


@app.route("/privado")
@login_required
def privado():
    return render_template("privado.html", username=session.get("username"))



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        nombre = request.form["nombre"]
        apellidos = request.form["apellidos"]
        email = request.form["email"]

        # Generar hash seguro (por defecto usa PBKDF2 + salt)
        password = generate_password_hash(password)  # o generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

        cursor = conn.cursor()
        # Asegurarse de que la tabla users exista en SQLite
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT UNIQUE NOT NULL,
                   password TEXT NOT NULL,
                   nombre TEXT,
                   apellidos TEXT,
                   email TEXT UNIQUE
               )"""
        )
        conn.commit()
        # comprobar si usuario o email ya existen
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            msg = "Usuari o email ja registrat"
            render_template("login.html", msg=msg)
            return redirect(url_for("login"))

        cursor.execute(
            "INSERT INTO users (username, password, nombre, apellidos, email) VALUES (?, ?, ?, ?, ?)",
            (username, password, nombre, apellidos, email),
        )
        conn.commit()
        msg = "Usuari creat, ja pots iniciar sessió"
        render_template("login.html", msg=msg)
        return redirect(url_for("login"))
    return redirect(url_for("login"))

@app.route("/upload_excel", methods=["GET", "POST"])
def upload_excel():
    if request.method == "POST":
        # Aquí manejarías la subida del archivo Excel
        archivo = request.files.get("file")
        if archivo:
            pass  # Lógica para guardar el archivo

    return redirect(url_for("privado"))

@app.route("/create_folder", methods=["POST"])
@login_required
def create_folder():
    print("create_folder called")
    if request.method == "POST":
        # Aquí manejarías la creación de la carpeta
        data = request.get_json()        # dict de Python
        codigo = data.get('codigo')
        asesor = data.get('asesor')
        
        print(f"Codigo: {codigo}, Asesor: {asesor}")
        if codigo and asesor:
            return generar_zip_de_carpeta("./crea_carpeta", codigo, asesor)
    return redirect(url_for("privado"))



@app.route("/create_folder_sdgfp", methods=["POST"])
@login_required
def create_folder_sdgfp():
    print("create_folder_sdgfp called")
    if request.method == "POST":
        # Aquí manejarías la creación de la carpeta
        data = request.get_json()        # dict de Python
        codigo = data.get('codigo')
        asesor = data.get('asesor')
        
        print(f"Codigo: {codigo}, Asesor: {asesor}")
        if codigo and asesor:
            return generar_zip_de_carpeta("./crea_carpeta_sdgfp", codigo, asesor)
    return redirect(url_for("privado"))


@app.route("/excel_cdd", methods=["GET"])
@login_required
def excel_cdd():
    return send_file("CDD/Plantilla_Cuestionario_CDD.xlsx", as_attachment=True, download_name="Plantilla_Cuestionario_CDD.xlsx")

@app.route("/cdd", methods=["GET", "POST"])
@login_required
def cdd_view():
    if request.method == "POST":
        print("POST request received at /cdd")
        archivo_excel = request.files.get("file")
        print(f"Archivo recibido en /cdd: {archivo_excel.filename if archivo_excel else 'No file'}")
        if archivo_excel and archivo_excel.filename:
            try:
                # Convertir filas del Excel a la estructura esperada para cuestionarios
                if hasattr(archivo_excel, "stream"):
                    archivo_excel.stream.seek(0)
                    df = pd.read_excel(archivo_excel.stream, sheet_name=0, engine="openpyxl")
                elif isinstance(archivo_excel, (bytes, bytearray)):
                    df = pd.read_excel(BytesIO(archivo_excel), sheet_name=0, engine="openpyxl")
                elif isinstance(archivo_excel, BytesIO):
                    archivo_excel.seek(0)
                    df = pd.read_excel(archivo_excel, sheet_name=0, engine="openpyxl")
                else:
                    df = pd.read_excel(archivo_excel, sheet_name=0, engine="openpyxl")

                df.columns = df.columns.str.strip()

                datos_cuestionarios = []

                for _, row in df.iterrows():
                    datos_cuestionarios.append({
                        "codigo": "" if pd.isna(row["Código"]) else str(row["Código"]),
                        "titulo": "" if pd.isna(row["Título"]) else str(row["Título"]),
                        "horas": "" if pd.isna(row["horas"]) else str(row["horas"]),
                        "asesoria": "" if pd.isna(row["Asesoría"]) else str(row["Asesoría"]),
                        "correoelectronico": "" if pd.isna(row["Correo"]) else str(row["Correo"]),
                        "tipo": "" if pd.isna(row["Tipo"]) else str(row["Tipo"])
                })
                # print("datos_cuestionarios:", datos_cuestionarios)
                tmp_file =cdd.crear_zip_cuestionarios_directo(datos_cuestionarios)

                return send_file(tmp_file, as_attachment=True, download_name="cuestionarios_cdd.zip")

            except Exception as e:
                print(f"Error al leer el Excel: {e}")
            finally:
                if os.path.exists("cdd.zip"):
                    import time
                    for _ in range(20):
                        try:
                            os.remove("cdd.zip")  # Limpiar el ZIP temporal después de enviarlo
                            break
                        except PermissionError:
                            time.sleep(0.25)
    
    return render_template("cdd.html")


@app.route("/designes", methods=["POST"])
@login_required
def designes():
    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            datos_identificativos = crea_designa.extraer_datos_identificativos(archivo)
            print("Datos identificativos:", datos_identificativos)

            result = crea_designa.on_process(json_data, datos_identificativos, tipo="des")
            print("Result from on_process:", result)
            return enviar_archivos_o_zip(result, "designas.zip")
    return redirect(url_for("privado"))


@app.route("/designessdgfp", methods=["POST"])
@login_required
def designessdgfp():
    if request.method == "POST":
        archivo = request.files.get("file")
        campana = request.form.get("campana", "")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            datos_identificativos = crea_designa.extraer_datos_identificativos(archivo)

            result = crea_designa.on_process(json_data, datos_identificativos, tipo="dessdgfp", campana=campana)
            print("Result from on_process:", result)
            return enviar_archivos_o_zip(result, "designas.zip")
    return redirect(url_for("privado"))


@app.route("/certifica", methods=["POST"])
@login_required
def certifica():
    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            datos_identificativos = crea_designa.extraer_datos_identificativos(archivo)

            result = crea_designa.on_process(json_data, datos_identificativos, tipo="cer")
            print("Result from on_process:", result)
            return enviar_archivos_o_zip(result, "certificas.zip")
    return redirect(url_for("privado"))


@app.route("/certificasdgfp", methods=["POST"])
@login_required
def certificasdgfp():
    if request.method == "POST":
        archivo = request.files.get("file")
        campana = request.form.get("campana", "")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            datos_identificativos = crea_designa.extraer_datos_identificativos(archivo)

            result = crea_designa.on_process(json_data, datos_identificativos, tipo="cersdgfp", campana=campana)
            print("Result from on_process:", result)
            return enviar_archivos_o_zip(result, "certificas.zip")
    return redirect(url_for("privado"))


@app.route("/resolc-dgfp", methods=["POST"])
@login_required
def resolc_dgfp():
    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            personas = []
            for persona in json_data:
                if persona['Movimientos'][0]['JURÍDICO'] != "Empresa/autónomo":
                    personas.append(persona['Nombre'])
                
            return app.response_class(json.dumps({"personas": personas}, ensure_ascii=False), mimetype='application/json')
    return redirect(url_for("privado"))


@app.route("/genera-resolc", methods=["POST"])
@login_required
def genera_resolc():
    if request.method == "POST":
        archivo = request.files.get("file")

        if archivo:
            json_data = crea_designa.process_excel(archivo)
            datos_identificativos = crea_designa.extraer_datos_identificativos(archivo)
            resultados = request.form.get("resultados")
            if not resultados:
                resultados = []
            else:
                try:
                    parsed = json.loads(resultados)
                    resultados = parsed if isinstance(parsed, list) else [parsed]
                except Exception:
                    resultados = [r.strip() for r in resultados.split(",") if r.strip()]
            print(resultados)
            result = crea_designa.on_process(json_data, datos_identificativos, tipo="resolc", resultados=resultados)
            return enviar_archivos_o_zip(result, "resolc.zip")
    return redirect(url_for("privado"))


@app.route("/minuta-dgfp", methods=["POST"])
@login_required
def minuta_dgfp():
    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            identificativos = crea_designa.extraer_datos_identificativos(archivo)
            
            personas = []
            for persona in json_data:
                if persona['Movimientos'][0]['JURÍDICO'] != "Empresa/autónomo":
                    personas.append(persona)
                
            return jsonify({"personas": personas, "identificativos": identificativos})
    return redirect(url_for("privado"))


@app.route("/genera-minuta", methods=["POST"])
@login_required
def genera_minuta():
    if request.method == "POST":
        archivo = request.files.get("file")

        if archivo:
            json_data = crea_designa.process_excel(archivo)
            datos_identificativos = crea_designa.extraer_datos_identificativos(archivo)

        resultados_str = request.form.get("resultados")  # String JSON del FormData
        if not resultados_str:
            return jsonify({"error": "No resultados"}), 400
        
        try:
            resultados = json.loads(resultados_str)  # Parsea a list de dicts
        except json.JSONDecodeError as e:
            return jsonify({"error": f"JSON inválido: {e}"}), 400
        
        files = []
        for res in resultados:
            datos_recopilados = {
                "Nombre": res["persona"]["Nombre"],
                "NIF": res["persona"]["DNI"],
                "Domicili": res["valores"]["Domicili"],
                "CP": res["valores"]["CP"],
                "Población": res["valores"]["Población"],
                "Provincia": res["valores"]["Provincia"],
                "Nombre del curso": res["valores"]["Nombre del curso"],
                "Importe bruto": res["valores"]["Importe bruto"],
                "Importe neto": res["valores"]["Importe neto"],
                "IBAN": res["valores"]["IBAN"],
                "BIC": res["valores"]["BIC"],
                "Email": res["valores"]["Email"],
                "Teléfono": res["valores"]["Teléfono"],
                "Grup": res["valores"]["Grup"],
                "Nivell": res["valores"]["Nivell"],
                "Relacio_juridica": res["valores"]["Relacio_juridica"],
                "Dates_inici_final": res["valores"]["Dates_inici_final"],
            }
            
            result = crea_designa.on_process(json_data, datos_identificativos, tipo="min", minuta_datos=datos_recopilados) 
            if result is None:
                return "Procesamiento falló: on_process devolvió None", 400
            files.append(result)
            
        return enviar_archivos_o_zip(files, "minutas.zip")


# perfil
@app.route("/actualizaperfil", methods=["POST"])
@login_required
def actualizaperfil():
    cursor = conn.cursor()
    user_id = session.get("user_id")
    if request.method == "POST":
        # aceptar JSON o form-data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        nombre = data.get("nombre")
        apellidos = data.get("apellidos")
        email = data.get("email")
        password = data.get("password", "")
        api_key = data.get("api_key", "")

        # opcional: aceptar "usuario" o "username" si hace falta
        username = data.get("usuario") or data.get("username")


        if password == "":
            try:
                cursor.execute(
                    "UPDATE users SET nombre = ?, apellidos = ?, email = ?, api_key = ? WHERE id = ?",
                    (nombre, apellidos, email, api_key, user_id),
                )
                conn.commit()
            except sqlite3.IntegrityError as e:
                return f"Error actualizando perfil: {e}", 400
        else:
            password = generate_password_hash(password)
            try:
                cursor.execute(
                    "UPDATE users SET nombre = ?, apellidos = ?, email = ?, password = ?, api_key = ? WHERE id = ?",
                    (nombre, apellidos, email, password, api_key, user_id),
                )
                conn.commit()
            except sqlite3.IntegrityError as e:
                return f"Error actualizando perfil: {e}", 400
        
    return "Dades de perfil actualitzats correctament"

    

# datos perfil
@app.route("/perfil", methods=["GET"])
@login_required
def perfil():
    cursor = conn.cursor()
    user_id = session.get("user_id")

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user:
        perfil_data = {
            "usuario": user["username"],
            "nombre": user["nombre"],
            "apellidos": user["apellidos"],
            "email": user["email"],
            "api_key": user["api_key"]
        }
        return jsonify(perfil_data)
    else:
        return jsonify({"error": "Usuario no encontrado"}), 404
    

@app.route("/exceldates", methods=["POST"])
def exceldates():
    # Aquí va la lógica para manejar la subida y procesamiento del archivo Excel
    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            datos_identificativos = crea_designa.extraer_datos_identificativos(archivo)
        print("Datos identificativos:", datos_identificativos)
        resultado = {
            "codigo_edicion": datos_identificativos.get('CÓDIGO EDICIÓN / CODI EDICIÓ'),
            "titulo_accion": datos_identificativos.get('TÍTULO ACCIÓN FORMATIVA / TÍTOL ACCIÓ FORMATIVA'),
            "fecha_inicio": datos_identificativos.get('FECHAS REALIZACIÓN / DATES REALITZACIÓ', '').split(' al ')[0] if ' al ' in datos_identificativos.get('FECHAS REALIZACIÓN / DATES REALITZACIÓ', '') else '',
            "fecha_fin": datos_identificativos.get('FECHAS REALIZACIÓN / DATES REALITZACIÓ', '').split(' al ')[1] if ' al ' in datos_identificativos.get('FECHAS REALIZACIÓN / DATES REALITZACIÓ', '') else ''
        }
    return jsonify(resultado)

@app.route("/recordatoridates", methods=["POST"])
@login_required
def recordatoridates():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS formacio (
                asesoria INTEGER,
                codi_ed TEXT,
                titol TEXT,
                data_ini DATE,
                data_fin DATE,
                data_insc DATE,
                data_conf DATE,
                data_list DATE
            )"""
        )
        conn.commit()
        print(data.get("codi"), data.get("titulo"), data.get("dataInici"), data.get("dataFi"), data.get("dataInscripcio"), data.get("dataConfirmacio"), data.get("dataLlistes"))
        try:
            cursor.execute(
                """INSERT OR REPLACE INTO formacio 
                    (asesoria, codi_ed, titol, data_ini, data_fin, data_insc, data_conf, data_list)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session.get("user_id"),
                    data.get("codi"),
                    data.get("titulo"),
                    data.get("dataInici"),
                    data.get("dataFi"),
                    data.get("dataInscripcio"),
                    data.get("dataConfirmacio"),
                    data.get("dataLlistes")
                )
            )
            conn.commit()

            # CORREO QUE SE ENVÍA AL USUARIO CON LOS RECORDATORIOS DE LAS FECHAS IMPORTANTES DEL CURSO

            lista_eventos=[
                {
                    "fecha": data.get("dataInici"),
                    "titulo": f"INICIO DEL CURSO {data.get('codi')} - {data.get('titulo')}",
                    "descripcion": f"INICIO DEL CURSO {data.get('codi')} - {data.get('titulo')}",
                },
                {
                    "fecha": data.get("dataFi"), 
                    "titulo": f"FIN DEL CURSO {data.get('codi')} - {data.get('titulo')}",
                    "descripcion": f"FIN DEL CURSO {data.get('codi')} - {data.get('titulo')}",
                },
                {
                    "fecha": data.get("dataInscripcio"),
                    "titulo": f"INSCRIPCIÓN DEL CURSO {data.get('codi')} - {data.get('titulo')}",
                    "descripcion": f"Si no ho has modificat en la APP demà comença la inscripció del curs: INSCRIPCIÓN DEL CURSO {data.get('codi')} - {data.get('titulo')}.",
                },
                {
                    "fecha": data.get("dataConfirmacio"),
                    "titulo": f"CONFIRMACIÓN DEL CURSO {data.get('codi')} - {data.get('titulo')}",
                    "descripcion": f"Si no ho has modificat en la APP demà comença la fase de confirmació del curs {data.get('codi')} - {data.get('titulo')}. Per tant cal que vages fent la llista de baremacions. Recorda que tens un correu model a https://cefirefp.github.io/docs/gestioformacions/preparar/#fase-de-confirmacio, Gesform et permet enviar un correu de manera automàtica.",
                },
                {
                    "fecha": data.get("dataLlistes"),
                    "titulo": f"LISTAS DEL CURSO {data.get('codi')} - {data.get('titulo')}",
                    "descripcion": f"Si no ho has modificat en la APP demà comença la fase de llistes del curs {data.get('codi')} - {data.get('titulo')}. Recorda que has d'importar els participants a Gesform i enviar les llistes de participants a la DGFP. Recorda que tens un correu model a https://cefirefp.github.io/docs/gestioformacions/preparar/#publicacio-del-llistat-definitiu, Gesform NO envia un correu de manera automàtica, per tant cal que envies tú el correu.",
                }
            ]


            destinatario = cursor.execute("SELECT email FROM users WHERE id = ?", (session.get("user_id"),)).fetchone()["email"]

            print("Destinatario del correo:", destinatario)

            correu.add_calendar_multiples(app, destinatario, lista_eventos)





            return jsonify({"success": True, "message": "Recordatori guardat"}), 200
        except sqlite3.Error as e:
            return jsonify({"error": str(e)}), 400
        
# FALTA CREAR EL PROMPT PER A RESOLDRE LA RESPOSTA

@app.route("/comprovaperfil", methods=["POST"])
@login_required
def comprovaperfil():
    perfil = request.json.get("perfil")
    if not perfil:
        return jsonify({"error": "Falten dades en JSON"}), 400
    
    prompt = f"Actúa com un expert lingüista en valencià normatiu (AVL) i castellà normatiu. En el següent json tens perfils en valencià i en castellà: {perfil}\n\n. Vull que revises el text i fes que complixca els requisits lingüístics següents:\n- El text ha d'estar en valencià normatiu de la Generalitat Valenciana AVL (desenrotllar enlloc desenvolupar, desenrotllament enlloc de desenvolupament, servici enlloc servei, este enlloc d'aquest, i totes les formes derivades...) o en castellà normatiu segons cada text, sinó paraules en altres llengües. Aquells termes que traduixques de l'anglès tant en castellà como en valencià em poses després entre parèntesis el terme en anglès, però només si en el text original estan en anglès.\n- El text ha de ser formal i adequat per a un perfil professional.\n- El text ha de ser clar, concís i ben estructurat.\n\nRevisa el text i torna'm només el text corregit complint els requisits, sense cap explicació addicional ni comentaris. M'has de tornar el text amb un JSON així: {{\"perfil\": {{ \"objetivos_val\": \"Ací la resposta\", \"objetivos_cas\": \"Ací la resposta\", \"contenidos_val\": \"Ací la resposta\", \"contenidos_cas\": \"Ací la resposta\"}}}}, però amb les respostes del perfil corregit segons els requisits lingüístics indicats, a més cal que siguen equivalents en la corresponent llengüa en el castellà i el valencià. No has de canviar res més del JSON, és necessari que siga eixe format de JSON inamovible, només el text del perfil per a complir els requisits. Si el text ja compleix els requisits, torna'm el mateix text sinó canvis. Només vull el JSON pur com a resposta i és important que tingues en compte les indiciacions lingüistiques que t'he donat."

    GOOGLE_AI_KEY = conn.cursor().execute("SELECT api_key FROM users WHERE id = ?", (session.get("user_id"),)).fetchone()["api_key"]
    
    if not GOOGLE_AI_KEY:
        return jsonify({"error": "No tens la API key configurada"}), 400
    


    task_id = str(uuid.uuid4())
    task.tareas[task_id] = {"event": Event(), "result": None, "status": "waiting"}
    
    task.procesar_ai_async(task_id, prompt, GOOGLE_AI_KEY)
    
    if task.tareas[task_id]["event"].wait(timeout=120):
        result = task.tareas[task_id]["result"]
        del task.tareas[task_id]  # Limpia memoria
        return jsonify(result)
    else:
        del task.tareas[task_id]
        return jsonify({"error": "Timeout (120s)"}), 408

@app.route("/imatgedates", methods=["POST"])
@login_required
def imatgedates():
    if request.method == "POST":
        archivo = request.files.get("file")

        if archivo:
            GOOGLE_AI_KEY = conn.cursor().execute("SELECT api_key FROM users WHERE id = ?", (session.get("user_id"),)).fetchone()["api_key"]
            if not GOOGLE_AI_KEY:
                return jsonify({"error": "No tens la API key configurada"}), 400

            client = genai.Client(api_key=GOOGLE_AI_KEY)

            image_bytes = archivo.read()
            response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type='image/png',
            ),
            'Saca los datos que te pido de esta imagen en un json. Con este ejemplo de formato: {"titulo": "", "codi": "", "fecha_inicio": "", "fecha_fin": "", "inicio": "", "fin": "", "confirmacion": ""}. Ten en cuenta que cuando digo codi me refiero a la referencia, que empieza siempre por 26FP... Devuelve solamente los datos en el formato JSON que te he dicho, sin explicaciones ni texto adicional.'
            ]
            )
        resp_text = response.text.replace("```json", "").replace("```", "")

        print(response.text)
        return jsonify(resp_text)
    


@app.route("/usuaris", methods=["GET"])
@admin_required
def usuaris():
    rows = conn.cursor().execute(
        "SELECT id, username, nombre, apellidos, email, api_key FROM users ORDER BY id"
    ).fetchall()
    usuarios = [dict(row) for row in rows]
    return jsonify(usuarios)

@app.route("/usuaris/update", methods=["POST"])
@admin_required
def usuaris_update():
    data = request.get_json()
    if not data or not data.get("id"):
        return jsonify({"error": "Falta ID"}), 400

    try:
        conn.execute(
            """
            UPDATE users
            SET username=?, nombre=?, apellidos=?, email=?
            WHERE id=?
            """,
            (
                data.get("username"),
                data.get("nombre"),
                data.get("apellidos"),
                data.get("email"),
                data["id"],
            ),
        )
        conn.commit()
        # Devolver el usuario actualizado
        row = conn.execute(
            "SELECT id, username, nombre, apellidos, email, api_key FROM users WHERE id=?",
            (data["id"],),
        ).fetchone()
        return jsonify(dict(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/usuaris/delete", methods=["POST"])
@admin_required
def usuaris_delete():
    user_id = request.args.get("id")
    if not user_id:
        return jsonify({"error": "Falta ID"}), 400

    try:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ==========================================================================
# Flask Routes SIGNAR AUTOFIRMA
# ==========================================================================

@app.route('/')
def index():
    """Render the main client dashboard."""
    return render_template('index.html')

@app.route('/upload_excel_signar', methods=['POST'])
def upload_excel_signar():
    """
    Accepts the uploaded plantilla.xlsx file, parses it using pandas,
    generates a beautifully formatted PDF certificate for each row,
    and returns their Base64 encodings to the frontend queue.
    """
    if 'file' not in request.files or 'batch_id' not in request.form:
        return jsonify({'success': False, 'error': 'Parámetros incompletos.'}), 400
        
    file = request.files['file']
    batch_id = request.form['batch_id']
    
    # Secure batch_id to prevent directory traversal
    batch_id = os.path.basename(batch_id)
    if not batch_id or batch_id == '..':
        return jsonify({'success': False, 'error': 'Identificador de lote no válido.'}), 400
        
    if file.filename == '':
        return jsonify({'success': False, 'error': 'El nombre del archivo está vacío.'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Tipo de archivo no permitido. Solo se aceptan archivos Excel (.xlsx).'}), 400

    try:
        # Create unique directory for this batch upload
        batch_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], batch_id)
        os.makedirs(batch_upload_dir, exist_ok=True)
        
        # Save Excel file
        excel_path = os.path.join(batch_upload_dir, "plantilla_procesada.xlsx")
        file.save(excel_path)
        
        # Load and parse Excel
        df = pd.read_excel(excel_path)
        df = df.fillna('')  # Replace all NaNs with empty strings safely
        
        # Check required columns
        required_cols = [
            'nombre y apellidos', 'dni', 'nombre del curso', 'nombre del asesor',
            'lugar de realización', 'hora inicio', 'hora final', 'fecha de asistencia'
        ]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return jsonify({
                'success': False,
                'error': f"La plantilla Excel no contiene las columnas necesarias. Faltan: {', '.join(missing_cols)}"
            }), 400
            
        generated_files = []
        
        # Generate PDF for each attendee row
        for idx, row in df.iterrows():
            raw_name = str(row.get('nombre y apellidos', f"justificante_{idx}")).strip()
            if not raw_name:
                continue  # skip empty rows
                
            # Clean name for safe filename
            clean_name = "".join(c for c in raw_name if c.isalnum() or c in (' ', '_', '-')).strip()
            clean_name = clean_name.replace(' ', '_')
            original_pdf_name = f"justificante_{clean_name}.pdf"
            
            # Generate a secure prefix
            unique_filename = f"{uuid.uuid4().hex}_{original_pdf_name}"
            pdf_path = os.path.join(batch_upload_dir, unique_filename)
            
            # Generate the PDF
            generate_pdf_from_row(row, pdf_path)
            
            # Convert PDF to Base64
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
                pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                
            generated_files.append({
                'original_filename': original_pdf_name,
                'filename': unique_filename,
                'pdf_base64': pdf_base64
            })
            
        if not generated_files:
            return jsonify({'success': False, 'error': 'No se encontraron registros válidos para generar justificantes.'}), 400
            
        return jsonify({
            'success': True,
            'files': generated_files
        })
        
    except Exception as e:
        app.logger.error(f"Error parsing Excel & generating PDFs: {str(e)}")
        return jsonify({'success': False, 'error': f"Error al procesar el archivo Excel: {str(e)}"}), 500

@app.route('/save_signed', methods=['POST'])
def save_signed():
    """
    Accepts a Base64-encoded signed PDF and a batch_id,
    decodes it, and saves it in the batch signed folder.
    """
    data = request.get_json()
    if not data or 'filename' not in data or 'signed_base64' not in data or 'batch_id' not in data:
        return jsonify({'success': False, 'error': 'Parámetros incompletos.'}), 400
        
    filename = os.path.basename(data['filename'])
    batch_id = os.path.basename(data['batch_id'])
    signed_base64 = data['signed_base64']
    
    if not batch_id or batch_id == '..':
         return jsonify({'success': False, 'error': 'Identificador de lote no válido.'}), 400
         
    if ',' in signed_base64:
        signed_base64 = signed_base64.split(',', 1)[1]
        
    try:
        signed_bytes = base64.b64decode(signed_base64)
        
        # Ensure batch directory exists inside signed_files
        batch_signed_dir = os.path.join(app.config['SIGNED_FOLDER'], batch_id)
        os.makedirs(batch_signed_dir, exist_ok=True)
        
        signed_filename = f"firmado_{filename}"
        signed_path = os.path.join(batch_signed_dir, signed_filename)
        
        # Write to disk
        with open(signed_path, "wb") as f:
            f.write(signed_bytes)
            
        return jsonify({
            'success': True,
            'filename': signed_filename
        })
        
    except Exception as e:
        app.logger.error(f"Error saving signed PDF: {str(e)}")
        return jsonify({'success': False, 'error': f"Error al guardar el archivo firmado: {str(e)}"}), 500

@app.route('/download_batch/<batch_id>', methods=['GET'])
def download_batch(batch_id):
    """
    Packages all signed PDF documents in the specified batch into a single ZIP file,
    deletes all uploaded/signed directories from disk to ensure zero persistence,
    and returns the ZIP file in-memory for download.
    """
    batch_id = os.path.basename(batch_id)
    if not batch_id or batch_id == '..':
        return "Lote no válido", 400

    batch_signed_dir = os.path.join(app.config['SIGNED_FOLDER'], batch_id)
    batch_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], batch_id)

    if not os.path.exists(batch_signed_dir):
        return "El lote de firmas no existe, ha expirado o ya ha sido descargado.", 404

    try:
        # 1. Read all signed PDFs from disk into memory
        files_to_zip = []
        for filename in os.listdir(batch_signed_dir):
            file_path = os.path.join(batch_signed_dir, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'rb') as f:
                    # Clean up unique secure prefix from the zip entries
                    # signed filename has format: firmado_<uuid>_justificante_<cleanName>.pdf
                    clean_name = filename
                    parts = filename.split('_', 2)
                    if len(parts) >= 3 and len(parts[1]) == 32:
                        clean_name = f"firmado_{parts[2]}"
                    files_to_zip.append((clean_name, f.read()))

        # 2. PHYSICALLY DELETE ALL DIRECTORIES ON SERVER DISK IMMEDIATELY
        # This completely guarantees no user documents remain on the server!
        shutil.rmtree(batch_signed_dir, ignore_errors=True)
        shutil.rmtree(batch_upload_dir, ignore_errors=True)

        # If there are no files signed in this batch, return error
        if not files_to_zip:
            return "No se encontraron archivos firmados en este lote.", 400

        # 3. CONSTRUCT ZIP FILE ENTIRELY IN-MEMORY
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for fname, fbytes in files_to_zip:
                zipf.writestr(fname, fbytes)
        
        # Seek stream back to start
        memory_file.seek(0)

        # 4. Stream ZIP file directly to the client
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='justificantes_firmados.zip'
        )

    except Exception as e:
        app.logger.error(f"Error packing batch {batch_id} to ZIP: {str(e)}")
        # Attempt emergency clean up
        shutil.rmtree(batch_signed_dir, ignore_errors=True)
        shutil.rmtree(batch_upload_dir, ignore_errors=True)
        return f"Error al generar el archivo comprimido: {str(e)}", 500