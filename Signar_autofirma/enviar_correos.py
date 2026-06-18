import os
import sys
import platform

# Verificar dependencias antes de importar módulos de terceros o iniciar
def comprobar_dependencias():
    faltantes = []
    
    # 1. pandas
    try:
        import pandas
    except ImportError:
        faltantes.append("pandas")
        
    # 2. openpyxl (requerido para que pandas lea excel)
    try:
        import openpyxl
    except ImportError:
        faltantes.append("openpyxl")
        
    # 3. win32com (pywin32) - solo en Windows
    if platform.system() == "Windows":
        try:
            import win32com.client
        except ImportError:
            faltantes.append("pywin32")
            
    if faltantes:
        mensaje_texto = (
            "\n" + "="*70 + "\n"
            "ERROR: Faltan dependencias de Python necesarias para ejecutar este script.\n\n"
            f"Módulos faltantes: {', '.join(faltantes)}\n\n"
            "Para instalarlos, abre la terminal (CMD o PowerShell) y ejecuta:\n"
            f"pip install {' '.join(faltantes)}\n"
            + "="*70 + "\n"
        )
        print(mensaje_texto, file=sys.stderr)
        
        # Intentar mostrar mensaje con Tkinter
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()
            
            mensaje_gui = (
                "No se pueden importar las siguientes dependencias necesarias:\n"
                f"- {', '.join(faltantes)}\n\n"
                "Para instalarlas, por favor abre la terminal (CMD/PowerShell) y ejecuta el comando:\n\n"
                f"pip install {' '.join(faltantes)}"
            )
            messagebox.showerror("Error de Dependencias", mensaje_gui)
            root.destroy()
        except Exception:
            pass
            
        sys.exit(1)

comprobar_dependencias()

import html
import pandas as pd
import time
import subprocess
import tkinter as tk
from tkinter import ttk


def obtener_smtp_cuenta(cuenta):
    try:
        return str(cuenta.SmtpAddress).strip()
    except Exception:
        return ""


def forzar_cuenta_envio(correo, cuenta_outlook):
    if cuenta_outlook is None:
        return

    # Metodo directo
    try:
        correo.SendUsingAccount = cuenta_outlook
    except Exception:
        pass

    # Fallback COM: en algunos perfiles Outlook ignora el setter anterior
    try:
        correo._oleobj_.Invoke(*(64209, 0, 8, 0, cuenta_outlook))
    except Exception:
        pass


def obtener_cuentas_outlook():
    import win32com.client as win32

    outlook = win32.Dispatch('Outlook.Application')
    session = outlook.Session
    return list(session.Accounts)


def construir_cuerpo_html(cuerpo_plano):
    return "<br>".join(html.escape(linea) for linea in cuerpo_plano.splitlines())


def mostrar_formulario_envio(cuentas):
    if not cuentas:
        return None

    labels = []
    for cuenta in cuentas:
        nombre = str(cuenta)
        smtp = obtener_smtp_cuenta(cuenta)
        labels.append(f"{nombre} ({smtp})" if smtp else nombre)

    root = tk.Tk()
    root.title("Configuracion de envio")
    root.geometry("720x520")
    root.resizable(False, False)

    resultado = {"data": None}

    marco = ttk.Frame(root, padding=16)
    marco.pack(fill="both", expand=True)

    ttk.Label(marco, text="Selecciona la cuenta de correo electronico desde la cual quieres enviar los correos").pack(anchor="w")
    cuenta_var = tk.StringVar(value=labels[0])
    combo = ttk.Combobox(marco, textvariable=cuenta_var, values=labels, state="readonly")
    combo.current(0)
    combo.pack(fill="x", pady=(4, 12))

    ttk.Label(marco, text='Escribe el asunto del mensaje (por ejemplo: "Certificado asistencia formacion 26FP25CF001")').pack(anchor="w")
    asunto_var = tk.StringVar(value="Certificado de Asistencia")
    entrada_asunto = ttk.Entry(marco, textvariable=asunto_var)
    entrada_asunto.pack(fill="x", pady=(4, 12))

    ttk.Label(marco, text='Escribe el cuerpo del mensaje (por ejemplo: "Adjuntamos certificado de asistenciade la formacion 26FP25CF001")').pack(anchor="w")
    texto_cuerpo = tk.Text(marco, wrap="word", height=14)
    texto_cuerpo.pack(fill="both", expand=True, pady=(4, 12))
    texto_cuerpo.insert("1.0", "Adjunto Certificado de Asistencia")

    estado_var = tk.StringVar(value="")
    ttk.Label(marco, textvariable=estado_var, foreground="red").pack(anchor="w", pady=(0, 8))

    botones = ttk.Frame(marco)
    botones.pack(fill="x")

    def al_continuar():
        asunto = asunto_var.get().strip()
        cuerpo = texto_cuerpo.get("1.0", "end").strip()
        if not asunto:
            estado_var.set("El asunto no puede estar vacio.")
            return
        if not cuerpo:
            estado_var.set("El cuerpo no puede estar vacio.")
            return

        indice = combo.current()
        if indice < 0:
            estado_var.set("Selecciona una cuenta de envio.")
            return

        resultado["data"] = {
            "cuenta": cuentas[indice],
            "asunto": asunto,
            "cuerpo": cuerpo,
        }
        root.destroy()

    def al_cancelar():
        resultado["data"] = None
        root.destroy()

    ttk.Button(botones, text="Continuar", command=al_continuar).pack(side="left")
    ttk.Button(botones, text="Cancelar", command=al_cancelar).pack(side="left", padx=(8, 0))

    root.protocol("WM_DELETE_WINDOW", al_cancelar)
    entrada_asunto.focus_set()
    root.mainloop()

    return resultado["data"]


def mostrar_confirmacion_revision(cuenta_envio):
    root = tk.Tk()
    root.title("Confirmacion")
    root.geometry("640x180")
    root.resizable(False, False)

    resultado = {"continuar": False}

    marco = ttk.Frame(root, padding=16)
    marco.pack(fill="both", expand=True)

    mensaje = (
        f"Hemos enviado un correo electronico de prueba a tu cuenta {cuenta_envio}, por favor, "
        "revisa que el asunto y el texto son correctos.\n"
        "En el caso de que sean correctos pulsa continuar, en caso contrario pulsa cancelar para detener el proceso"
    )
    ttk.Label(marco, text=mensaje, justify="left", wraplength=600).pack(anchor="w", pady=(0, 16))

    botones = ttk.Frame(marco)
    botones.pack(fill="x")

    def al_continuar():
        resultado["continuar"] = True
        root.destroy()

    def al_cancelar():
        resultado["continuar"] = False
        root.destroy()

    ttk.Button(botones, text="Continuar", command=al_continuar).pack(side="left")
    ttk.Button(botones, text="Cancelar", command=al_cancelar).pack(side="left", padx=(8, 0))

    root.protocol("WM_DELETE_WINDOW", al_cancelar)
    root.mainloop()

    return resultado["continuar"]


def mostrar_advertencia_inicial():
    root = tk.Tk()
    root.title("Advertencia")
    root.geometry("760x260")
    root.resizable(False, False)

    resultado = {"continuar": False}

    marco = ttk.Frame(root, padding=16)
    marco.pack(fill="both", expand=True)

    texto = (
        "- Para que funcione el envio tienes que tener instalado en tu ordenador Microsoft Office Classic"
    )
    ttk.Label(marco, text=texto, justify="left", wraplength=720).pack(anchor="w", pady=(0, 16))

    botones = ttk.Frame(marco)
    botones.pack(fill="x")

    def al_continuar():
        resultado["continuar"] = True
        root.destroy()

    def al_cancelar():
        resultado["continuar"] = False
        root.destroy()

    ttk.Button(botones, text="Continuar", command=al_continuar).pack(side="left")
    ttk.Button(botones, text="Cancelar", command=al_cancelar).pack(side="left", padx=(8, 0))

    root.protocol("WM_DELETE_WINDOW", al_cancelar)
    root.mainloop()

    return resultado["continuar"]


def mostrar_confirmacion_envio_masivo(total_correos):
    root = tk.Tk()
    root.title("Confirmacion de envio")
    root.geometry("560x180")
    root.resizable(False, False)

    resultado = {"continuar": False}

    marco = ttk.Frame(root, padding=16)
    marco.pack(fill="both", expand=True)

    mensaje = f"Se van a enviar {total_correos} correos electronicos. Desea continuar?"
    ttk.Label(marco, text=mensaje, justify="left", wraplength=520).pack(anchor="w", pady=(0, 16))

    botones = ttk.Frame(marco)
    botones.pack(fill="x")

    def al_continuar():
        resultado["continuar"] = True
        root.destroy()

    def al_cancelar():
        resultado["continuar"] = False
        root.destroy()

    ttk.Button(botones, text="Continuar", command=al_continuar).pack(side="left")
    ttk.Button(botones, text="Cancelar", command=al_cancelar).pack(side="left", padx=(8, 0))

    root.protocol("WM_DELETE_WINDOW", al_cancelar)
    root.mainloop()

    return resultado["continuar"]


def enviar_mensaje_prueba(cuenta_outlook, asunto, cuerpo):
    if cuenta_outlook is None:
        print("No se pudo enviar mensaje de prueba porque no hay cuenta seleccionada.")
        return False

    destinatario_prueba = obtener_smtp_cuenta(cuenta_outlook)
    if not destinatario_prueba:
        print("No se pudo obtener el email de la cuenta seleccionada para enviar la prueba.")
        return False

    asunto_prueba = f"MENSAJE DE PRUEBA - {asunto}"
    enviar_correo(
        destinatario=destinatario_prueba,
        ruta_adjunto="",
        asunto=asunto_prueba,
        cuerpo=cuerpo,
        modo_borrador=False,
        cuenta_outlook=cuenta_outlook,
        adjuntar_archivo=False,
    )
    return True


def enviar_correo(destinatario, ruta_adjunto, asunto, cuerpo, modo_borrador=True, cuenta_outlook=None, adjuntar_archivo=True):
    sistema = platform.system()
    
    # Asegurar ruta absoluta
    ruta_abs = os.path.abspath(ruta_adjunto)
    
    if sistema == "Windows":
        import win32com.client as win32
        outlook = win32.Dispatch('Outlook.Application')
        correo = outlook.CreateItem(0)
        forzar_cuenta_envio(correo, cuenta_outlook)
        smtp = obtener_smtp_cuenta(cuenta_outlook)
        if smtp:
            print(f"Intentando enviar desde: {smtp}")
        correo.To = destinatario
        correo.Subject = asunto
        if adjuntar_archivo:
            correo.Attachments.Add(ruta_abs)
        correo.HTMLBody = cuerpo
        try:
            if modo_borrador:
                correo.Save()
                print(f"Guardado en borradores: {destinatario}")
            else:
                correo.Send()
                print(f"Enviado: {destinatario}")
        except Exception as e:
            print(f"Error al enviar a {destinatario}: {e}")
            return False
        return True
        
    elif sistema == "Darwin":  # macOS
        # Escapamos comillas para evitar errores en AppleScript
        applescript = f'''
        tell application "Microsoft Outlook"
            set newMessage to make new outgoing message with properties {{subject:"{asunto}", content:"{cuerpo}"}}
            make new recipient at newMessage with properties {{email address:{{address:"{destinatario}"}}}}
            {f'make new attachment at newMessage with properties {{file:"{ruta_abs}"}}' if adjuntar_archivo else ''}
            save newMessage
            {"-- send newMessage" if modo_borrador else "send newMessage"}
        end tell
        '''
        subprocess.run(['osascript', '-e', applescript])
        return True
    else:
        print(f"Sistema operativo {sistema} no compatible.")
        return False


def cargar_destinatarios(ruta_excel):
    df = pd.read_excel(ruta_excel)
    df.columns = [col.lower().strip() for col in df.columns]
    return df


def procesar_excel(df, asunto, cuerpo, modo_borrador=True, cuenta_outlook=None):
    total = len(df)
    enviados_ok = 0
    enviados_error = 0

    root = tk.Tk()
    root.title("Progreso de envio")
    root.geometry("800x520")
    root.resizable(False, False)

    marco = ttk.Frame(root, padding=16)
    marco.pack(fill="both", expand=True)

    estado_var = tk.StringVar(value="Iniciando envio...")
    resumen_var = tk.StringVar(value="")
    contador_enviados_var = tk.StringVar(value="Enviados: 0")
    contador_errores_var = tk.StringVar(value="Errores: 0")
    contador_pendientes_var = tk.StringVar(value=f"Pendientes: {total}")

    ttk.Label(marco, textvariable=estado_var).pack(anchor="w", pady=(0, 8))

    marco_contadores = ttk.Frame(marco)
    marco_contadores.pack(fill="x", pady=(0, 8))
    ttk.Label(marco_contadores, textvariable=contador_pendientes_var).pack(side="left", padx=(0, 16))
    ttk.Label(marco_contadores, textvariable=contador_enviados_var).pack(side="left", padx=(0, 16))
    ttk.Label(marco_contadores, textvariable=contador_errores_var).pack(side="left")

    progreso = ttk.Progressbar(marco, mode="determinate", maximum=max(total, 1), value=0)
    progreso.pack(fill="x", pady=(0, 10))

    texto_log = tk.Text(marco, wrap="word", height=18)
    texto_log.pack(fill="both", expand=True)
    texto_log.configure(state="disabled")

    ttk.Label(marco, textvariable=resumen_var).pack(anchor="w", pady=(10, 8))

    boton_salir = ttk.Button(marco, text="Salir", state="disabled", command=root.destroy)
    boton_salir.pack(anchor="e")

    def bloquear_cierre():
        return

    root.protocol("WM_DELETE_WINDOW", bloquear_cierre)

    def agregar_log(mensaje):
        texto_log.configure(state="normal")
        texto_log.insert("end", mensaje + "\n")
        texto_log.see("end")
        texto_log.configure(state="disabled")
        root.update_idletasks()
    
    for indice, (_, row) in enumerate(df.iterrows(), start=1):
        destinatario = str(row['email']).strip()
        adjunto = str(row['adjunto']).strip()
        estado_var.set(f"Enviando {indice} de {total}: {destinatario}")
        agregar_log(f"[{indice}/{total}] Procesando: {destinatario}")
        ok = enviar_correo(destinatario, adjunto, asunto, cuerpo, modo_borrador, cuenta_outlook)
        if ok:
            enviados_ok += 1
            agregar_log(f"[{indice}/{total}] Enviado correctamente: {destinatario}")
        else:
            enviados_error += 1
            agregar_log(f"[{indice}/{total}] Error en envio: {destinatario}")

        pendientes = total - indice
        contador_enviados_var.set(f"Enviados: {enviados_ok}")
        contador_errores_var.set(f"Errores: {enviados_error}")
        contador_pendientes_var.set(f"Pendientes: {pendientes}")

        progreso["value"] = indice
        root.update()

    resumen = f"Resumen de envio -> Correctos: {enviados_ok} | Errores: {enviados_error}"
    estado_var.set("Envio finalizado")
    resumen_var.set(resumen)
    agregar_log(resumen)
    print(resumen)

    boton_salir.configure(state="normal")
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()

if __name__ == "__main__":
    if platform.system() != "Windows":
        print("Este flujo grafico esta preparado para Windows con Outlook.")
        sys.exit(1)

    continuar_advertencia = mostrar_advertencia_inicial()
    if not continuar_advertencia:
        print("Ejecucion cancelada por el usuario.")
        sys.exit(0)

    cuentas = obtener_cuentas_outlook()
    if not cuentas:
        print("No se encontraron cuentas en Outlook.")
        sys.exit(1)

    configuracion = mostrar_formulario_envio(cuentas)
    if configuracion is None:
        print("Ejecucion cancelada por el usuario.")
        sys.exit(0)

    cuenta = configuracion["cuenta"]
    asunto_mensaje = configuracion["asunto"]
    cuerpo_plano = configuracion["cuerpo"]
    cuerpo_mensaje = construir_cuerpo_html(cuerpo_plano)

    prueba_enviada = enviar_mensaje_prueba(cuenta, asunto_mensaje, cuerpo_mensaje)
    if not prueba_enviada:
        print("No se pudo completar el envio de prueba. Se detiene el script.")
        sys.exit(1)

    cuenta_envio = obtener_smtp_cuenta(cuenta) or str(cuenta)
    continuar = mostrar_confirmacion_revision(cuenta_envio)
    if not continuar:
        print("Ejecucion cancelada por el usuario.")
        sys.exit(0)

    df_destinatarios = cargar_destinatarios("contactos.xlsx")
    total_correos = len(df_destinatarios)
    if total_correos == 0:
        print("No hay correos para enviar en contactos.xlsx.")
        sys.exit(0)

    continuar_masivo = mostrar_confirmacion_envio_masivo(total_correos)
    if not continuar_masivo:
        print("Ejecucion cancelada por el usuario.")
        sys.exit(0)

    procesar_excel(df_destinatarios, asunto_mensaje, cuerpo_mensaje, modo_borrador=False, cuenta_outlook=cuenta)