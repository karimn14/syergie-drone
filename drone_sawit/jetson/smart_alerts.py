"""
smart_alerts.py
Smart operator notification and escalation for Drone Sawit.
"""
import smtplib
from email.mime.text import MIMEText
import os

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.example.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USER = os.environ.get('EMAIL_USER', 'drone@domain.com')
EMAIL_PASS = os.environ.get('EMAIL_PASS', 'password')
EMAIL_TO = os.environ.get('EMAIL_TO', 'operator@domain.com')


def send_alert(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        print('Alert sent.')
    except Exception as e:
        print(f'Failed to send alert: {e}')

if __name__ == "__main__":
    send_alert('Drone Sawit Alert', 'Critical anomaly detected during mission.')
