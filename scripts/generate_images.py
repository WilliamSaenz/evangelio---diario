"""
generate_images.py
Genera las 4 ilustraciones de la lámina (header, teología, psicología,
neurociencia) con Pollinations.ai, modelo Flux — gratis e ilimitado,
sin API key, sin cuenta.

Endpoint: GET https://image.pollinations.ai/prompt/{prompt}
"""
import hashlib
from datetime import date
from urllib.parse import quote

import requests

BASE_URL = "https://image.pollinations.ai/prompt/"

ESTILO_COMUN = (
    ", warm editorial illustration style, painterly, historically accurate "
    "biblical-era setting, no modern objects, no text or letters in the "
    "image, consistent warm color palette, correct anatomy, no photo, no "
    "anime, no 3d render"
)


class ImagenError(Exception):
    pass


def _seed_para(fecha: date, slot: str) -> int:
    """Seed determinístico por fecha+slot: mismo dia -> misma imagen si se
    reintenta, distinto slot -> imagen distinta."""
    base = f"{fecha.isoformat()}-{slot}"
    return int(hashlib.sha256(base.encode()).hexdigest(), 16) % (2**31)


def generar_imagen(prompt: str, fecha: date, slot: str, width: int, height: int) -> bytes:
    prompt_final = prompt.strip() + ESTILO_COMUN
    url = BASE_URL + quote(prompt_final)
    params = {
        "width": width,
        "height": height,
        "nologo": "true",
        "model": "flux",
        "seed": _seed_para(fecha, slot),
    }
    resp = requests.get(url, params=params, timeout=120)
    if resp.status_code != 200 or not resp.content:
        raise ImagenError(f"Pollinations respondió {resp.status_code} para slot '{slot}'")
    return resp.content


def generar_todas(contenido: dict, fecha: date) -> dict:
    """Devuelve dict slot -> bytes de imagen para los 4 huecos de la lámina."""
    specs = {
        "header": (contenido["imagen_header"], 900, 540),
        "teologia": (contenido["imagen_teologia"], 700, 500),
        "psicologia": (contenido["imagen_psicologia"], 700, 500),
        "neurociencia": (contenido["imagen_neurociencia"], 700, 500),
    }
    imagenes = {}
    for slot, (prompt, w, h) in specs.items():
        imagenes[slot] = generar_imagen(prompt, fecha, slot, w, h)
    return imagenes
