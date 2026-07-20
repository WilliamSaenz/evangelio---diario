"""
send_email.py
Envía el mensaje final por correo (Gmail SMTP, gratis, sin límites
relevantes para 1 envío diario — hasta 500 correos/día en el plan free).

Requiere las variables de entorno:
  GMAIL_USER          -> tu dirección de Gmail que envía
                          (ej: williamsaenz343@gmail.com)
  GMAIL_APP_PASSWORD  -> contraseña de aplicación de 16 caracteres,
                          generada en myaccount.google.com/security
                          (Verificación en 2 pasos > Contraseñas de app)
  EMAIL_TO            -> dirección de correo que recibe la lámina
"""
import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


class EnvioError(Exception):
    pass


def enviar_email(
    imagen_bytes: bytes,
    asunto: str,
    cuerpo: str = "",
    mimetype: str = "image/png",
    nombre_archivo: str = "evangelio_hoy.png",
    remitente: str | None = None,
    password: str | None = None,
    destino: str | None = None,
) -> dict:
    remitente = remitente or os.environ["GMAIL_USER"]
    password = password or os.environ["GMAIL_APP_PASSWORD"]
    destino = destino or os.environ["EMAIL_TO"]

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = remitente
    msg["To"] = destino
    msg.set_content(cuerpo or "Adjunto la lámina del Evangelio de Hoy.")

    maintype, subtype = mimetype.split("/")
    msg.add_attachment(
        imagen_bytes,
        maintype=maintype,
        subtype=subtype,
        filename=nombre_archivo,
    )

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.login(remitente, password)
            server.send_message(msg)
    except smtplib.SMTPException as e:
        raise EnvioError(f"Error enviando por Gmail: {e}") from e

    return {"enviado": True, "to": destino}
