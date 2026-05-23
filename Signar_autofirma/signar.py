import os
import base64
import uuid
import shutil
import zipfile
import io
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from fpdf import FPDF


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

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================================================================
# Official PDF Attendance Certificate Generator Layout (FPDF2)
# ==========================================================================

class AttendanceCertificate(FPDF):
    def header(self):
        # Draw the official Generalitat logo in the upper right
        logo_path = os.path.join(BASE_DIR, 'logo_azul.png')
        if os.path.exists(logo_path):
            # Coordinates: x=145, y=20, w=35 (35mm wide)
            self.image(logo_path, x=145, y=20, w=35)
            
        # Draw CEFIRE / Generalitat Text Header on the left
        self.set_text_color(26, 36, 43)
        self.set_font('Helvetica', 'B', 8)
        self.set_xy(30, 20)
        self.cell(0, 4.2, "GENERALITAT VALENCIANA", ln=1)
        self.set_font('Helvetica', '', 8)
        self.cell(0, 4.2, "Conselleria d'Educació, Cultura i Esport", ln=1)
        self.cell(0, 4.2, "CEFIRE Específic de Formació Professional", ln=1)
        
        # Draw a beautiful colored separator line
        self.set_draw_color(59, 130, 246)  # Blue color
        self.set_line_width(0.8)
        self.line(30, 36, 180, 36)
        
    def footer(self):
        # Draw official verification footer at the bottom
        self.set_y(-25)
        self.set_font('Helvetica', 'I', 7.5)
        self.set_text_color(156, 163, 175)
        self.cell(0, 4, "Document signat electrònicament.", align='C', ln=1)
        self.cell(0, 4, "CEFIRE Específic de FP - Avinguda de Campanar, 32, 46015 València", align='C')

def sanitize_for_latin1(text):
    """
    Cleans typographically rich quotes/dashes and encodes to Latin-1,
    safely handling unsupported characters to prevent PDF crashes.
    """
    if not text:
        return ""
    text = str(text).strip()
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    text = text.replace('–', '-').replace('—', '-')
    return text.encode('latin-1', errors='replace').decode('latin-1')

def generate_pdf_from_row(row_data, output_path):
    """Generates an attendance certificate PDF using the requested layout and variables."""
    # A4 standard: 210 x 297 mm
    pdf = AttendanceCertificate(orientation='P', unit='mm', format='A4')
    pdf.set_margins(30, 40, 30) # Left=30, Top=40, Right=30
    pdf.add_page()
    
    # Document Title
    pdf.ln(18)
    pdf.set_font('Helvetica', 'B', 15)
    pdf.set_text_color(17, 13, 41)  # Dark slate
    pdf.cell(0, 10, "JUSTIFICANT D'ASSISTÈNCIA", align='C', ln=1)
    pdf.ln(12)
    
    # Set main body typography
    pdf.set_font('Helvetica', '', 11.5)
    pdf.set_text_color(31, 41, 55)  # Soft charcoal grey for readability
    
    # Sanitize all row details for Latin-1 Helvetica compatibility
    assessor = sanitize_for_latin1(row_data.get('nombre del asesor', ''))
    name = sanitize_for_latin1(row_data.get('nombre y apellidos', ''))
    dni = sanitize_for_latin1(row_data.get('dni', ''))
    course = sanitize_for_latin1(row_data.get('nombre del curso', ''))
    place = sanitize_for_latin1(row_data.get('lugar de realización', ''))
    start_time = sanitize_for_latin1(row_data.get('hora inicio', ''))
    end_time = sanitize_for_latin1(row_data.get('hora final', ''))
    date_attendance = sanitize_for_latin1(row_data.get('fecha de asistencia', ''))
    
    # Paragraph 1: Assessor Header
    header_text = f"{assessor}, assessor de formació del CEFIRE Específic de Formació Professional en la Direcció General de Formació Professional,"
    pdf.multi_cell(0, 7.5, header_text, align='J')
    pdf.ln(8)
    
    # Certifies header
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, "CERTIFICA:", ln=1)
    pdf.ln(4)
    
    # Paragraph 2: Main Attendance Text
    body_text = (
        f"Que {name} amb DNI {dni}, ha assistit el dia {date_attendance} "
        f"a la formació \"{course}\", realitzada al {place} de València, "
        f"en horari de {start_time} a {end_time} hores."
    )
    
    pdf.set_font('Helvetica', '', 11.5)
    pdf.multi_cell(0, 7.5, body_text, align='J')
    pdf.ln(8)
    
    # Paragraph 3: Ending communication
    ending_text = "La qual cosa comunique als efectes pertinents."
    pdf.multi_cell(0, 7.5, ending_text, align='J')
    pdf.ln(18)
    
    # Sign-off date line
    pdf.set_font('Helvetica', '', 11.5)
    pdf.cell(0, 8, f"València, a data de la signatura electrònica.", ln=1)
    pdf.ln(5)
    
    # Signature line subtitle
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(107, 114, 128)
    pdf.cell(0, 6, "Assessor/a de Formació CEFIRE FP", ln=1)
    
    # Save PDF to disk
    pdf.output(output_path)

# ==========================================================================
# Excel Template Generation Startup hook
# ==========================================================================

def ensure_excel_template():
    """Generates the downloadable Excel template pre-filled with mock data."""
    template_path = os.path.join(STATIC_FOLDER, 'plantilla_justificantes.xlsx')
    if not os.path.exists(template_path):
        data = {
            'nombre y apellidos': ['Joan Pérez i García', 'Maria Sanchis i Moreno'],
            'dni': ['12345678A', '87654321B'],
            'nombre del curso': ['Innovació en la Formació Professional', 'Eines Digitals per a Docents de FP'],
            'nombre del asesor': ['Andreu Valor i Soler', 'Anna Segura i Beltran'],
            'lugar de realización': ['CEFIRE Específic de FP', 'Sede de la Direcció General de FP'],
            'hora inicio': ['09:00', '16:00'],
            'hora final': ['14:00', '20:00'],
            'fecha de asistencia': ['25 de maig de 2026', '26 de maig de 2026']
        }
        df = pd.DataFrame(data)
        df.to_excel(template_path, index=False)
        print(f"Plantilla Excel pre-generada en: {template_path}")

# Pre-generate plantilla on import/startup
ensure_excel_template()

