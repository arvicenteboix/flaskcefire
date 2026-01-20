# auto-py-to-exe para compilar este script
# Asegúrate de tener instaladas las librerías necesarias
# pyinstaller --onefile --add-data "archivo.txt:." tu_script.py


import shutil
import os, sys
import re

version = "v1.0.12"

# Función para crear carpeta y archivos docx
def crear_proyecto():


    codigo = entrada.get().upper()

    nombre_asesor = asesor_var.get()
    nombre_carpeta = f"{codigo}_{nombre_asesor}"

    if not nombre_carpeta or nombre_carpeta == f"_{nombre_asesor}":
        messagebox.showwarning("Advertencia", "Introduce un nombre para la carpeta.")
        return

    # Crear carpeta si no existe
    try:
        os.makedirs(nombre_carpeta, exist_ok=True)

        # Copiar archivos adicionales
        try:
            archivos_a_copiar2 = [
            "AutorizacionGrabacionYDifusion.pdf",
            "AutorizacionUsoMaterialesAbierto.pdf",
            "DATOS PONENTE_NOMBRE.pdf",
            "FITXA ECONÒMICA.xlsx",
            "README.txt",
            ]

            for archivo in archivos_a_copiar2:
                destino = os.path.join(nombre_carpeta, f"{codigo}_{archivo}")
                if not os.path.exists(origen):
                    messagebox.showwarning("Advertencia", f"No se encuentra el archivo: {archivo}")
                    continue
                shutil.copyfile(origen, destino)
            
            if es_no_funcionario_var.get():
                archivo_no_funcionario = "Informe motivado de necesidad de ponente NO FUNCIONARIO CAST.docx"
                origen = obtener_ruta(archivo_no_funcionario)
                destino = os.path.join(nombre_carpeta, f"{codigo}_{archivo_no_funcionario}")

            if contrato_menor.get():
                archivos_contrato_menor = [
                    "Modelo informe necesidad.docx",
                    "Modelo certificado conformidad contrato menor.docx"
                ]
                for archivo_contrato_menor in archivos_contrato_menor:
                    origen = obtener_ruta(archivo_contrato_menor)
                    destino = os.path.join(nombre_carpeta, f"{codigo}_{archivo_contrato_menor}")
                    if not os.path.exists(origen):
                        messagebox.showwarning("Advertencia", f"No se encuentra el archivo: {archivo_contrato_menor}")
                        continue
                    shutil.copyfile(origen, destino)

                archivos_contrato_menor2 = [
                    "INSTRUCCIONES FACTURACION FACE_2025_sdgfp.pdf",
                    "Manual_detallado_FACe-Manual-Proveedores.pdf"
                ]

                for archivo_contrato_menor in archivos_contrato_menor2:
                    origen = obtener_ruta(archivo_contrato_menor)
                    destino = os.path.join(nombre_carpeta, f"{archivo_contrato_menor}")
                    if not os.path.exists(origen):
                        messagebox.showwarning("Advertencia", f"No se encuentra el archivo: {archivo_contrato_menor}")
                        continue
                    shutil.copyfile(origen, destino)

            if not os.path.exists(origen):
                messagebox.showwarning("Advertencia", f"No se encuentra el archivo: {archivo_no_funcionario}")
            else:
                shutil.copyfile(origen, destino)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    except Exception as e:
        messagebox.showerror("Error", str(e))

    # Crear subcarpeta y copiar archivos DOCX

    try:
        subcarpeta = os.path.join(nombre_carpeta, f"{codigo}-Tec")
        os.makedirs(subcarpeta, exist_ok=True)

        archivos_a_copiar = [
            "CuadroTexto.docx",
            "Evidencias.docx",
            "FSE_Ficha_seguimiento.docx"
        ]

        for archivo in archivos_a_copiar:
            origen = obtener_ruta(archivo)
            destino = os.path.join(subcarpeta, f"{codigo}_{archivo}")
            if not os.path.exists(origen):
                messagebox.showwarning("Advertencia", f"No se encuentra el archivo: {archivo}")
                continue
            shutil.copyfile(origen, destino)
        

        # messagebox.showinfo("Éxito", f"Se crearon los archivos DOCX en la carpeta '{nombre_carpeta}'.")

    except Exception as e:
        messagebox.showerror("Error", str(e))
    
    messagebox.showinfo("Éxito", f"Se ha creado la carpeta '{nombre_carpeta}'.")

def check_version():
    import requests
    import webbrowser
    
    try:
        url = "https://api.github.com/repos/arvicenteboix/crea_carpeta/releases/latest"
        response = requests.get(url, timeout=5)
        latest_release = response.json()["tag_name"]
    except:
        ventana_actualizacion = tk.Toplevel()
        ventana_actualizacion.title("Error de actualización")
        ventana_actualizacion.geometry("350x180")
        ventana_actualizacion.resizable(False, False)
        ventana_actualizacion.transient(ventana)  # La ventana de error está por encima de la principal
        ventana_actualizacion.grab_set()  # Bloquea interacción con la ventana principal hasta cerrar
        ventana_actualizacion.focus_set()

        label = tk.Label(
            ventana_actualizacion,
            text="No se pudo verificar si hay actualizaciones disponibles.\n\n"
             "Por favor, consulta la página del proyecto de vez en cuando:\n"
             "https://github.com/arvicenteboix/crea_carpeta/releases",
            wraplength=320,
            justify="left"
        )
        label.pack(pady=(20, 10))

        def abrir_enlace():
            webbrowser.open("https://github.com/arvicenteboix/crea_carpeta/releases")

        boton_enlace = tk.Button(
            ventana_actualizacion,
            text="Abrir página del proyecto",
            command=abrir_enlace,
            bg="#007bff",
            fg="white",
            font=("Arial", 10),
            relief="flat",
            padx=10,
            pady=5
        )
        boton_enlace.pack(pady=(0, 15))

        boton_cerrar = tk.Button(
            ventana_actualizacion,
            text="Cerrar",
            command=ventana_actualizacion.destroy,
            font=("Arial", 10),
            relief="flat",
            padx=10,
            pady=5
        )
        boton_cerrar.pack()

        return
    

    if latest_release != version:
        # Crear ventana personalizada con botón para abrir el enlace
        def abrir_enlace():
            webbrowser.open("https://github.com/arvicenteboix/crea_carpeta/releases")

        ventana_actualizacion = tk.Toplevel()
        ventana_actualizacion.title("Actualización disponible")
        ventana_actualizacion.geometry("350x180")
        ventana_actualizacion.resizable(False, False)
        ventana_actualizacion.transient(ventana)  # La ventana de actualización está por encima de la principal
        ventana_actualizacion.grab_set()  # Bloquea interacción con la ventana principal hasta cerrar
        ventana_actualizacion.focus_set()
 
        label = tk.Label(
            ventana_actualizacion,
            text=f"Hay una nueva versión disponible: {latest_release}. Tienes {version}.\n\nVisita el repositorio para descargarla.",
            wraplength=320,
            justify="left"
        )
        label.pack(pady=(20, 10))

        boton_enlace = tk.Button(
            ventana_actualizacion,
            text="Abrir página de descargas",
            command=abrir_enlace,
            bg="#007bff",
            fg="white",
            font=("Arial", 10),
            relief="flat",
            padx=10,
            pady=5
        )
        boton_enlace.pack(pady=(0, 15))

        boton_cerrar = tk.Button(
            ventana_actualizacion,
            text="Cerrar",
            command=ventana_actualizacion.destroy,
            font=("Arial", 10),
            relief="flat",
            padx=10,
            pady=5
        )
        boton_cerrar.pack()

def resource_path(relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath('.'), relative_path)
# Interfaz gráfica
ventana = tk.Tk()

ventana.iconbitmap(resource_path("icon.ico"))
ventana.title("Generador de Carpeta")
ventana.geometry("350x320")
ventana.configure(bg="#e9ecef")


frame = tk.Frame(ventana, bg="#ffffff", bd=2, relief="groove")
frame.place(relx=0.5, rely=0.5, anchor="center", width=300, height=280)
es_no_funcionario_var = tk.BooleanVar()
contrato_menor = tk.BooleanVar()

etiqueta = tk.Label(frame, text="Asesor:", bg="#ffffff", font=("Arial", 11))
etiqueta.pack(pady=(15, 5))

asesores = ["ALFREDO", "GLORIA", "PACO", "VERA", "GEMMA", "CAMILO", "SANTIAGO", "ANNA", "LOURDES", "LORENA", "PATRICIA", "JOSE", "DAVID"]
asesor_var = tk.StringVar(value=asesores[0])
desplegable = tk.OptionMenu(frame, asesor_var, *asesores)
desplegable.config(font=("Arial", 10), width=20, bg="#ffffff")
desplegable.pack(pady=5)

etiqueta = tk.Label(frame, text="Código del curso:", bg="#ffffff", font=("Arial", 11))
etiqueta.pack(pady=(15, 5))

def validar_codigo(codigo):
    # Patrón: 2 dígitos, 2 letras, 2 dígitos, 2 letras, 3 dígitos (ej: 25fp45er345)
    patron = r'^\d{2}[a-zA-Z]{2}\d{2}[a-zA-Z]{2}\d{3}$'
    return re.match(patron, codigo) is not None

def on_focus_out(event):
    codigo = entrada.get()
    if codigo and not validar_codigo(codigo):
        messagebox.showwarning("Advertencia", "El código debe tener el formato de código Gesform")
        entrada.focus_set()
        return 0
    return 1

entrada = tk.Entry(frame, width=28, font=("Arial", 10), relief="solid", bd=1)
entrada.pack(pady=5)
# entrada.bind("<FocusOut>", on_focus_out)

checkbox = tk.Checkbutton(frame, text="Es no funcionario", variable=es_no_funcionario_var, bg="#ffffff", font=("Arial", 10))
checkbox.pack(pady=(5, 0))

checkbox = tk.Checkbutton(frame, text="Contiene factura empresa materiales", variable=contrato_menor, bg="#ffffff", font=("Arial", 10))
checkbox.pack(pady=(5, 0))

boton = tk.Button(frame, text="Crear Carpeta", command=crear_proyecto, bg="#007bff", fg="white",
                  font=("Arial", 10), relief="flat", padx=10, pady=5)
boton.pack(pady=(10, 5))

label_version = tk.Label(ventana, text=version, bg="#e9ecef", font=("Arial", 8), fg="#6c757d")
label_version.place(relx=1.0, rely=1.0, anchor="se", x=-1, y=-1)

check_version()

ventana.mainloop()

