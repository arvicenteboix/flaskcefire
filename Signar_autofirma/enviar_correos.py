import os
import sys
import pandas as pd
import win32com.client as win32
import time

def enviar_correos_outlook(ruta_excel="contactos.xlsx", modo_borrador=True):
    """
    Lee un archivo Excel y envía correos electrónicos con archivos adjuntos a través de Outlook.
    
    :param ruta_excel: Ruta del archivo de Excel (.xlsx)
    :param modo_borrador: Si es True, guarda los correos en Borradores para revisión.
                          Si es False, los envía directamente.
    """
    print("=" * 60)
    print("  AUTOMATIZACIÓN DE ENVÍO DE CORREOS CON OUTLOOK")
    print("=" * 60)
    print(f"[*] Cargando archivo Excel: {ruta_excel}")
    print(f"[*] Modo: {'BORRADOR (Guardar en Borradores)' if modo_borrador else 'ENVÍO DIRECTO (Envío real)'}")
    print("-" * 60)

    # 1. Verificar si existe el archivo Excel
    if not os.path.exists(ruta_excel):
        print(f"[ERROR] No se encontró el archivo Excel en: {os.path.abspath(ruta_excel)}")
        return

    # 2. Leer el Excel
    try:
        df = pd.read_excel(ruta_excel)
    except Exception as e:
        print(f"[ERROR] No se pudo leer el archivo Excel: {e}")
        return

    # 3. Validar columnas
    columnas_requeridas = ['email', 'adjunto']
    # Convertir nombres de columnas a minúsculas para mayor flexibilidad
    df.columns = [col.lower().strip() for col in df.columns]
    
    for col in columnas_requeridas:
        if col not in df.columns:
            print(f"[ERROR] Falta la columna obligatoria '{col}' en el archivo Excel.")
            print(f"Columnas encontradas: {list(df.columns)}")
            return

    total_filas = len(df)
    print(f"[i] Se encontraron {total_filas} registros para procesar.\n")

    # 4. Conectar con Outlook
    try:
        # win32.Dispatch se conecta a una instancia existente de Outlook o abre una nueva
        outlook = win32.Dispatch('Outlook.Application')
        # Obtener el espacio de nombres MAPI
        namespace = outlook.GetNamespace("MAPI")
    except Exception as e:
        print("[ERROR] No se pudo conectar con Outlook.")
        print("Asegúrate de tener Microsoft Outlook instalado y configurado con tu cuenta.")
        print(f"Detalle del error: {e}")
        return

    exitosos = 0
    fallidos = 0

    # Obtener el directorio del archivo Excel para resolver rutas relativas
    directorio_excel = os.path.dirname(os.path.abspath(ruta_excel))

    for index, row in df.iterrows():
        num_registro = index + 1
        destinatario = str(row['email']).strip()
        adjunto_raw = str(row['adjunto']).strip()

        print(f"[{num_registro}/{total_filas}] Procesando destinatario: {destinatario}")

        # Validar email básico
        if not destinatario or destinatario == 'nan' or '@' not in destinatario:
            print(f"    [!] Correo inválido u omitido: '{destinatario}'. Saltando registro.")
            fallidos += 1
            print("-" * 40)
            continue

        # Validar y resolver la ruta del adjunto
        if not adjunto_raw or adjunto_raw == 'nan':
            print("    [!] No se especificó archivo adjunto. Saltando registro.")
            fallidos += 1
            print("-" * 40)
            continue

        # Si la ruta es relativa, resolverla respecto al directorio del Excel
        if not os.path.isabs(adjunto_raw):
            ruta_adjunto = os.path.abspath(os.path.join(directorio_excel, adjunto_raw))
        else:
            ruta_adjunto = adjunto_raw

        # Verificar si el archivo adjunto realmente existe
        if not os.path.exists(ruta_adjunto):
            print(f"    [!] El archivo adjunto no existe en: {ruta_adjunto}")
            print("    [!] Saltando este registro para evitar errores de envío.")
            fallidos += 1
            print("-" * 40)
            continue

        # 5. Crear el correo electrónico
        try:
            # CreateItem(0) crea un objeto de tipo MailItem (correo estándar)
            correo = outlook.CreateItem(0)
            
            # Asignar destinatario
            correo.To = destinatario
            
            # Configurar Asunto del correo (puedes personalizar esto o leerlo del Excel si añades una columna 'asunto')
            nombre_archivo = os.path.basename(ruta_adjunto)
            correo.Subject = f"CEFIRE de FP: Justificante de asistencia {nombre_archivo}"
            
            # Configurar Cuerpo del correo en HTML
            correo.HTMLBody = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333333;">
                    <h2>Estimado usuario,</h2>
                    <p>Le hacemos entrega del justificante de asistencia solicitado adjunto a este correo electrónico.</p>
                    <p><b>Detalles del adjunto:</b></p>
                    <ul>
                        <li><b>Archivo:</b> {nombre_archivo}</li>
                        <li><b>Fecha de envío:</b> {time.strftime('%d/%m/%Y %H:%M:%S')}</li>
                    </ul>
                    <hr style="border: 0; border-top: 1px solid #eeeeee;">
                    <p style="font-size: 0.9em; color: #777777;">
                        Este es un mensaje automático generado mediante un script de integración con Microsoft Outlook.
                    </p>
                </body>
            </html>
            """
            
            # Adjuntar el archivo (La API COM de Outlook requiere rutas ABSOLUTAS)
            correo.Attachments.Add(ruta_adjunto)
            
            # 6. Enviar o Guardar en Borradores
            if modo_borrador:
                correo.Save()
                print("    [OK] Correo guardado exitosamente en la carpeta de 'Borradores'.")
            else:
                correo.Send()
                print("    [OK] Correo enviado exitosamente.")
            
            exitosos += 1
            
            # Pequeña pausa para no saturar Outlook/el servidor de correo
            time.sleep(0.5)

        except Exception as e:
            print(f"    [ERROR] Falló la creación/envío del correo: {e}")
            fallidos += 1

        print("-" * 40)

    # Reporte final
    print("\n" + "=" * 60)
    print("  RESUMEN DE PROCESAMIENTO")
    print("=" * 60)
    print(f"  Total procesados: {total_filas}")
    print(f"  Exitosos:         {exitosos}")
    print(f"  Fallidos/Omitidos:{fallidos}")
    print("=" * 60)
    if modo_borrador:
        print("  [INFO] Abre tu aplicación Outlook y ve a la carpeta 'Borradores'")
        print("  para revisar y enviar los correos cuando desees.")
    print("=" * 60)

if __name__ == "__main__":
    # Nombre del archivo excel por defecto
    archivo_excel = "contactos.xlsx"
    
    # Permitir pasar la ruta del excel como argumento
    if len(sys.argv) > 1:
        archivo_excel = sys.argv[1]
        
    # Preguntar al usuario si desea enviar directamente o guardar en borrador
    print("Selecciona una opción:")
    print("1) Guardar en 'Borradores' (Recomendado para verificar primero)")
    print("2) Enviar directamente (Real)")
    
    opcion = input("Elige (1 o 2) [Por defecto: 1]: ").strip()
    
    borrador = True
    if opcion == "2":
        borrador = False
        
    enviar_correos_outlook(archivo_excel, modo_borrador=borrador)
