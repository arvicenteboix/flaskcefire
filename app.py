from werkzeug.security import check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash
import sqlite3
import os
import zipfile, tempfile, os
from flask import send_file
import crea_designa
import json
import correu

import task

from threading import Event
import uuid
from datetime import datetime

app = Flask(__name__)

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
    return render_template("registro.html")

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
def privado():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
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
def create_folder():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    print("create_folder called")
    if request.method == "POST":
        # Aquí manejarías la creación de la carpeta
        data = request.get_json()        # dict de Python
        codigo = data.get('codigo')
        asesor = data.get('asesor')
        
        print(f"Codigo: {codigo}, Asesor: {asesor}")
        if codigo and asesor:
            repo_dir = os.path.dirname(__file__)
            root_folder = f"{codigo}_{asesor}"

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            print(f"Creating zip file at: {tmp.name}")
            tmp.close()
            try:
                with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Aquí agregarías los archivos a la carpeta zip
                    # Por ejemplo, creando archivos de texto de ejemplo
                    for archivo in os.listdir("./crea_carpeta"):
                        ruta_completa = os.path.join("./crea_carpeta", archivo)
                        if os.path.isfile(ruta_completa):
                            nuevo_nombre = f"{codigo}_{archivo}"  # Prefijo + nombre original
                            arcname = os.path.join(root_folder, nuevo_nombre)
                            zf.write(ruta_completa, arcname=arcname)
                        else:
                            # si es un directorio, manejar su contenido
                            if os.path.isdir(ruta_completa):
                                # Carpeta que termina en "-Tec": renombrar carpeta a "{codigo}-Tec"
                                # y prefixar todos los archivos con "codigo_"
                                if archivo.endswith("-Tec"):
                                    new_dir = f"{codigo}-Tec"
                                    for root, _, files in os.walk(ruta_completa):
                                        for fname in files:
                                            full = os.path.join(root, fname)
                                            # usar solo el nombre del archivo (sin subcarpetas internas) para el prefijo
                                            nuevo_nombre = f"{codigo}_{os.path.basename(fname)}"
                                            arcname = os.path.join(root_folder, new_dir, nuevo_nombre)
                                            zf.write(full, arcname=arcname)
                                else:
                                    # Otras carpetas: conservar estructura dentro de root_folder
                                    base = os.path.abspath(os.path.join("./crea_carpeta"))
                                    for root, _, files in os.walk(ruta_completa):
                                        for fname in files:
                                            full = os.path.join(root, fname)
                                            rel = os.path.relpath(full, base)  # incluye el nombre de la carpeta original
                                            arcname = os.path.join(root_folder, rel)
                                            zf.write(full, arcname=arcname)

                    #zf.writestr(f"{root_folder}/info.txt", f"Código: {codigo}\nAsesor: {asesor}\n")
                    #zf.writestr(f"{root_folder}/readme.txt", "Esta es una carpeta creada automáticamente.\n")
                    print(f"Zip file {tmp.name} created successfully.")              
                try:
                    return send_file(tmp.name, as_attachment=True, download_name=f"{root_folder}.zip")
                except TypeError:
                    return send_file(tmp.name, as_attachment=True, attachment_filename=f"{root_folder}.zip")
            finally:
                # don't remove immediately to allow send_file to read it; optional cleanup could be added later
                pass
            # Lógica para crear la carpeta
            
            pass
    return redirect(url_for("privado"))



@app.route("/create_folder_sdgfp", methods=["POST"])
def create_folder_sdgfp():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    print("create_folder_sdgfp called")
    if request.method == "POST":
        # Aquí manejarías la creación de la carpeta
        data = request.get_json()        # dict de Python
        codigo = data.get('codigo')
        asesor = data.get('asesor')
        
        print(f"Codigo: {codigo}, Asesor: {asesor}")
        if codigo and asesor:
            repo_dir = os.path.dirname(__file__)
            root_folder = f"{codigo}_{asesor}"

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            print(f"Creating zip file at: {tmp.name}")
            tmp.close()
            try:
                with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Aquí agregarías los archivos a la carpeta zip
                    # Por ejemplo, creando archivos de texto de ejemplo
                    for archivo in os.listdir("./crea_carpeta_sdgfp"):
                        ruta_completa = os.path.join("./crea_carpeta_sdgfp", archivo)
                        if os.path.isfile(ruta_completa):
                            nuevo_nombre = f"{codigo}_{archivo}"  # Prefijo + nombre original
                            arcname = os.path.join(root_folder, nuevo_nombre)
                            zf.write(ruta_completa, arcname=arcname)
                        else:
                            # si es un directorio, manejar su contenido
                            if os.path.isdir(ruta_completa):
                                # Carpeta que termina en "-Tec": renombrar carpeta a "{codigo}-Tec"
                                # y prefixar todos los archivos con "codigo_"
                                if archivo.endswith("-Tec"):
                                    new_dir = f"{codigo}-Tec"
                                    for root, _, files in os.walk(ruta_completa):
                                        for fname in files:
                                            full = os.path.join(root, fname)
                                            # usar solo el nombre del archivo (sin subcarpetas internas) para el prefijo
                                            nuevo_nombre = f"{codigo}_{os.path.basename(fname)}"
                                            arcname = os.path.join(root_folder, new_dir, nuevo_nombre)
                                            zf.write(full, arcname=arcname)
                                else:
                                    # Otras carpetas: conservar estructura dentro de root_folder
                                    base = os.path.abspath(os.path.join("./crea_carpeta_sdgfp"))
                                    for root, _, files in os.walk(ruta_completa):
                                        for fname in files:
                                            full = os.path.join(root, fname)
                                            rel = os.path.relpath(full, base)  # incluye el nombre de la carpeta original
                                            arcname = os.path.join(root_folder, rel)
                                            zf.write(full, arcname=arcname)

                    #zf.writestr(f"{root_folder}/info.txt", f"Código: {codigo}\nAsesor: {asesor}\n")
                    #zf.writestr(f"{root_folder}/readme.txt", "Esta es una carpeta creada automáticamente.\n")
                    print(f"Zip file {tmp.name} created successfully.")              
                try:
                    return send_file(tmp.name, as_attachment=True, download_name=f"{root_folder}.zip")
                except TypeError:
                    return send_file(tmp.name, as_attachment=True, attachment_filename=f"{root_folder}.zip")
            finally:
                # don't remove immediately to allow send_file to read it; optional cleanup could be added later
                pass
            # Lógica para crear la carpeta
            
            pass
    return redirect(url_for("privado"))


@app.route("/designes", methods=["POST"])
def designes():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            datos_identificativos = crea_designa.extraer_datos_identificativos(archivo)
            # print("Datos identificativos:", datos_identificativos)
            # buffer, path = crea_designa.on_process(json_data, datos_identificativos, tipo="des")

            result = crea_designa.on_process(json_data, datos_identificativos, tipo="des")
            print("Result from on_process:", result)
            
            if result is None:
                return jsonify({"error": "Procesamiento falló: on_process devolvió None"}), 400
            # Manejar múltiples archivos devueltos por on_process: crear un ZIP y devolverlo
            files = list(result)
            if len(files) == 1:
                buffer, path = files[0]
                return send_file(buffer, as_attachment=True, download_name=path)

            tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            tmp_zip.close()
            try:
                with zipfile.ZipFile(tmp_zip.name, "w", zipfile.ZIP_DEFLATED) as zf:
                    for buffer, path in files:
                        # si buffer es una ruta en disco
                        if isinstance(buffer, str) and os.path.isfile(buffer):
                            zf.write(buffer, arcname=path)
                        # si buffer es bytes/bytearray
                        elif isinstance(buffer, (bytes, bytearray)):
                            zf.writestr(path, buffer)
                        # si buffer es file-like
                        elif hasattr(buffer, "read"):
                            try:
                                buffer.seek(0)
                            except Exception:
                                pass
                            zf.writestr(path, buffer.read())
                        else:
                            # intentar serializar a bytes como fallback
                            zf.writestr(path, bytes(buffer))
                try:
                    return send_file(tmp_zip.name, as_attachment=True, download_name="designas.zip")
                except TypeError:
                    return send_file(tmp_zip.name, as_attachment=True, attachment_filename="designas.zip")
            finally:
                # opcional: limpiar el zip tras enviarlo si se desea (no lo hacemos inmediatamente para permitir send_file)
                pass
            # return enviar_arxiu(buffer, path)
            # enviar_arxiu(buffer, path)
    return redirect(url_for("privado"))

# DESIGNES SDGFP 

@app.route("/designessdgfp", methods=["POST"])
def designessdgfp():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            datos_identificativos = crea_designa.extraer_datos_identificativos(archivo)
            # print("Datos identificativos:", datos_identificativos)
            # buffer, path = crea_designa.on_process(json_data, datos_identificativos, tipo="des")

            result = crea_designa.on_process(json_data, datos_identificativos, tipo="dessdgfp")
            print("Result from on_process:", result)
            
            if result is None:
                return jsonify({"error": "Procesamiento falló: on_process devolvió None"}), 400
            # Manejar múltiples archivos devueltos por on_process: crear un ZIP y devolverlo
            files = list(result)
            if len(files) == 1:
                buffer, path = files[0]
                return send_file(buffer, as_attachment=True, download_name=path)

            tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            tmp_zip.close()
            try:
                with zipfile.ZipFile(tmp_zip.name, "w", zipfile.ZIP_DEFLATED) as zf:
                    for buffer, path in files:
                        # si buffer es una ruta en disco
                        if isinstance(buffer, str) and os.path.isfile(buffer):
                            zf.write(buffer, arcname=path)
                        # si buffer es bytes/bytearray
                        elif isinstance(buffer, (bytes, bytearray)):
                            zf.writestr(path, buffer)
                        # si buffer es file-like
                        elif hasattr(buffer, "read"):
                            try:
                                buffer.seek(0)
                            except Exception:
                                pass
                            zf.writestr(path, buffer.read())
                        else:
                            # intentar serializar a bytes como fallback
                            zf.writestr(path, bytes(buffer))
                try:
                    return send_file(tmp_zip.name, as_attachment=True, download_name="designas.zip")
                except TypeError:
                    return send_file(tmp_zip.name, as_attachment=True, attachment_filename="designas.zip")
            finally:
                # opcional: limpiar el zip tras enviarlo si se desea (no lo hacemos inmediatamente para permitir send_file)
                pass
            # return enviar_arxiu(buffer, path)
            # enviar_arxiu(buffer, path)
    return redirect(url_for("privado"))




# CERTIFICA

@app.route("/certifica", methods=["POST"])
def certifica():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            datos_identificativos = crea_designa.extraer_datos_identificativos(archivo)
            # print("Datos identificativos:", datos_identificativos)
            # buffer, path = crea_designa.on_process(json_data, datos_identificativos, tipo="des")

            result = crea_designa.on_process(json_data, datos_identificativos, tipo="cer")
            print("Result from on_process:", result)
            
            if result is None:
                return jsonify({"error": "Procesamiento falló: on_process devolvió None"}), 400
            files = list(result)
            if len(files) == 1:
                buffer, path = files[0]
                return send_file(buffer, as_attachment=True, download_name=path)

            tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            tmp_zip.close()
            try:
                with zipfile.ZipFile(tmp_zip.name, "w", zipfile.ZIP_DEFLATED) as zf:
                    for buffer, path in files:
                        # si buffer es una ruta en disco
                        if isinstance(buffer, str) and os.path.isfile(buffer):
                            zf.write(buffer, arcname=path)
                        # si buffer es bytes/bytearray
                        elif isinstance(buffer, (bytes, bytearray)):
                            zf.writestr(path, buffer)
                        # si buffer es file-like
                        elif hasattr(buffer, "read"):
                            try:
                                buffer.seek(0)
                            except Exception:
                                pass
                            zf.writestr(path, buffer.read())
                        else:
                            # intentar serializar a bytes como fallback
                            zf.writestr(path, bytes(buffer))
                try:
                    return send_file(tmp_zip.name, as_attachment=True, download_name="certificas.zip")
                except TypeError:
                    return send_file(tmp_zip.name, as_attachment=True, attachment_filename="certificas.zip")
            finally:
                # opcional: limpiar el zip tras enviarlo si se desea (no lo hacemos inmediatamente para permitir send_file)
                pass
            # return enviar_arxiu(buffer, path)
            # enviar_arxiu(buffer, path)
            # return enviar_arxiu(buffer, path)
            # enviar_arxiu(buffer, path)
    return redirect(url_for("privado"))

# CERTIFICA SDGFP

@app.route("/certificasdgfp", methods=["POST"])
def certificasdgfp():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            datos_identificativos = crea_designa.extraer_datos_identificativos(archivo)

            result = crea_designa.on_process(json_data, datos_identificativos, tipo="cersdgfp")
            print("Result from on_process:", result)
            
            if result is None:
                return jsonify({"error": "Procesamiento falló: on_process devolvió None"}), 400
            files = list(result)
            if len(files) == 1:
                buffer, path = files[0]
                return send_file(buffer, as_attachment=True, download_name=path)

            tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            tmp_zip.close()
            try:
                with zipfile.ZipFile(tmp_zip.name, "w", zipfile.ZIP_DEFLATED) as zf:
                    for buffer, path in files:
                        # si buffer es una ruta en disco
                        if isinstance(buffer, str) and os.path.isfile(buffer):
                            zf.write(buffer, arcname=path)
                        # si buffer es bytes/bytearray
                        elif isinstance(buffer, (bytes, bytearray)):
                            zf.writestr(path, buffer)
                        # si buffer es file-like
                        elif hasattr(buffer, "read"):
                            try:
                                buffer.seek(0)
                            except Exception:
                                pass
                            zf.writestr(path, buffer.read())
                        else:
                            # intentar serializar a bytes como fallback
                            zf.writestr(path, bytes(buffer))
                try:
                    return send_file(tmp_zip.name, as_attachment=True, download_name="certificas.zip")
                except TypeError:
                    return send_file(tmp_zip.name, as_attachment=True, attachment_filename="certificas.zip")
            finally:
                pass
    return redirect(url_for("privado"))




@app.route("/resolc-dgfp", methods=["POST"])
def resolc_dgfp():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            personas = []
            for persona in json_data:

                # print("Procesando persona para resolución DGFP:", persona)
                if persona['Movimientos'][0]['JURÍDICO'] != "Empresa/autónomo":
                    personas.append(persona['Nombre'])
                
            return app.response_class(json.dumps({"personas": personas}, ensure_ascii=False), mimetype='application/json')

        

            # return enviar_arxiu(buffer, path)
            # enviar_arxiu(buffer, path)
    return redirect(url_for("privado"))

@app.route("/genera-resolc", methods=["POST"])
def genera_resolc():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
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
            if result is None:
                return jsonify({"error": "Procesamiento falló: on_process devolvió None"}), 400
            # { p, fecha, centro, cargo }
            files = list(result)
            if len(files) == 1:
                buffer, path = files[0]
                return send_file(buffer, as_attachment=True, download_name=path)

            tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            tmp_zip.close()
            try:
                with zipfile.ZipFile(tmp_zip.name, "w", zipfile.ZIP_DEFLATED) as zf:
                    for buffer, path in files:
                        # si buffer es una ruta en disco
                        if isinstance(buffer, str) and os.path.isfile(buffer):
                            zf.write(buffer, arcname=path)
                        # si buffer es bytes/bytearray
                        elif isinstance(buffer, (bytes, bytearray)):
                            zf.writestr(path, buffer)
                        # si buffer es file-like
                        elif hasattr(buffer, "read"):
                            try:
                                buffer.seek(0)
                            except Exception:
                                pass
                            zf.writestr(path, buffer.read())
                        else:
                            # intentar serializar a bytes como fallback
                            zf.writestr(path, bytes(buffer))
                try:
                    return send_file(tmp_zip.name, as_attachment=True, download_name="resolc.zip")
                except TypeError:
                    return send_file(tmp_zip.name, as_attachment=True, attachment_filename="resolc.zip")
            finally:
                # opcional: limpiar el zip tras enviarlo si se desea (no lo hacemos inmediatamente para permitir send_file)
                pass

            # return enviar_arxiu(buffer, path)
            # enviar_arxiu(buffer, path)
    return redirect(url_for("privado"))


@app.route("/minuta-dgfp", methods=["POST"])
def minuta_dgfp():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            json_data = crea_designa.process_excel(archivo)
            identificativos = crea_designa.extraer_datos_identificativos(archivo)
            
            personas = []
            # personas se almacenará como lista de diccionarios y se devolverá como JSON usando jsonify
            for persona in json_data:

                # print("Procesando persona para resolución DGFP:", persona)
                if persona['Movimientos'][0]['JURÍDICO'] != "Empresa/autónomo":
                    personas.append(persona)
                
                

            return jsonify({"personas": personas, "identificativos": identificativos})

        

            # return enviar_arxiu(buffer, path)
            # enviar_arxiu(buffer, path)
    return redirect(url_for("privado"))

@app.route("/genera-minuta", methods=["POST"])
def genera_minuta():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
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
                "Nombre": res["persona"]["Nombre"],  # Directo, sin .get()
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
            try:
                return send_file(tmp_zip.name, as_attachment=True, download_name="minutas.zip")
            except TypeError:
                return send_file(tmp_zip.name, as_attachment=True, attachment_filename="minutas.zip")
        finally:
            pass


# perfil
@app.route("/actualizaperfil", methods=["POST"])
def actualizaperfil():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
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
def perfil():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
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
def recordatoridates():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
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
            return jsonify({"success": True, "message": "Recordatori guardat"}), 200
        except sqlite3.Error as e:
            return jsonify({"error": str(e)}), 400
        
# FALTA CREAR EL PROMPT PER A RESOLDRE LA RESPOSTA

@app.route("/comprovaperfil", methods=["POST"])
def comprovaperfil():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    perfil = request.json.get("perfil")
    if not perfil:
        return jsonify({"error": "Falten dades en JSON"}), 400
    
    prompt = f"En el següent json tens perfils en valencià i en castellà: {perfil}\n\n. Vull que revises el text i fes complixca els requisits lingüístics següents:\n- El text ha d'estar en valencià normatiu de la Generalitat Valenciana AVL (desenrotllar enlloc desenvolupar, desenrotllament enlloc de desenvolupament, servici enlloc servei, este enlloc d'aquest, i totes les formes derivades...) o en castellà normatiu segons cada text, sense paraules en altres llengües. Aquells termes que traduixques tant en castellà com en valencià em poses després entre parèntesis el terme en anglès.\n- El text ha de ser formal i adequat per a un perfil professional.\n- El text ha de ser clar, concís i ben estructurat.\n\nRevisa el text i torna'm només el text corregit complint els requisits, sense cap explicació addicional ni comentaris. M'has de tornar el text amb amb un JSON així: {{\"perfil\": {{ \"objetivos_val\": \"Ací la resposta\", \"objetivos_cas\": \"Ací la resposta\", \"contenidos_val\": \"Ací la resposta\"}}}}, però amb les respostes del perfil corregit segons els requisits lingüístics indicats. No has de canviar res més del JSON, és necessari que siga eixe format de JSON inamovible, només el text del perfil per a complir els requisits. Si el text ja compleix els requisits, torna'm el mateix text sense canvis. Només vull el JSON pur com a resposta i és important que tingues en compte les indiciacions lingüistiques que t'he donat."
   


    prompt2 = """Actua com un expert lingüista en valencià normatiu (AVL) i castellà normatiu. Tens aquest JSON amb perfils professionals:

    {perfil}

    Tasca: Revisa cada secció del JSON i assegura't que compleix aquests requisits estrictes:

    ## REQUISITS LINGÜÍSTICS OBLIGATORIS

    ### 1. VALENCIÀ NORMATIU (Generalitat Valenciana)
    - desenrotllar (NO desenvolupar)
    - desenrotllament (NO desenvolupament) 
    - servici (NO servei)
    - este (NO aquest)
    - totes les formes derivades: desenrotlla, desenrotllaments, servicis, estes...
    - Verbs: col·locar (NO colocar), enxaneta, etc.
    - Ortografia AVL: llengua, València, atenció, etc.

    ### 2. CASTELLÀ NORMATIU (RAE)
    - Ortografia RAE estàndard

    ### 3. REQUISITS GENERAL
    - NOMÉS valencià o castellà segons la secció
    - Termes tècnics: traduïu + (anglès) ex: "intel·ligència artificial (artificial intelligence)"
    - Formalitat professional absoluta
    - Clar, concís, estructurat (1-2 frases per idea)

    ## RESPOSTA OBLIGATÒRIA
    Torna **NOMÉS** aquest JSON exacte, sense explicacions:

    ```json
    {{"perfil": {{ 
    "objetivos_val": "TEXT CORREGIT VALENCIÀ", 
    "objetivos_cas": "TEXT CORREGIT CASTELLÀ", 
    "contenidos_val": "TEXT CORREGIT VALENCIÀ",
    "contenidos_cas": "TEXT CORREGIT CASTELLÀ"
    }}}}
    ```

    ✅ Si ja compleix els requisits: copia text original  
    ❌ Si té errors: corregeix només segons requisits  
    ⚠️  NUNCA canvies l'estructura JSON ni afegeixes text extra

    **Exemple de correcció necessària:**
    ```
    Entrada: "desenvolupar web service"
    Sortida valencià: "desenrotllar servici web (web service)"
    ```

    RESPONS NOMÉS EL JSON VALIDAT. No has de canviar res més del JSON, és necessari que siga eixe format de JSON inamovible, només el text del perfil per a complir els requisits. Si el text ja compleix els requisits, torna'm el mateix text sense canvis. Només vull el JSON pur com a resposta i és important que tingues en compte les indiciacions lingüistiques que t'he donat."""


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
