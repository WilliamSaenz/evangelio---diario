"""
Render de la lámina: plantilla Jinja2 -> HTML -> PNG con Playwright.

El Evangelio va COMPLETO E INTACTO. Lo único que se le hace es envolver la
frase clave en <strong> para resaltarla. Si la frase que devolvió Gemini no
coincide literal, se busca la coincidencia aproximada más larga y, si tampoco
aparece, se deja el texto sin resaltar antes que alterarlo.
"""

from __future__ import annotations

import html as html_mod
import re
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from config import (
    FRASE_CIERRE,
    ICONO_POR_DEFECTO,
    ICONOS,
    LAMINA_ANCHO,
    LAMINA_ESCALA,
)
from fetch_gospel import Evangelio
from format_message import calcular_ws, dia_semana, fecha_larga, mes_nombre

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLAS = RAIZ / "templates"

ICONO_LIBRO = ICONOS["libro"]


# ---------------------------------------------------------------------------
# Resaltado de la frase clave dentro del Evangelio completo
# ---------------------------------------------------------------------------


def _normalizar(s: str) -> str:
    return re.sub(r"[\s\u00a0]+", " ", s).strip()


def resaltar(texto: str, frase: str) -> str:
    """
    Devuelve el Evangelio escapado como HTML, con la frase clave en <strong>.

    Nunca modifica, acorta ni reescribe el texto: solo inserta las etiquetas.
    """
    escapado = html_mod.escape(texto)
    objetivo = _normalizar(frase)
    if not objetivo:
        return escapado

    # 1) coincidencia exacta ignorando diferencias de espaciado
    patron = r"\s+".join(re.escape(p) for p in html_mod.escape(objetivo).split())
    m = re.search(patron, escapado)
    if m:
        return escapado[: m.start()] + f"<strong>{m.group(0)}</strong>" + escapado[m.end() :]

    # 2) coincidencia aproximada: el prefijo más largo de la frase que sí aparece
    palabras = html_mod.escape(objetivo).split()
    for corte in range(len(palabras), 4, -1):
        patron = r"\s+".join(re.escape(p) for p in palabras[:corte])
        m = re.search(patron, escapado)
        if m:
            print(f"    ⚠ frase clave resaltada parcialmente ({corte}/{len(palabras)} palabras)")
            return (
                escapado[: m.start()] + f"<strong>{m.group(0)}</strong>" + escapado[m.end() :]
            )

    print("    ⚠ no se pudo ubicar la frase clave; el Evangelio va sin resaltado")
    return escapado


# ---------------------------------------------------------------------------
# Armado del contexto
# ---------------------------------------------------------------------------


def construir_contexto(ev: Evangelio, contenido: dict, imagenes: dict) -> dict:
    columnas = []
    for clave, clase, titulo, icono in (
        ("teologia", "c-teologia", "TEOLOGÍA", "cruz"),
        ("psicologia", "c-psicologia", "PSICOLOGÍA", "corazon"),
        ("neurociencia", "c-neuro", "NEUROCIENCIA", "estrella"),
    ):
        bloque = contenido[clave]
        columnas.append(
            {
                "clase": clase,
                "titulo": titulo,
                "icono_svg": ICONOS[icono],
                "imagen": imagenes[clave],
                "texto": bloque["texto"],
                "frase": bloque["frase_destacada"],
                "fuente": bloque["fuente"],
            }
        )

    practicas = []
    for p in contenido["practicas"]:
        practicas.append(
            {
                "titulo": p["titulo"],
                "descripcion": p["descripcion"],
                "icono_svg": ICONOS.get(p["icono"], ICONOS[ICONO_POR_DEFECTO]),
            }
        )

    return {
        "ancho": LAMINA_ANCHO,
        "dia_semana": dia_semana(ev.fecha),
        "dia_numero": ev.fecha.day,
        "mes": mes_nombre(ev.fecha),
        "anio": ev.fecha.year,
        "cita": ev.cita.bonita(),
        "evangelio_html": resaltar(ev.texto, contenido["frase_clave"]),
        "columnas": columnas,
        "practicas": practicas,
        "imagenes": imagenes,
        "frase_cierre": FRASE_CIERRE,
        "icono_libro": ICONO_LIBRO,
        "ws": calcular_ws(ev.fecha),
        "fuente_evangelio": f"{ev.fuente_texto or 'Dominicos.org'}, {fecha_larga(ev.fecha)}",
        "fuentes_verificacion": ", ".join(ev.fuentes_ok),
    }


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def renderizar_html(contexto: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(PLANTILLAS)),
        autoescape=select_autoescape(["html"]),
    )
    return env.get_template("template.html").render(**contexto)


def html_a_png(html: str, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp_html = destino.with_suffix(".html")
    tmp_html.write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        navegador = p.chromium.launch(args=["--force-color-profile=srgb"])
        pagina = navegador.new_page(
            viewport={"width": LAMINA_ANCHO, "height": 1400},
            device_scale_factor=LAMINA_ESCALA,
        )
        pagina.goto(tmp_html.as_uri(), wait_until="networkidle")
        # Esperamos a que las fuentes estén listas para que no salte el layout
        pagina.evaluate("() => document.fonts.ready")
        pagina.wait_for_timeout(600)
        pagina.locator("#lamina").screenshot(path=str(destino))
        navegador.close()

    print(f"    ✓ lámina renderizada: {destino} ({destino.stat().st_size // 1024} KB)")
    return destino


def generar_lamina(
    ev: Evangelio, contenido: dict, imagenes: dict, salida: Path
) -> Path:
    print("  → renderizando lámina")
    contexto = construir_contexto(ev, contenido, imagenes)
    return html_a_png(renderizar_html(contexto), salida)


if __name__ == "__main__":
    print("Este módulo se usa desde main.py")
