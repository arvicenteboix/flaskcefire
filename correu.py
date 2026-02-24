from flask import Flask
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from datetime import datetime



# Llistat d'exemple de correus
mail = None
scheduler = None

def enviar_correus(app, conn):
    """Funció que envia correus a tots els contactes"""
    
    def envia(datos, tipo):
        with app.app_context():
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
                print(f"  ✓ Enviat {tipo} a {usuari['nombre']} ({len(formacions)} formacions)")

    def envia_david(datos):
        with app.app_context():
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
    '''
    def envia_david(datos):
        print ("Execute david")

    def envia(datos, tipo):
        print(f"  ✓ Enviant {tipo} a {len(datos)} formacions...")
    '''
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