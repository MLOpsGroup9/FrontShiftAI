import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "email_config.json"

def send_email(subject: str, message: str):
    print(f"🔍 Looking for config file at: {CONFIG_PATH}")
    if not CONFIG_PATH.exists():
        print("❌ Config file not found!")
        return

    with open(CONFIG_PATH, "r") as f:
        creds = json.load(f)

    sender = creds.get("sender")
    password = creds.get("password")
    receiver = creds.get("receiver")

    print(f"📧 Attempting to send email via Gmail SSL...")
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    try:
        # First try SSL (port 465)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(sender, password)
            server.send_message(msg)
        print(f"✅ Email sent successfully to {receiver} using SSL (465)")
        return
    except Exception as e:
        print(f"⚠️ SSL failed: {e}, retrying with STARTTLS (587)...")

    try:
        # Fallback to STARTTLS (port 587)
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        print(f"✅ Email sent successfully to {receiver} using STARTTLS (587)")
    except Exception as e:
        print(f"❌ Failed to send email via both SSL and TLS: {e}")

if __name__ == "__main__":
    send_email("FrontShiftAI Test Email", "This is a test email from your local ML pipeline.")
