import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("GOOGLEPASSWORD")

def send_email(subject, body, to_email):
    # msg = MIMEMultipart()
    # msg['From'] = EMAIL
    # msg['To'] = to_email
    # msg['Subject'] = subject

    # msg.attach(MIMEText(body, 'plain'))

    # try:
    #     server = smtplib.SMTP('smtp.gmail.com', 587)
    #     server.starttls()
    #     server.login(EMAIL, PASSWORD)
    #     text = msg.as_string()
    #     server.sendmail(EMAIL, to_email, text)
    #     print(f"Email sent to {to_email} ✅")
    # except Exception as e:
    #     print(f"Failed to send email: {e}")
    # finally:
    #     server.quit()
    pass