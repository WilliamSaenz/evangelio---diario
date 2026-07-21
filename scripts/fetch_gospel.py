"""
fetch_gospel.py
Obtiene el Evangelio del día desde dos fuentes católicas independientes
y las cruza para verificación, tal como exige el prompt maestro.

Fuente principal:  ACI Prensa   (aciprensa.com/calendario/YYYY-MM-DD)
Segunda fuente:     Dominicos.org (dominicos.org/predicacion/evangelio-del-dia/hoy/)

Ambas son páginas HTML públicas, sin API key, sin costo.

CAMBIO (21/7/2026): se agrega verificación de que el contenido devuelto por
ACI Prensa realmente corresponda a la fecha pedida (buscando el literal
"D de mes de AAAA" dentro del texto de la página) y reintentos con espera si
todavía no coincide. Esto evita que, si el sitio no actualizó su contenido
al momento exacto de la corrida (p. ej. muy temprano a la mañana), la
automatización mande en silencio el Evangelio de un día anterior.
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


def _literales_fecha(target_date: date) -> list[str]:
    """Formas aceptadas de la fecha en español tal como aparece en ACI Prensa,
    p. ej. '21 de julio de 2026' y '9 de julio de 2026' / '09 de julio de 2026'."""
    mes = MESES[target_date.month]
    dia_sin_cero = str(target_date.day)
    dia_con_cero = f"{target_date.day:02d}"
    anio = target_date.year
    return [
        f"{dia_sin_cero} de {mes} de {anio}",
        f"{dia_con_cero} de {mes} de {anio}",
    ]


def _fecha_coincide(text: str, target_date: date) -> bool:
    texto_lower = text.lower()
    return any(lit in texto_lower for lit in _literales_fecha(target_date))


def fetch_from_aciprensa(
    target_date: date,
    intentos: int = 3,
    espera_seg: int = 240,
) -> dict:
    """Fuente principal. Devuelve celebracion, color, cita, texto, url.

    Reintenta si la página todavía no muestra el literal de la fecha pedida
    (caso típico: el sitio no roló al día nuevo cuando corremos muy temprano).
    """
    url = f"https://www.aciprensa.com/calendario/{target_date.isoformat()}"

    ultimo_error = None
    for intento in range(1, intentos + 1):
        text = _get_text(url)
        if _fecha_coincide(text, target_date):
            return _parse_aciprensa(text, url)
        ultimo_error = (
            f"El contenido de {url} no muestra la fecha esperada "
            f"({_literales_fecha(target_date)[0]}) — intento {intento}/{intentos}"
        )
        print(f"[aviso] {ultimo_error}", file=sys.stderr)
        if intento < intentos:
            time.sleep(espera_seg)

    raise FuenteNoDisponible(
        f"ACI Prensa no mostró el Evangelio de {target_date.isoformat()} "
        f"después de {intentos} intentos. Último aviso: {ultimo_error}"
    )


def _parse_aciprensa(text: str, url: str) -> dict:
    m_cel = re.search(
        r"\n([^\n]{3,80})\n+"
        r"[a-záéíóúñ]+ \d{1,2},\s*\d{4}\n+"
        r"«\s*Día anterior",
        text,
        re.IGNORECASE,
    )
    celebracion = m_cel.group(1).strip() if m_cel else None

    m_color = re.search(r"Color:\s*([A-Za-zÁÉÍÓÚñáéíóú]+)", text)
    color = m_color.group(1).strip() if m_color else None

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
    cuerpo_crudo = m_ev.group(2).strip()
    cuerpo = re.sub(r"(?m)^\s*\d{1,3}", "", cuerpo_crudo)
    cuerpo = re.sub(r"\n{1,}", " ", cuerpo).strip()
    cuerpo = re.sub(r"\s{2,}", " ", cuerpo)

    if not celebracion or not cita or not cuerpo:
        raise FuenteNoDisponible(f"Extracción incompleta de {url}")

    return {
        "fuente": "ACI Prensa",
        "url": url,
        "celebracion": celebracion,
        "color_liturgico": color,
        "cita": cita,
        "texto": cuerpo,
    }


def _parse_dominicos(text_intro: str, text_lect: str, url_intro: str) -> dict:
    m_ciclo = re.search(
        r"Año litúrgico\s*([0-9]{4}\s*-\s*[0-9]{4})\s*-?\s*\(?Ciclo\s*([ABC])\)?",
        text_intro,
    )
    anio_liturgico = m_ciclo.group(1).strip() if m_ciclo else None
    ciclo = m_ciclo.group(2).strip() if m_ciclo else None

    m_cel = re.search(r"Homilía\s+(.+)", text_intro)
    celebracion = m_cel.group(1).strip() if m_cel else None

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
        "celebracion": celebracion,
        "anio_liturgico": anio_liturgico,
        "ciclo": ciclo,
        "cita": cita,
        "texto": cuerpo,
    }


def fetch_from_dominicos() -> dict:
    """Segunda fuente (verificación). Usa el endpoint 'hoy' del sitio."""
    url_intro = "https://www.dominicos.org/predicacion/evangelio-del-dia/hoy/"
    url_lecturas = "https://www.dominicos.org/predicacion/evangelio-del-dia/hoy/lecturas/"

    text_intro = _get_text(url_intro)
    text_lect = _get_text(url_lecturas)
    return _parse_dominicos(text_intro, text_lect, url_intro)


def _normaliza_cita(cita: str) -> str:
    """Normaliza 'Mateo 10:7-15' / 'san Mateo 10, 7-15' -> 'mateo 10'."""
    c = cita.lower()
    c = c.replace("san ", "").replace("según ", "")
    m = re.search(r"([a-záéíóúñ]+)\s+(\d+)", c)
    return f"{m.group(1)}{m.group(2)}" if m else c


def verificar_y_obtener(target_date: date) -> dict:
    """
    Trae ambas fuentes, verifica que coincidan en libro+capítulo,
    y devuelve el paquete final de datos del Evangelio del día.
    Si la segunda fuente falla o no coincide, igual continúa con la
    principal pero deja constancia en 'verificado'.
    """
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
        "celebracion": principal["celebracion"],
        "color_liturgico": principal.get("color_liturgico"),
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
