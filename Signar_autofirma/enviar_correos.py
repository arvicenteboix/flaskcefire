import os
import sys
import pandas as pd
import platform
import time
import subprocess

def enviar_correo(destinatario, ruta_adjunto, asunto, modo_borrador=True):
    sistema = platform.system()
    
    # Asegurar ruta absoluta
    ruta_abs = os.path.abspath(ruta_adjunto)
    
    if sistema == "Windows":
        import win32com.client as win32
        outlook = win32.Dispatch('Outlook.Application')
        correo = outlook.CreateItem(0)
        correo.To = destinatario
        correo.Subject = asunto
        correo.Attachments.Add(ruta_abs)
        correo.HTMLBody = "Adjunto el archivo solicitado."
        if modo_borrador: correo.Save()
        else: correo.Send()
        
    elif sistema == "Darwin":  # macOS
        # Escapamos comillas para evitar errores en AppleScript
        applescript = f'''
        tell application "Microsoft Outlook"
            set newMessage to make new outgoing message with properties {{subject:"{asunto}", content:"Adjunto el archivo solicitado."}}
            make new recipient at newMessage with properties {{email address:{{address:"{destinatario}"}}}}
            make new attachment at newMessage with properties {{file:"{ruta_abs}"}}
            save newMessage
            {"-- send newMessage" if modo_borrador else "send newMessage"}
        end tell
        '''
        subprocess.run(['osascript', '-e', applescript])
    else:
        print(f"Sistema operativo {sistema} no compatible.")

def procesar_excel(ruta_excel, modo_borrador=True):
    df = pd.read_excel(ruta_excel)
    df.columns = [col.lower().strip() for col in df.columns]
    
    for _, row in df.iterrows():
        destinatario = str(row['email']).strip()
        adjunto = str(row['adjunto']).strip()
        print(f"Procesando: {destinatario}")
        enviar_correo(destinatario, adjunto, "Justificante de asistencia", modo_borrador)

if __name__ == "__main__":
    # Ajusta aquí la configuración
    procesar_excel("contactos.xlsx", modo_borrador=True)