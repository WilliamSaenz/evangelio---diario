"""
Generación del contenido de la lámina con Gemini.

Fix del bug del "JSON inválido / respuesta cortada": en vez de pedirle a Gemini
que "responda solo JSON" y cruzar los dedos, se usa salida estructurada real
(responseMimeType + responseSchema). Con eso la API garantiza JSON válido y
conforme al esquema; ya no hay que limpiar backticks ni parsear a mano.
"""

from __future__ import annotations

import json
import os
import time

import requests

from config import (
    ESTILO_ILUSTRACION,
    GEMINI_MAX_TOKENS,
    GEMINI_MODELO,
    GEMINI_REINTENTOS,
    GEMINI_URL,
    HTTP_TIMEOUT,
    ICONOS,
)
from fetch_gospel import Evangelio
from format_message import fecha_larga

# ---------------------------------------------------------------------------
# Esquema de la respuesta
# ---------------------------------------------------------------------------

_BLOQUE = {
    "type": "object",
    "properties": {
        "texto": {"type": "string"},
        "frase_destacada": {"type": "string"},
        "fuente": {"type": "string"},
    },
    "required": ["texto", "frase_destacada", "fuente"],
}

ESQUEMA = {
    "type": "object",
    "properties": {
        "idea_central": {"type": "string"},
        "frase_clave": {"type": "string"},
        "teologia": _BLOQUE,
        "psicologia": _BLOQUE,
        "neurociencia": _BLOQUE,
        "practicas": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string"},
                    "descripcion": {"type": "string"},
                    "icono": {"type": "string", "enum": sorted(ICONOS.keys())},
                },
                "required": ["titulo", "descripcion", "icono"],
            },
        },
        "imagenes": {
            "type": "object",
            "properties": {
                "header": {"type": "string"},
                "teologia": {"type": "string"},
                "psicologia": {"type": "string"},
                "neurociencia": {"type": "string"},
                "cierre": {"type": "string"},
            },
            "required": ["header", "teologia", "psicologia", "neurociencia", "cierre"],
        },
    },
    "required": [
        "idea_central",
        "frase_clave",
        "teologia",
        "psicologia",
        "neurociencia",
        "practicas",
        "imagenes",
    ],
}


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def construir_prompt(ev: Evangelio) -> str:
    iconos = ", ".join(sorted(ICONOS.keys()))
    return f"""Sos un teólogo católico que además domina psicología clínica basada en evidencia y neurociencia. Preparás una lámina diaria de meditación del Evangelio.

EVANGELIO DEL DÍA — {fecha_larga(ev.fecha)}
Cita: {ev.cita.bonita()}
{f"Tiempo litúrgico: {ev.titulo_liturgico}" if ev.titulo_liturgico else ""}

Texto completo:
\"\"\"
{ev.texto}
\"\"\"

TAREA
Elegí UNA sola idea central de este Evangelio y desarrollala. Todo lo que generes tiene que salir de ESTE Evangelio en particular, no de generalidades cristianas que servirían para cualquier día.

1. idea_central: una frase que resuma la idea que elegiste.

2. frase_clave: la frase MÁS IMPORTANTE del Evangelio, copiada LITERAL Y EXACTAMENTE del texto de arriba, carácter por carácter, sin reescribir ni acortar ni cambiar puntuación. Entre 8 y 30 palabras. Se va a usar para resaltarla dentro del texto original, así que si no es idéntica no va a funcionar.

3. teologia / psicologia / neurociencia: para cada una,
   - texto: 2 oraciones como máximo, unas 25 palabras. Claro, concreto, sin jerga.
     Si dudás entre una versión más corta y una más completa, elegí SIEMPRE la más corta.
   - frase_destacada: una frase breve y potente que condense el bloque (máximo 10 palabras).
   - fuente: una referencia bibliográfica REAL y verificable, en formato APA abreviado.

   Teología: solo Sagrada Escritura, Catecismo, Padres o Doctores de la Iglesia,
   o Magisterio pontificio. Nada de blogs ni frases anónimas.
   Psicología: literatura clínica basada en evidencia (atención, regulación
   emocional, hábitos, motivación, decisiones, vínculos). Nada de autoayuda y
   ningún diagnóstico.
   Neurociencia: investigación real sobre neuroplasticidad, atención, memoria o
   emoción, con lenguaje prudente ("puede favorecer…", "se asocia con…", "la
   evidencia sugiere…"). Nada de neuromitos ni de cambios inmediatos.

   NO INVENTES fuentes. Si no estás seguro de una referencia específica, usá una
   más genérica pero verdadera (por ejemplo "Catecismo de la Iglesia Católica",
   sin número de párrafo) antes que inventar autor, obra, año o número.

4. practicas: exactamente 3 acciones concretas para hacer HOY, atadas a esta idea central.
   - titulo: 1 o 2 palabras, en imperativo (ej: "Ordenar", "Escuchar", "Soltar").
   - descripcion: una oración de unas 12 palabras, concreta y realizable en el día.
   - icono: elegí de esta lista el que mejor represente la práctica: {iconos}
   Las 3 prácticas deben variar según el Evangelio de hoy y usar 3 iconos DISTINTOS entre sí.

5. imagenes: prompts en INGLÉS para generar 5 ilustraciones. Cada una tiene que describir una escena visual concreta y DISTINTA de las otras cuatro.
   - header: la escena principal de este Evangelio.
   - teologia / psicologia / neurociencia: una imagen que evoque el contenido de cada bloque, ligada al Evangelio.
   - cierre: una escena de Jesús mostrando misericordia con alguien concreto — abrazando a una persona, acogiendo a un chico, levantando a alguien caído. Distinta de las otras cuatro.
   Cada prompt: una sola oración descriptiva, sin texto ni letras en la imagen, sin nombres de artistas.

Escribí todo en español rioplatense neutro, salvo los prompts de imagen que van en inglés."""


# ---------------------------------------------------------------------------
# Llamada a la API
# ---------------------------------------------------------------------------


def _llamar_gemini(prompt: str, api_key: str) -> dict:
    url = GEMINI_URL.format(modelo=GEMINI_MODELO)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": GEMINI_MAX_TOKENS,
            # Esto es lo que garantiza JSON válido:
            "responseMimeType": "application/json",
            "responseSchema": ESQUEMA,
        },
    }
    r = requests.post(
        url,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        json=payload,
        timeout=HTTP_TIMEOUT * 3,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:500]}")

    data = r.json()
    candidatos = data.get("candidates") or []
    if not candidatos:
        raise RuntimeError(f"Gemini no devolvió candidatos: {json.dumps(data)[:500]}")

    cand = candidatos[0]
    motivo = cand.get("finishReason")
    if motivo not in (None, "STOP"):
        raise RuntimeError(f"Gemini cortó la respuesta (finishReason={motivo})")

    partes = cand.get("content", {}).get("parts") or []
    crudo = "".join(p.get("text", "") for p in partes).strip()
    if not crudo:
        raise RuntimeError("Gemini devolvió una respuesta vacía")

    return json.loads(crudo)


def _validar(contenido: dict, ev: Evangelio) -> dict:
    """Chequeos que el esquema no puede hacer solo."""
    # La frase clave tiene que existir de verdad dentro del Evangelio.
    frase = " ".join(contenido["frase_clave"].split())
    texto_plano = " ".join(ev.texto.split())
    if frase not in texto_plano:
        print("  ⚠ frase_clave no coincide literal con el texto; se buscará aproximada")

    # Iconos distintos entre sí.
    usados = [p["icono"] for p in contenido["practicas"]]
    if len(set(usados)) < 3:
        libres = [k for k in sorted(ICONOS) if k not in usados]
        for i, p in enumerate(contenido["practicas"]):
            if usados.count(p["icono"]) > 1 and libres:
                p["icono"] = libres.pop(0)
                usados[i] = p["icono"]
        print("  ⚠ iconos repetidos; se reasignaron")

    # Estilo común a todos los prompts de imagen.
    for k, v in contenido["imagenes"].items():
        contenido["imagenes"][k] = f"{v.rstrip('. ')}. {ESTILO_ILUSTRACION}"

    return contenido


def generar_contenido(ev: Evangelio, api_key: str | None = None) -> dict:
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta la variable de entorno GEMINI_API_KEY")

    prompt = construir_prompt(ev)
    ultimo_error: Exception | None = None

    for intento in range(1, GEMINI_REINTENTOS + 1):
        print(f"  → Gemini ({GEMINI_MODELO}), intento {intento}/{GEMINI_REINTENTOS}")
        try:
            contenido = _llamar_gemini(prompt, api_key)
            print(f"    ✓ idea central: {contenido['idea_central']}")
            return _validar(contenido, ev)
        except Exception as e:  # noqa: BLE001 — queremos reintentar ante cualquier cosa
            ultimo_error = e
            print(f"    ✗ {e}")
            if intento < GEMINI_REINTENTOS:
                time.sleep(5 * intento)

    raise RuntimeError(f"Gemini falló tras {GEMINI_REINTENTOS} intentos: {ultimo_error}")


if __name__ == "__main__":
    from fetch_gospel import obtener_evangelio
    from format_message import hoy_ar

    evangelio = obtener_evangelio(hoy_ar())
    print(json.dumps(generar_contenido(evangelio), ensure_ascii=False, indent=2))
