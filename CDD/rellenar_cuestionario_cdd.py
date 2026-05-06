from pypdf import PdfReader, PdfWriter
from io import BytesIO
from pathlib import Path
import zipfile
import tempfile

def rellenar_cuestionario_en_memoria(codigo, titulo, horas, asesoria, correoelectronico, tipo):
    """Genera PDF en memoria (BytesIO) sin guardar en disco"""
    data = {
        'codigo': codigo,
        'titulo': titulo,
        'horas': horas,
        'asesoria': asesoria,
        'correoelectronico': correoelectronico
    }

    archivo_original = 'CDD/Cuestionario-CDD-rellenable-CAS_todo.pdf'
    
    reader = PdfReader(archivo_original)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    # Rellenar campos de texto
    writer.update_page_form_field_values(writer.pages[0], data)
    
    # Marcar casilla del tipo
    writer.update_page_form_field_values(
        writer.pages[0], 
        {tipo: "/Yes"},
        auto_regenerate=False
    )

    # Devolver PDF en memoria (BytesIO)
    pdf_memoria = BytesIO()
    writer.write(pdf_memoria)
    pdf_memoria.seek(0)  # Resetear al inicio
    return pdf_memoria


def crear_zip_cuestionarios_directo(datos):
    """Crea ZIP directamente desde PDFs en memoria"""

    tmp_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
    tmp_file.close()
    nombre_zip = tmp_file.name

    with zipfile.ZipFile(nombre_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for dato in datos:
            # Generar PDF en memoria
            pdf_bytes = rellenar_cuestionario_en_memoria(
                dato['codigo'],
                dato['titulo'],
                dato['horas'],
                dato['asesoria'],
                dato['correoelectronico'],
                dato['tipo']
            )
            
            # Añadir directamente al ZIP con nombre = código
            zipf.writestr(f"{dato['codigo']}.pdf", pdf_bytes.getvalue())
    
    print(f"✅ Creado {nombre_zip} con {len(datos)} cuestionarios (sin archivos temporales)")
    return nombre_zip
