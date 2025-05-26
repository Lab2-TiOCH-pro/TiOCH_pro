import smtplib
from email.mime.text import MIMEText
from django.conf import settings

class EmailService:
    @staticmethod
    def send(to: str, subject: str, content: str) -> dict:
        msg = MIMEText(content)
        msg['Subject'] = subject
        msg['From'] = settings.DEFAULT_FROM_EMAIL
        msg['To'] = to
        
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.DEFAULT_FROM_EMAIL, to, msg.as_string())
        
        return {'status': 'success'}