from werkzeug.security import check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash
import sqlite3
import os
import zipfile, tempfile, os
from flask import send_file
import crea_designa
import json


app = Flask(__name__)

app.secret_key = "dgfp123"

# Usar SQLite en lugar de MySQL
db_path = os.path.join(os.path.dirname(__file__), "miapp.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.row_factory = sqlite3.Row

def enviar_arxiu(buffer, save_path):
    return send_file(
        buffer,
        as_attachment=True,
        download_name=save_path,  # Ej: 'mi_documento.docx'
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


@app.route("/datosusr")
def datosusr():
    if session.get("logged_in"):
            return f"Usuario: {session.get('username')}, ID: {session.get('user_id'), Nombre: {session.get('nombre')}, Apellidos: {session.get('apellidos')}}"
    else:
        return "No estás logueado"



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
            return render_template("login.html", msg=msg)

        cursor.execute(
            "INSERT INTO users (username, password, nombre, apellidos, email) VALUES (?, ?, ?, ?, ?)",
            (username, password, nombre, apellidos, email),
        )
        conn.commit()
        msg = "Usuari creat, ja pots iniciar sessió"
        #return redirect(url_for("login"))
    return render_template("login.html", msg=msg)

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

        # opcional: aceptar "usuario" o "username" si hace falta
        username = data.get("usuario") or data.get("username")


        if password == "":
            try:
                cursor.execute(
                    "UPDATE users SET nombre = ?, apellidos = ?, email = ? WHERE id = ?",
                    (nombre, apellidos, email, user_id),
                )
                conn.commit()
            except sqlite3.IntegrityError as e:
                return f"Error actualizando perfil: {e}", 400
        else:
            password = generate_password_hash(password)
            try:
                cursor.execute(
                    "UPDATE users SET nombre = ?, apellidos = ?, email = ?, password = ? WHERE id = ?",
                    (nombre, apellidos, email, password, user_id),
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
        }
        return jsonify(perfil_data)
    else:
        return jsonify({"error": "Usuario no encontrado"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)