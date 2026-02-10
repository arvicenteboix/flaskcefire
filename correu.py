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
                    body=f"Hola {usuari['nombre']},\n\nEt recordem la formació: {formacion['codigo']} - {formacion['titol']} - a dia de hui està en estat: {tipo}.\n\nSalutacions,"
                )
                mail.send(msg)

    def envia_david(datos):
        with app.app_context():
            body = "Formacions que entren en inscripció a dia de hui:\n\n"
            for formacion in datos:
                body += f"Formació: {formacion['codigo']} - {formacion['titol']} - Data Inscripció: {formacion['data_insc']}\n"

            msg = Message(
                subject='Recordatori: Formacions en inscripció a dia de hui',
                sender='valenciacefire@gmail.com',
                recipients=['ar.vicenteboix@gva.es'],
                body=body
            )
            mail.send(msg)


    print(datetime.now(), "Enviant correus...")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, email FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT * FROM formacio where data_ini = date('now')")
    hoy = cursor.fetchall()
    if len(hoy) > 0:
        envia(hoy, "Inici")

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
    mail = Mail(app)
    scheduler = BackgroundScheduler()
    # Inicialitzar Mail amb la configuració de app
    mail.init_app(app)
    # Configurar scheduler
    scheduler.add_job(func=lambda: enviar_correus(app, conn), trigger='cron', hour=1, minute=0)
    # scheduler.add_job(func=lambda: enviar_correus(app, conn), trigger='interval', seconds=10)  # Per a proves, envia cada minut
    scheduler.start()
    # Aturar scheduler quan es tanque l'app
    atexit.register(lambda: scheduler.shutdown(wait=False))
    return mail, scheduler