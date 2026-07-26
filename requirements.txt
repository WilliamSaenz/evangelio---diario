"""
Envío de la lámina por email (Gmail SMTP).

Nota importante sobre GitHub Actions: un secret que NO existe no llega como
variable ausente, llega como CADENA VACÍA. Por eso acá nunca se usa
os.environ.get(x, default): siempre se lee y recién si el valor viene vacío se
aplica el default. Con el patrón ingenuo, int(os.environ.get("SMTP_PORT","465"))
levanta ValueError cuando el secret no está cargado.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path


def _env(nombre: str, defecto: str = "") -> str:
    """Lee una variable de entorno tratando la cadena vacía como ausente."""
    valor = os.environ.get(nombre)
    return valor.strip() if valor and valor.strip() else defecto


def _config() -> tuple[str, str, str, str, int]:
    usuario = _env("SMTP_USER")
    clave = _env("SMTP_PASS")
    destino = _env("EMAIL_TO") or usuario
    host = _env("SMTP_HOST", "smtp.gmail.com")
    puerto_txt = _env("SMTP_PORT", "465")

    faltan = [n for n, v in (("SMTP_USER", usuario), ("SMTP_PASS", clave)) if not v]
    if faltan:
        raise RuntimeError(
            f"Faltan secrets: {', '.join(faltan)}. "
            "Cargalos en Settings → Secrets and variables → Actions."
        )

    try:
        puerto = int(puerto_txt)
    except ValueError:
        raise RuntimeError(
            f"SMTP_PORT tiene un valor no numérico ({puerto_txt!r}). "
            "Dejá el secret sin crear para usar 465, o cargá 465 o 587."
        ) from None

    # Gmail rechaza las contraseñas de cuenta: exige contraseña de aplicación,
    # que son 16 letras (se muestra en 4 grupos de 4, pero se pega sin espacios).
    if "gmail" in host and len(clave.replace(" ", "")) != 16:
        print(
            "    ⚠ SMTP_PASS no parece una contraseña de aplicación de Google "
            f"(tiene {len(clave.replace(' ', ''))} caracteres, se esperan 16). "
            "Si el login falla, ese es el motivo."
        )

    return usuario, clave.replace(" ", ""), destino, host, puerto


def _conectar(host: str, puerto: int, usuario: str, clave: str):
    contexto = ssl.create_default_context()
    if puerto == 465:
        servidor = smtplib.SMTP_SSL(host, puerto, context=contexto, timeout=60)
    else:
        servidor = smtplib.SMTP(host, puerto, timeout=60)
        servidor.starttls(context=contexto)
    try:
        servidor.login(usuario, clave)
    except smtplib.SMTPAuthenticationError as e:
        servidor.close()
        raise RuntimeError(
            f"Gmail rechazó el login de {usuario}. Causas habituales: "
            "la contraseña no es una contraseña de aplicación, o la cuenta no "
            f"tiene la verificación en 2 pasos activada. Respuesta: {e.smtp_code} "
            f"{e.smtp_error!r}"
        ) from None
    return servidor


def enviar_lamina(imagen: Path, asunto: str, resumen: str) -> None:
    usuario, clave, destino, host, puerto = _config()

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = usuario
    msg["To"] = destino

    cid = make_msgid()[1:-1]
    msg.set_content(
        f"{resumen}\n\nLa lámina va adjunta como PNG.\n"
        "(Si ves este texto, tu cliente de correo no muestra HTML.)"
    )
    msg.add_alternative(
        f"""<html><body style="margin:0;padding:16px;background:#fbf6ec;
        font-family:Helvetica,Arial,sans-serif;color:#2b2620">
        <p style="font-size:15px;margin:0 0 14px">{resumen}</p>
        <img src="cid:{cid}" style="width:100%;max-width:640px;
             border-radius:10px;display:block">
        <p style="font-size:13px;color:#767267;margin:14px 0 0">
        También va adjunta en calidad completa para subir al estado.</p>
        </body></html>""",
        subtype="html",
    )

    datos = imagen.read_bytes()
    # payload[1] es la parte HTML; add_related la convierte en multipart/related
    # para que la imagen se vea embebida en el cuerpo del correo.
    msg.get_payload()[1].add_related(
        datos, maintype="image", subtype="png", cid=f"<{cid}>"
    )
    # Y además adjunta, para poder guardarla y subirla al estado.
    msg.add_attachment(datos, maintype="image", subtype="png", filename=imagen.name)

    with _conectar(host, puerto, usuario, clave) as servidor:
        servidor.send_message(msg)

    print(f"    ✓ correo enviado a {destino} ({len(datos) // 1024} KB)")


def enviar_alerta(motivo: str) -> None:
    """Aviso cuando la corrida falla, para no enterarte por ausencia."""
    try:
        usuario, clave, destino, host, puerto = _config()
    except RuntimeError as e:
        print(f"    (no se pudo avisar del fallo: {e})")
        return

    msg = EmailMessage()
    msg["Subject"] = "⚠ Evangelio de Hoy — la lámina de hoy no se generó"
    msg["From"] = usuario
    msg["To"] = destino
    msg.set_content(
        "La corrida de hoy falló y no se generó la lámina.\n\n"
        f"Motivo:\n{motivo}\n\n"
        "Revisá el log en la pestaña Actions del repo."
    )

    try:
        with _conectar(host, puerto, usuario, clave) as servidor:
            servidor.send_message(msg)
        print("    ✓ aviso de fallo enviado")
    except Exception as e:  # noqa: BLE001
        print(f"    (no se pudo enviar el aviso: {e})")


if __name__ == "__main__":
    # Chequeo de configuración sin enviar nada.
    try:
        usuario, _, destino, host, puerto = _config()
        print(f"Config OK: {usuario} → {destino} vía {host}:{puerto}")
    except RuntimeError as e:
        print(f"Config incompleta: {e}")
