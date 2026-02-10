from flask import Flask
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from datetime import datetime



# Llistat d'exemple de correus


def enviar_correus(app, conn):
    """Funció que envia correus a tots els contactes"""
    def envia(datos, tipo):
        with app.app_context():
            for formacion in datos:
                usuari = users[formacion['asesoria']]
                msg = Message(
                    subject=f'Recordatori: {formacion["titol"]} - {tipo}',
                    sender='valenciacefire@gmail.com',
                    recipients=[usuari['email']],
                    body=f"Hola {usuari['nombre']},\n\nEt recordem la formació: {formacion['codigo']} - {formacion['titol']} - demà estarà en estat: {tipo}.\n\nSalutacions,"
                )
                mail.send(msg)

    def envia_david(datos):
        with app.app_context():
            body = "Formacions que entren en inscripció demà:\n\n"
            for formacion in datos:
                body += f"Formació: {formacion['codigo']} - {formacion['titol']} - Data Inscripció: {formacion['data_insc']}\n"

            msg = Message(
                subject='Recordatori: Formacions en inscripció demà',
                sender='valenciacefire@gmail.com',
                recipients=['montalva_dav@gva.es'],
                body=body
            )
            mail.send(msg)


    print(datetime.now(), "Enviant correus...")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, email FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT * FROM formacio where data_ini = date('now', '+1 day')")
    hoy = cursor.fetchall()
    envia(hoy, "Inici")

    cursor.execute("SELECT * FROM formacio where data_insc = date('now', '+1 day')")
    inscripciones = cursor.fetchall()
    envia(inscripciones, "Inscripció")
    envia_david(inscripciones)


    cursor.execute("SELECT * FROM formacio where data_conf = date('now', '+1 day')")
    confirmaciones = cursor.fetchall()
    envia(confirmaciones, "Confirmació")

    cursor.execute("SELECT * FROM formacio where data_list = date('now', '+1 day')")
    listados = cursor.fetchall()
    envia(listados, "Llistat definitiu")

    








    '''
    cursor.execute("SELECT email FROM users where id=1")
    EMAIL_LIST = [row['email'] for row in cursor.fetchall()]
    print(f"Enviant correus a: {EMAIL_LIST}")

    with app.app_context():
        for email in EMAIL_LIST:
            msg = Message(
                subject='Recordatori',
                sender='valenciacefire@gmail.com',
                recipients=[email],
                body='Et recorde aquest correu, prova 2'
            )
            mail.send(msg)
            print(f"Correu enviat a {email}")
    '''


def init_mail_and_scheduler(app, conn):
    """Inicialitza Mail i el scheduler amb l'app de Flask."""
    global mail, scheduler
    mail = Mail(app)
    scheduler = BackgroundScheduler()
    # Inicialitzar Mail amb la configuració de app
    mail.init_app(app)
    # Configurar scheduler
    scheduler.add_job(func=lambda: enviar_correus(app, conn), trigger='cron', hour=4, minute=0)
    # scheduler.add_job(func=lambda: enviar_correus(app, conn), trigger='interval', seconds=10)  # Per a proves, envia cada minut
    scheduler.start()
    # Aturar scheduler quan es tanque l'app
    atexit.register(lambda: scheduler.shutdown(wait=False))
    return mail, scheduler