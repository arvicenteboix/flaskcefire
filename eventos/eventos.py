import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, date
from icalendar import Calendar, Event
import pytz
import os


# pip install icalendar pytz


def add_calendar_multiples(fecha_usuario, titulo, descripcion, lugar, destinatario, api_key, lista_eventos=None):
    """
    Envía correo con archivo .ics que contiene MÚLTIPLES eventos de todo el día
    
    lista_eventos = [
        {"fecha": "15-03-2026", "titulo": "Evento 1", "descripcion": "Desc 1", "lugar": "Lugar 1"},
        {"fecha": "16-03-2026", "titulo": "Evento 2", "descripcion": "Desc 2", "lugar": "Lugar 2"},
        ...
    ]
    """
    
    def fecha_ics_allday(fecha_str):
        """Convierte dd-MM-yyyy a fecha de TODO EL DÍA para ICS"""
        fecha_dt = datetime.strptime(fecha_str, "%d-%m-%Y").date()
        return fecha_dt

    # Si no se pasa lista_eventos, usar solo el evento original
    if lista_eventos is None:
        lista_eventos = [{
            "fecha": fecha_usuario,
            "titulo": titulo,
            "descripcion": descripcion,
            "lugar": lugar
        }]

    # Crear calendario ICS con MÚLTIPLES eventos
    cal = Calendar()
    
    for evento_data in lista_eventos:
        evento = Event()
        evento.add('summary', evento_data['titulo'])
        evento.add('description', evento_data['descripcion'])
        evento.add('location', evento_data['lugar'])
        fecha_evento = fecha_ics_allday(evento_data['fecha'])
        evento.add('dtstart', fecha_evento)  # Todo el día
        evento.add('dtend', fecha_evento)    # Mismo día
        evento.add('dtstamp', pytz.UTC.localize(datetime.now()))
        evento.add('transp', 'TRANSPARENT')  # No ocupa slot horario
        
        cal.add_component(evento)

    # Guardar archivo ICS
    nombre_archivo = 'calendario_multi.ics'
    with open(nombre_archivo, 'wb') as f:
        f.write(cal.to_ical())

    # CONFIGURACIÓN CORREO
    remitente = 'valenciacefire@gmail.com'
    asunto = f'Calendario con {len(lista_eventos)} eventos'
    cuerpo = f"""
Hola,

Adjunto el archivo .ics con {len(lista_eventos)} eventos de TODO EL DÍA:

"""
    
    for i, evento in enumerate(lista_eventos, 1):
        cuerpo += f"{i}. {evento['titulo']} - {evento['fecha']} ({evento['lugar']})\n"

    cuerpo += f"""
Abre el adjunto para añadir TODOS los eventos a Outlook, Google Calendar, etc.

Saludos,
Tu sistema automático
    """

    # Crear mensaje email
    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = asunto
    msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

    # Adjuntar ICS
    with open(nombre_archivo, 'rb') as adjunto:
        parte = MIMEBase('application', 'octet-stream')
        parte.set_payload(adjunto.read())
    encoders.encode_base64(parte)
    parte.add_header(
        'Content-Disposition',
        f'attachment; filename="calendario_multiples.ics"'
    )
    parte.add_header('Content-Type', f'text/calendar; name="calendario_multiples.ics"')
    msg.attach(parte)

    # ENVIAR CORREO (Gmail)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, api_key)
        texto = msg.as_string()
        server.sendmail(remitente, destinatario, texto)
        server.quit()
        
        print("✅ Correo enviado correctamente")
        print(f"📅 {len(lista_eventos)} eventos enviados:")
        for evento in lista_eventos:
            print(f"   - {evento['titulo']} ({evento['fecha']})")
        
    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        # Limpiar archivo temporal
        if os.path.exists(nombre_archivo):
            os.remove(nombre_archivo)


if __name__ == "__main__":
    # EJEMPLO 1: Múltiples eventos
    add_calendar_multiples(
        fecha_usuario="15-03-2026",  # No se usa si pasas lista_eventos
        titulo="Evento único",       # No se usa si pasas lista_eventos
        descripcion="Desc único",    # No se usa si pasas lista_eventos
        lugar="Lugar único",         # No se usa si pasas lista_eventos
        destinatario="ar.vicenteboix@edu.gva.es",
        api_key="TU_API_KEY_DE_GMAIL",
        lista_eventos=[
            {
                "fecha": "15-03-2026",
                "titulo": "Sesión FP Mañana",
                "descripcion": "Formación profesores ciclo DAM",
                "lugar": "CEFIRE Valencia - Sala 1"
            },
            {
                "fecha": "16-03-2026", 
                "titulo": "Sesión FP Tarde",
                "descripcion": "Formación profesores ciclo DAW",
                "lugar": "CEFIRE Valencia - Sala 2"
            },
            {
                "fecha": "20-03-2026",
                "titulo": "Taller Certificaciones",
                "descripcion": "Habilidades profesionales FP",
                "lugar": "Online via Teams"
            }
        ]
    )
