"""
Generación de las 5 ilustraciones de la lámina con Pollinations.ai (modelo Flux).

Gratis, sin cuenta ni API key. Devuelve las imágenes en base64 listas para
embeber en el HTML (así el render no depende de que la red siga viva).

Las 5 imágenes son: header, teología, psicología, neurociencia y cierre.
La de cierre es siempre una escena distinta de Jesús mostrando misericordia.
"""

from __future__ import annotations

import base64
import time
import urllib.parse
from datetime import date

import requests

from config import (
    HTTP_TIMEOUT,
    IMG_CIERRE,
    IMG_COLUMNA,
    IMG_HEADER,
    IMG_REINTENTOS,
    POLLINATIONS_URL,
)

TAMANOS = {
    "header": IMG_HEADER,
    "teologia": IMG_COLUMNA,
    "psicologia": IMG_COLUMNA,
    "neurociencia": IMG_COLUMNA,
    "cierre": IMG_CIERRE,
}

# Color de relleno por bloque, para el caso en que una imagen no se pueda
# generar: la lámina sale igual, con un panel liso en lugar de un hueco roto.
FALLBACK = {
    "header": "#c9a227",
    "teologia": "#a3c48a",
    "psicologia": "#8fb8dd",
    "neurociencia": "#4a2069",
    "cierre": "#c9a227",
}


def _semilla(fecha: date, clave: str) -> int:
    """
    Semilla determinística por día y por bloque.

    Misma fecha => mismas imágenes si hay que reintentar la corrida entera,
    pero días distintos => imágenes distintas. Y los 5 bloques nunca comparten
    semilla, así no salen parecidos entre sí.
    """
    base = fecha.toordinal() * 7
    return (base + sum(ord(c) for c in clave)) % 1_000_000


def _placeholder(clave: str) -> str:
    """SVG liso en base64, del color del bloque."""
    w, h = TAMANOS[clave]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
        f'<rect width="100%" height="100%" fill="{FALLBACK[clave]}"/></svg>'
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _generar_una(prompt: str, clave: str, fecha: date) -> str:
    w, h = TAMANOS[clave]
    url = POLLINATIONS_URL.format(prompt=urllib.parse.quote(prompt, safe=""))
    params = {
        "width": w,
        "height": h,
        "model": "flux",
        "nologo": "true",
        "private": "true",
        "seed": _semilla(fecha, clave),
    }

    for intento in range(1, IMG_REINTENTOS + 1):
        try:
            r = requests.get(url, params=params, timeout=HTTP_TIMEOUT * 4)
            tipo = r.headers.get("Content-Type", "")
            if r.status_code == 200 and tipo.startswith("image/") and len(r.content) > 2000:
                b64 = base64.b64encode(r.content).decode("ascii")
                print(f"    ✓ {clave} ({len(r.content) // 1024} KB)")
                return f"data:{tipo.split(';')[0]};base64,{b64}"
            print(f"    ✗ {clave}: HTTP {r.status_code}, tipo {tipo!r}")
        except requests.RequestException as e:
            print(f"    ✗ {clave}: {e}")
        if intento < IMG_REINTENTOS:
            time.sleep(6 * intento)

    print(f"    ⚠ {clave}: se usa panel liso de reemplazo")
    return _placeholder(clave)


def generar_imagenes(prompts: dict, fecha: date) -> dict:
    """prompts: dict con las 5 claves. Devuelve dict clave -> data URI."""
    print("  → generando ilustraciones (Pollinations / Flux)")
    imagenes = {}
    for clave in ("header", "teologia", "psicologia", "neurociencia", "cierre"):
        imagenes[clave] = _generar_una(prompts[clave], clave, fecha)
    return imagenes


if __name__ == "__main__":
    from format_message import hoy_ar

    demo = {
        k: f"a simple test illustration for {k}, warm tones"
        for k in TAMANOS
    }
    res = generar_imagenes(demo, hoy_ar())
    for k, v in res.items():
        print(k, len(v), "caracteres base64")
