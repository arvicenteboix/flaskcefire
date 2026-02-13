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
        return


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

