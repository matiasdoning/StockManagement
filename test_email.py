import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
import certifi

sender_email = os.environ.get("EMAIL_USER")
sender_password = os.environ.get("EMAIL_PASS")
recipient_email = os.environ.get("EMAIL_USER")

msg = MIMEMultipart("alternative")
msg["Subject"] = "🟢 Test Email - It Works!"
msg["From"] = sender_email
msg["To"] = recipient_email
body = "✅ This is a test email from GitHub Actions. It works!"
msg.attach(MIMEText(body, "plain"))

context = ssl.create_default_context(cafile=certifi.where())
with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
    server.login(sender_email, sender_password)
    server.send_message(msg)

print("📨 Test email sent successfully!")
