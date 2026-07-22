"""
fetch_gospel.py
Obtiene el Evangelio del día para la automatización "Evangelio de Hoy".

CAMBIO (22/7/2026): se reemplaza ACI Prensa como fuente PRINCIPAL por
Vatican News (vaticannews.va). Motivo: se detectó que ACI Prensa podía
tardar varias horas en publicar el contenido del día (más de las que
alcanza a cubrir un reintento corto), causando que la automatización de
las 4:30 a.m. mandara en silencio el Evangelio del día anterior.
Vatican News confirmado que publica el contenido del día siguiente desde
la noche anterior, con una fecha explícita ("FechaDD/MM/AAAA") que permite
validar sin ambigüedad que el contenido corresponde al día pedido.

Fuente principal:   Vatican News   (vaticannews.va/es/evangelio-de-hoy/AAAA/MM/DD.html)
Fuente de cruce:     Dominicos.org (dominicos.org/predicacion/evangelio-del-dia/hoy/)
Fuente de respaldo:  ACI Prensa    (solo si Vatican News falla del todo)
"""
import re
import sys
import time
import requests
from datetime import date
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EvangelioDiarioBot/1.0; +personal use)"
}
TIMEOUT = 20

MESES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre",
    12: "diciembre",
}


class FuenteNoDisponible(Exception):
    pass


def _get_text(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "svg"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


# ---------------------------------------------------------------------------
# FUENTE PRINCIPAL: Vatican News
# ---------------------------------------------------------------------------

def fetch_from_vaticannews(
    target_date: date,
    intentos: int = 3,
    espera_seg: int = 120,
) -> dict:
    """Fuente principal. Publica con mucha anticipación (confirmado: la
    noche anterior), por lo que no debería necesitar los reintentos largos
    que sí hacían falta con ACI Prensa. Se dejan igual como red de
    seguridad ante fallas transitorias de red."""
    y, m, d = target_date.year, target_date.month, target_date.day
    url = f"https://www.vaticannews.va/es/evangelio-de-hoy/{y}/{m:02d}/{d:02d}.html"
    fecha_esperada = f"{d:02d}/{m:02d}/{y}"

    ultimo_error = None
    for intento in range(1, intentos + 1):
        try:
            text = _get_text(url)
        except Exception as e:
            ultimo_error = f"error de red: {e}"
            print(f"[aviso] Vatican News intento {intento}/{intentos}: {ultimo_error}", file=sys.stderr)
            if intento < intentos:
                time.sleep(espera_seg)
            continue

        if re.search(r"Fecha\s*" + re.escape(fecha_esperada), text):
            try:
                return _parse_vaticannews(text, url)
            except FuenteNoDisponible as e:
                ultimo_error = str(e)
                print(f"[aviso] {ultimo_error} (intento {intento}/{intentos})", file=sys.stderr)
        else:
            ultimo_error = f"la página no muestra todavía 'Fecha{fecha_esperada}'"
            print(f"[aviso] Vatican News: {ultimo_error} (intento {intento}/{intentos})", file=sys.stderr)
            print(f"[debug] primeros 300 caracteres recibidos: {text[:300]!r}", file=sys.stderr)

        if intento < intentos:
            time.sleep(espera_seg)

    raise FuenteNoDisponible(
        f"Vatican News no dio el Evangelio de {target_date.isoformat()} "
        f"después de {intentos} intentos. Último aviso: {ultimo_error}"
    )


def _parse_vaticannews(text: str, url: str) -> dict:
    m_cel = re.search(r"Fecha\s*\d{2}/\d{2}/\d{4}\s*\n+([^\n]+)", text)
    celebracion = m_cel.group(1).strip() if m_cel else None

    m_ev = re.search(
        r"Evangelio del [Dd]ía\s*\n+"
        r"Lectura del santo evangelio según\s+(.+?)\s*\n+"
        r"([A-Za-zÁÉÍÓÚñáéíóú]+\s+\d+[^\n]*)\n+"
        r"(.*?)\n+"
        r"(?:Las palabras de los Papas|Palabras del Papa|$)",
        text,
        re.DOTALL,
    )
    if not m_ev:
        raise FuenteNoDisponible(f"No se pudo extraer el Evangelio de {url} (cambió el formato de la página)")

    evangelista = m_ev.group(1).strip()
    cita = m_ev.group(2).strip()
    cuerpo = re.sub(r"\s{2,}|\n+", " ", m_ev.group(3).strip()).strip()

    if not celebracion or not cita or not cuerpo:
        raise FuenteNoDisponible(f"Extracción incompleta de {url}")

    return {
        "fuente": "Vatican News",
        "url": url,
        "celebracion": celebracion,
        "evangelista": evangelista,
        "cita": cita,
        "texto": cuerpo,
    }


# ---------------------------------------------------------------------------
# FUENTE DE CRUCE: Dominicos.org
# ---------------------------------------------------------------------------

def _parse_dominicos(text_intro: str, text_lect: str, url_intro: str) -> dict:
    m_ciclo = re.search(
        r"Año litúrgico\s*([0-9]{4}\s*-\s*[0-9]{4})\s*-?\s*\(?Ciclo\s*([ABC])\)?",
        text_intro,
    )
    anio_liturgico = m_ciclo.group(1).strip() if m_ciclo else None
    ciclo = m_ciclo.group(2).strip() if m_ciclo else None

    m_ev = re.search(
        r"Evangelio del día\s*\n+"
        r"Lectura del santo evangelio según\s+(.+?)\n"
        r"(.*?)"
        r"\nDescargar",
        text_lect,
        re.DOTALL,
    )
    cita = cuerpo = None
    if m_ev:
        cita = m_ev.group(1).strip()
        cuerpo = re.sub(r"\n{1,}", " ", m_ev.group(2).strip())
        cuerpo = re.sub(r"\s{2,}", " ", cuerpo)

    return {
        "fuente": "Dominicos.org (Orden de Predicadores)",
        "url": url_intro,
        "anio_liturgico": anio_liturgico,
        "ciclo": ciclo,
        "cita": cita,
        "texto": cuerpo,
    }


def fetch_from_dominicos() -> dict:
    url_intro = "https://www.dominicos.org/predicacion/evangelio-del-dia/hoy/"
    url_lecturas = "https://www.dominicos.org/predicacion/evangelio-del-dia/hoy/lecturas/"
    text_intro = _get_text(url_intro)
    text_lect = _get_text(url_lecturas)
    return _parse_dominicos(text_intro, text_lect, url_intro)


# ---------------------------------------------------------------------------
# FUENTE DE RESPALDO (solo si Vatican News falla del todo): ACI Prensa
# ---------------------------------------------------------------------------

def _literales_fecha(target_date: date) -> list[str]:
    mes = MESES[target_date.month]
    return [
        f"{target_date.day} de {mes} de {target_date.year}",
        f"{target_date.day:02d} de {mes} de {target_date.year}",
    ]


def fetch_from_aciprensa(target_date: date) -> dict:
    """Respaldo de última instancia. NO se usa por defecto: ver aviso en
    verificar_y_obtener(). Se conserva por si Vatican News está caído."""
    url = f"https://www.aciprensa.com/calendario/{target_date.isoformat()}"
    text = _get_text(url)

    m_ev = re.search(
        r"\nEvangelio\s*\n"
        r"([A-ZÁÉÍÓÚa-záéíóúñ][A-Za-zÁÉÍÓÚñáéíóú0-9,:\.\-\s]*?)\n"
        r"(.*?)"
        r"(?:\nOR\n|\nÚltimas noticias|\Z)",
        text,
        re.DOTALL,
    )
    if not m_ev:
        raise FuenteNoDisponible(f"No se pudo extraer el Evangelio de {url}")

    cita = m_ev.group(1).strip()
    cuerpo = re.sub(r"(?m)^\s*\d{1,3}", "", m_ev.group(2).strip())
    cuerpo = re.sub(r"\n{1,}", " ", cuerpo).strip()
    cuerpo = re.sub(r"\s{2,}", " ", cuerpo)

    return {"fuente": "ACI Prensa (respaldo)", "url": url, "celebracion": None, "cita": cita, "texto": cuerpo}


# ---------------------------------------------------------------------------

def _normaliza_cita(cita: str) -> str:
    c = cita.lower().replace("san ", "").replace("según ", "")
    m = re.search(r"([a-záéíóúñ]+)\s+(\d+)", c)
    return f"{m.group(1)}{m.group(2)}" if m else c


def verificar_y_obtener(target_date: date) -> dict:
    """
    Trae Vatican News (principal), cruza con Dominicos.org, y solo si
    Vatican News falla del todo cae a ACI Prensa como último recurso.
    """
    try:
        principal = fetch_from_vaticannews(target_date)
    except FuenteNoDisponible as e:
        print(f"[aviso] Vatican News no disponible, usando ACI Prensa como respaldo: {e}", file=sys.stderr)
        principal = fetch_from_aciprensa(target_date)

    verificado = False
    segunda = None
    try:
        segunda = fetch_from_dominicos()
        if segunda.get("cita"):
            verificado = _normaliza_cita(principal["cita"]) == _normaliza_cita(segunda["cita"])
    except Exception as e:
        print(f"[aviso] segunda fuente no disponible: {e}", file=sys.stderr)

    return {
        "fecha": target_date.isoformat(),
        "celebracion": principal.get("celebracion"),
        "anio_liturgico": segunda.get("anio_liturgico") if segunda else None,
        "ciclo": segunda.get("ciclo") if segunda else None,
        "cita": principal["cita"],
        "texto": principal["texto"],
        "fuente_principal": {"nombre": principal["fuente"], "url": principal["url"]},
        "fuente_segunda": {"nombre": segunda["fuente"], "url": segunda["url"]} if segunda else None,
        "verificado_en_dos_fuentes": verificado,
    }


if __name__ == "__main__":
    d = date.today()
    import json
    print(json.dumps(verificar_y_obtener(d), ensure_ascii=False, indent=2))
