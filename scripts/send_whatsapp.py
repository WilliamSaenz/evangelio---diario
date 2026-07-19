"""
send_whatsapp.py
Envía el mensaje final por WhatsApp usando Wappfly (wappfly.com),
plan gratuito (sin tarjeta, ~50 mensajes/mes — de sobra para 1 por dia).

Requiere las variables de entorno:
  WAPPFLY_TOKEN   -> token de tu sesion (dashboard de Wappfly, tras
                     vincular tu numero con el codigo QR)
  WHATSAPP_TO     -> tu numero, con codigo de pais, SIN "+" ni espacios
                     (ej: 5491122334455)
"""
import base64
import os
import requests

WAPPFLY_URL_TEXTO = "https://wappfly.com/api/messages/send"
WAPPFLY_URL_IMAGEN = "https://wappfly.com/api/messages/image"


class EnvioError(Exception):
    pass


def enviar_mensaje(texto: str, token: str | None = None, destino: str | None = None) -> dict:
    token = token or os.environ["WAPPFLY_TOKEN"]
    destino = destino or os.environ["WHATSAPP_TO"]

    payload = {
        "to": f"{destino}@s.whatsapp.net",
        "text": texto,
    }
    headers = {
        "X-API-Token": token,
        "Content-Type": "application/json",
    }

    resp = requests.post(WAPPFLY_URL_TEXTO, headers=headers, json=payload, timeout=30)
    if resp.status_code not in (200, 201, 202):
        raise EnvioError(f"Wappfly respondió {resp.status_code}: {resp.text[:500]}")
    return resp.json() if resp.content else {}


def enviar_imagen(
    imagen_bytes: bytes,
    caption: str = "",
    mimetype: str = "image/png",
    token: str | None = None,
    destino: str | None = None,
) -> dict:
    token = token or os.environ["WAPPFLY_TOKEN"]
    destino = destino or os.environ["WHATSAPP_TO"]

    payload = {
        "to": f"{destino}@s.whatsapp.net",
        "file": base64.b64encode(imagen_bytes).decode("ascii"),
        "caption": caption,
        "mimetype": mimetype,
    }
    headers = {
        "X-API-Token": token,
        "Content-Type": "application/json",
    }

    resp = requests.post(WAPPFLY_URL_IMAGEN, headers=headers, json=payload, timeout=60)
    if resp.status_code not in (200, 201, 202):
        raise EnvioError(f"Wappfly (imagen) respondió {resp.status_code}: {resp.text[:500]}")
    return resp.json() if resp.content else {}
