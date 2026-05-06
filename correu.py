from flask import Flask
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from datetime import datetime

from datetime import datetime, date
from icalendar import Calendar, Event
import pytz
import os

# Llistat d'exemple de correus
mail = None
scheduler = None

def enviar_correus(app, conn):
    """Funció que envia correus a tots els contactes"""
    
    def envia(datos, tipo):
        pass  # Per a proves, no enviar correus reals. Descomenta el codi real per a producció.
        """ with app.app_context():
            # AGRUPAR por asesoria para enviar UN SOL correo por asesor
            formacions_por_asesor = {}
            for formacion in datos:
                asesoria = formacion['asesoria']
                if asesoria not in formacions_por_asesor:
                    formacions_por_asesor[asesoria] = []
                formacions_por_asesor[asesoria].append(formacion)
            
            # Enviar UN correo por cada asesor
            for asesoria, formacions in formacions_por_asesor.items():
                usuari = users[formacion['asesoria']]  # ← Solo una vez por asesor
                body = f"Hola {usuari['nombre']},\n\n"
                body += f"Recordatori {tipo} per a data { datetime.now().strftime('%d/%m/%y')}:\n\n"
               
                
                for formacion in formacions:
                    body += f"- {formacion['codi_ed']} - {formacion['titol']}\n"
                
                body += "\nSalutacions,"
                
                msg = Message(
                    subject=f'Recordatori: {tipo} ({len(formacions)} formacions)',
                    sender='valenciacefire@gmail.com',
                    recipients=[usuari['email']],
                    body=body
                )
                mail.send(msg)
                print(f"  ✓ Enviat {tipo} a {usuari['nombre']} ({len(formacions)} formacions)") """

    def envia_david(datos):
        pass
    """         with app.app_context():
            body = "Hola, \n\nFormacions que entren en inscripció a dia de hui per a posar en Instagram:\n\n"
            for formacion in datos:
                body += f"Formació: {formacion['codi_ed']} - {formacion['titol']} - Data Inscripció: { datetime.now().strftime('%d/%m/%y')}\n"

            body += "\nSalutacions,"
            msg = Message(
                subject='Recordatori: Formacions en inscripció a dia de hui',
                sender='valenciacefire@gmail.com',
                recipients=['ar.vicenteboix@edu.gva.es'],
                body=body
            )
            mail.send(msg) 
    
    def envia_david(datos):
        print ("Execute david")

    def envia(datos, tipo):
        print(f"  ✓ Enviant {tipo} a {len(datos)} formacions...")
    """

    print(datetime.now(), "Enviant correus...")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, email FROM users")
    users = cursor.fetchall()
    print(f"  ✓ Obtinguts {len(users)} usuaris de la base de dades.")


    cursor.execute("SELECT * FROM formacio where data_ini = date('now')")
    hoy = cursor.fetchall()
    print(f"  ✓ Obtingudes {len(hoy)} formacions que comencen avui.")
    if len(hoy) > 0:
        envia(hoy, "Inici de la formació")

    cursor.execute("SELECT * FROM formacio where data_insc = date('now')")
    inscripciones = cursor.fetchall()
    if len(inscripciones) > 0:
        envia(inscripciones, "Inscripció")
        envia_david(inscripciones)


    cursor.execute("SELECT * FROM formacio where data_conf = date('now')")
    confirmaciones = cursor.fetchall()
    if len(confirmaciones) > 0:
        envia(confirmaciones, "Confirmació")

    cursor.execute("SELECT * FROM formacio where data_list = date('now')")
    listados = cursor.fetchall()
    if len(listados) > 0:
        envia(listados, "Llistat definitiu")

def init_mail_and_scheduler(app, conn):
    """Inicialitza Mail i el scheduler amb l'app de Flask."""
    global mail, scheduler

    if scheduler and scheduler.running:
        print("⚠️  Scheduler ya está ejecutándose. Saltando...")
        return mail, scheduler
    
    print("🚀 Inicializando Mail y Scheduler...")
    mail = Mail(app)
    scheduler = BackgroundScheduler()

    # Inicialitzar Mail amb la configuració de app
    mail.init_app(app)
    scheduler.remove_all_jobs()
    # Configurar scheduler
    scheduler.add_job(func=lambda: enviar_correus(app, conn), trigger='cron', hour=2, minute=0)
    # scheduler.add_job(func=lambda: enviar_correus(app, conn), trigger='interval', seconds=10, replace_existing=True)  # Per a proves, envia cada minut
    scheduler.start()
    # Aturar scheduler quan es tanque l'app
    atexit.register(lambda: scheduler.shutdown(wait=False))
    return mail, scheduler



def add_calendar_multiples(app, destinatario, lista_eventos=None):

    print("🚀 Enviando correo con calendario múltiple...")

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
        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        return fecha_dt


    # Crear calendario ICS con MÚLTIPLES eventos
    cal = Calendar()
    
    for evento_data in lista_eventos:
        evento = Event()
        evento.add('summary', evento_data['titulo'])
        evento.add('description', evento_data['descripcion'])
        fecha_evento = fecha_ics_allday(evento_data['fecha'])
        evento.add('dtstart', fecha_evento)  # Todo el día
        evento.add('dtend', fecha_evento)    # Mismo día
        evento.add('dtstamp', pytz.UTC.localize(datetime.now()))
        evento.add('transp', 'TRANSPARENT')  # No ocupa slot horario
        evento.add('CATEGORIES', 'Categoría Roja') 
        
        cal.add_component(evento)

    asunto = f'Calendario del curso {lista_eventos[0]["titulo"].replace("INICIO DEL CURSO ", "")}'
    # Guardar archivo ICS
    nombre_archivo = f'{asunto.replace(" ", "_")}.ics'
    with open(nombre_archivo, 'wb') as f:
        f.write(cal.to_ical())

    asunto = f'Calendario del curso {lista_eventos[0]["titulo"].replace("INICIO DEL CURSO ", "")}'
    # CONFIGURACIÓN CORREO
    remitente = 'valenciacefire@gmail.com'
    # asunto = f'Calendario del curso {lista_eventos[0]["titulo"]}'
    cuerpo = f"""
Hola,

Adjunto el archivo .ics para el curso {lista_eventos[0]['titulo']} y sus eventos relacionados.:

Abre el adjunto para añadir TODOS los eventos a Outlook, Google Calendar, etc.

Saludos,

    """
    # ENVIAR CORREO con Mail
    with app.app_context():
        try:
            message = Message(
                subject=asunto,
                sender=remitente,
                recipients=[destinatario],
                body=cuerpo
            )
            
            # Adjuntar ICS
            with open(nombre_archivo, 'rb') as adjunto:
                message.attach(
                    filename=nombre_archivo,
                    content_type='text/calendar',
                    data=adjunto.read()
                )
            # Enviar correo
            mail.send(message)
            '''
            print("✅ Correo enviado correctamente")
            print(f"📅 {len(lista_eventos)} eventos enviados:")
            for evento in lista_eventos:
                print(f"   - {evento['titulo']} ({evento['fecha']})")
            '''
        except Exception as e:
            print(f"❌ Error: {e}")

        finally:
            # Limpiar archivo temporal
            if os.path.exists(nombre_archivo):
                os.remove(nombre_archivo)