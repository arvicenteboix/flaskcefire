from flask import Flask
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import smtplib

app = Flask(__name__)

# Configuració de Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] =  587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = ''
app.config['MAIL_PASSWORD'] = ''
app.config['MAIL_DEFAULT_SENDER'] = ''

mail = Mail(app)

# Llistat d'exemple de correus
EMAIL_LIST = [
    'alviboi@gmail.com',
    'tecnologiaindustrial@gmail.com',
]
def enviar_correus():
    """Funció que envia correus a tots els contactes"""
    with app.app_context():
        for email in EMAIL_LIST:
            msg = Message(
                subject='Recordatori',
                recipients=[email],
                body='Et recorde aquest correu'
            )
            mail.send(msg)
            print(f"Correu enviat a {email}")


# Configurar scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=enviar_correus, trigger='cron', hour=1, minute=0)
# scheduler.add_job(func=enviar_correus, trigger='interval', minutes=5)
scheduler.start()

# Aturar scheduler quan es tanci l'app
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def hello():
    return 'Worker de Flask en funcionament'

@app.route('/enviar')
def enviar():
    enviar_correus()
    return 'Correus enviats!'



if __name__ == '__main__':
    app.run(debug=True)