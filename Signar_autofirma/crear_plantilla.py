import pandas as pd
import os

def crear_datos_de_prueba():
    print("Creando archivos de texto de prueba para adjuntar...")
    
    # Crear dos archivos de texto sencillos de prueba
    adjunto1 = "reporte_mensual.txt"
    adjunto2 = "factura_pendiente.txt"
    
    with open(adjunto1, "w", encoding="utf-8") as f:
        f.write("Este es un archivo de prueba simulando un reporte mensual.\n")
        f.write("Generado automáticamente por el script de pruebas.")
        
    with open(adjunto2, "w", encoding="utf-8") as f:
        f.write("Este es un archivo de prueba simulando una factura pendiente.\n")
        f.write("Generado automáticamente por el script de pruebas.")
        
    print(f"Archivos creados: {adjunto1}, {adjunto2}")
    
    # Obtener rutas absolutas
    ruta_abs_1 = os.path.abspath(adjunto1)
    ruta_abs_2 = os.path.abspath(adjunto2)
    
    # Crear un DataFrame de ejemplo
    # Nota: Usamos un correo ficticio y uno que el usuario pueda editar.
    data = {
        "email": ["destinatario_prueba1@example.com", "destinatario_prueba2@example.com"],
        "adjunto": [ruta_abs_1, adjunto2] # Uno con ruta absoluta, otro con ruta relativa
    }
    
    df = pd.DataFrame(data)
    
    nombre_excel = "contactos.xlsx"
    df.to_excel(nombre_excel, index=False)
    print(f"Archivo Excel '{nombre_excel}' creado con éxito.")
    print("\nContenido del Excel:")
    print(df)
    print("\n¡Listo! Puedes editar 'contactos.xlsx' con tus propios correos y adjuntos reales.")

if __name__ == "__main__":
    crear_datos_de_prueba()
