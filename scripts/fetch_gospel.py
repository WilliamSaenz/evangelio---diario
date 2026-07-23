"""
fetch_gospel.py — Evangelio de Hoy

CAMBIO (23/7/2026 tarde): a pedido explícito, se sacan Vatican News y
ACI Prensa de la cadena automática (mostraron fallas recurrentes en la
práctica). Quedan tres fuentes, todas con validación de fecha explícita,
y se exige que coincidan AL MENOS 2 de las 3 para enviar. Si no hay
acuerdo, no se envía nada ese día — mejor eso que contenido dudoso.

Fuentes:
  1. Dominicos.org    (dominicos.org/predicacion/evangelio-del-dia/hoy/)
  2. evangeli.net     (evangeli.net/evangelio)
  3. Ciudad Redonda   (ciudadredonda.org/evangelio-lecturas-hoy/)
"""
import re
import sys
import requests
from datetime import date, timedelta
from itertools import combinations
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EvangelioDiarioBot/1.0; +personal use)"
}
TIMEOUT = 20

LIBRO_MAP = {
    "mt": "mateo", "mateo": "mateo",
    "mc": "marcos", "marcos": "marcos",
    "lc": "lucas", "lucas": "lucas",
    "jn": "juan", "juan": "juan",
}


class FuenteNoDisponible(Exception):
    pass


def _get_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _texto_de(soup: BeautifulSoup) -> str:
    soup = BeautifulSoup(str(soup), "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "svg"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def _normaliza_cita(cita: str) -> str:
    c = cita.lower().replace("san ", "").replace("según ", "").replace(".", "")
    m = re.search(r"([a-záéíóúñ]+)\s+(\d+)", c)
    if not m:
        return c
    libro = LIBRO_MAP.get(m.group(1), m.group(1))
    return f"{libro}{m.group(2)}"


# ---------------------------------------------------------------------------
# 1. Dominicos.org
# ---------------------------------------------------------------------------

def fetch_from_dominicos() -> dict:
    url_intro = "https://www.dominicos.org/predicacion/evangelio-del-dia/hoy/"
    url_lecturas = "https://www.dominicos.org/predicacion/evangelio-del-dia/hoy/lecturas/"
    text = _texto_de(_get_soup(url_lecturas))

    m_ev = re.search(
        r"Evangelio del día\s*\n+Lectura del santo evangelio según\s+(.+?)\n(.*?)\nDescargar",
        text, re.DOTALL,
    )
    if not m_ev:
        raise FuenteNoDisponible(f"No se pudo extraer el Evangelio de {url_lecturas}")
    cita = m_ev.group(1).strip()
    cuerpo = re.sub(r"\s{2,}|\n+", " ", m_ev.group(2).strip()).strip()
    if not cita or not cuerpo:
        raise FuenteNoDisponible(f"Extracción incompleta de {url_lecturas}")
    return {"fuente": "Dominicos.org", "url": url_intro, "celebracion": None, "cita": cita, "texto": cuerpo}


# ---------------------------------------------------------------------------
# 2. evangeli.net — valida fecha vía los links de día anterior/siguiente
# ---------------------------------------------------------------------------

def fetch_from_evangelinet(target_date: date) -> dict:
    url = "https://evangeli.net/evangelio"
    soup = _get_soup(url)

    anterior = (target_date - timedelta(days=1)).isoformat()
    siguiente = (target_date + timedelta(days=1)).isoformat()
    hrefs = [a.get("href", "") for a in soup.find_all("a")]
    if not any(f"/evangelio/dia/{anterior}" in h for h in hrefs) or \
       not any(f"/evangelio/dia/{siguiente}" in h for h in hrefs):
        raise FuenteNoDisponible(f"evangeli.net no muestra navegación consistente con {target_date.isoformat()}")

    text = _texto_de(soup)
    patrones = [
        r"Texto del Evangelio\s*\(([^)]+)\):?\s*\n*(.*?)(?:\n(?:Rev\.|Pensamientos para el Evangelio|¿Sabes cómo)|\Z)",
    ]
    for patron in patrones:
        m_ev = re.search(patron, text, re.DOTALL)
        if m_ev:
            cita = m_ev.group(1).strip()
            cuerpo = re.sub(r"\s{2,}|\n+", " ", m_ev.group(2).strip()).strip()
            if cita and cuerpo:
                return {"fuente": "evangeli.net", "url": url, "celebracion": None, "cita": cita, "texto": cuerpo}

    print(f"[debug] evangeli.net: no matcheó. Primeros 400 caracteres: {text[:400]!r}", file=sys.stderr)
    raise FuenteNoDisponible(f"No se pudo extraer el Evangelio de {url}")


# ---------------------------------------------------------------------------
# 3. Ciudad Redonda — valida fecha vía el link "occurrence=YYYY-MM-DD"
# ---------------------------------------------------------------------------

def fetch_from_ciudadredonda(target_date: date) -> dict:
    url = "https://www.ciudadredonda.org/evangelio-lecturas-hoy/"
    soup = _get_soup(url)

    hrefs = [a.get("href", "") for a in soup.find_all("a")]
    if not any(f"occurrence={target_date.isoformat()}" in h for h in hrefs):
        raise FuenteNoDisponible(f"Ciudad Redonda no muestra la fecha de {target_date.isoformat()} todavía")

    text = _texto_de(soup)
    m_ev = re.search(
        r"Evangelio\s*\n+"
        r"Lectura del santo evangelio según\s+(.+?)\s*\n+"
        r"(.*?)\n+"
        r"(?:Palabra del Señor|Compartir este evento)",
        text, re.DOTALL,
    )
    if not m_ev:
        print(f"[debug] Ciudad Redonda: no matcheó. Primeros 400 caracteres: {text[:400]!r}", file=sys.stderr)
        raise FuenteNoDisponible(f"No se pudo extraer el Evangelio de {url}")

    cita = m_ev.group(1).strip()
    cuerpo = re.sub(r"\s{2,}|\n+", " ", m_ev.group(2).strip()).strip()
    if not cita or not cuerpo:
        raise FuenteNoDisponible(f"Extracción incompleta de {url}")
    return {"fuente": "Ciudad Redonda", "url": url, "celebracion": None, "cita": cita, "texto": cuerpo}


# ---------------------------------------------------------------------------
# Orquestación: exige coincidencia de al menos 2 de las 3
# ---------------------------------------------------------------------------

def verificar_y_obtener(target_date: date) -> dict:
    candidatos = []
    for nombre, fn in [
        ("Dominicos.org", fetch_from_dominicos),
        ("evangeli.net", lambda: fetch_from_evangelinet(target_date)),
        ("Ciudad Redonda", lambda: fetch_from_ciudadredonda(target_date)),
    ]:
        try:
            candidatos.append(fn())
        except Exception as e:
            print(f"[aviso] {nombre} no disponible: {e}", file=sys.stderr)

    if len(candidatos) < 2:
        raise FuenteNoDisponible(
            f"Solo {len(candidatos)} fuente(s) disponible(s) para {target_date.isoformat()}; "
            f"hacen falta al menos 2 que coincidan."
        )

    for a, b in combinations(candidatos, 2):
        if _normaliza_cita(a["cita"]) == _normaliza_cita(b["cita"]):
            return {
                "fecha": target_date.isoformat(),
                "celebracion": a.get("celebracion") or b.get("celebracion"),
                "cita": a["cita"],
                "texto": a["texto"],
                "fuente_principal": {"nombre": a["fuente"], "url": a["url"]},
                "fuente_segunda": {"nombre": b["fuente"], "url": b["url"]},
                "verificado_en_dos_fuentes": True,
            }

    citas = ", ".join(f"{c['fuente']}: {c['cita']}" for c in candidatos)
    raise FuenteNoDisponible(
        f"Ninguna fuente coincide para {target_date.isoformat()} — {citas}. No se envía nada hasta poder confirmar."
    )


if __name__ == "__main__":
    import json
    print(json.dumps(verificar_y_obtener(date.today()), ensure_ascii=False, indent=2))
