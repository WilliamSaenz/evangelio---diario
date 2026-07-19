"""
render_lamina.py
Combina la plantilla HTML (templates/template.html) con el contenido del
día y las 4 imágenes generadas, y la renderiza a un PNG final usando
Playwright (headless Chromium).
"""
import base64
import pathlib
from datetime import date

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from format_message import calcular_ws, MESES, DIAS

TEMPLATES_DIR = pathlib.Path(__file__).parent.parent / "templates"


def _img_data_uri(img_bytes: bytes) -> str:
    b64 = base64.b64encode(img_bytes).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def armar_html(gospel: dict, contenido: dict, imagenes: dict) -> str:
    fecha = date.fromisoformat(gospel["fecha"])
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    tpl = env.get_template("template.html")

    data = dict(
        dia_semana=DIAS[fecha.weekday()],
        dia_numero=str(fecha.day),
        mes=MESES[fecha.month - 1].capitalize(),
        anio=str(fecha.year),
        cita_biblica=gospel["cita"],
        img_header=_img_data_uri(imagenes["header"]),
        evangelio_texto=contenido["evangelio_resumen"].replace("<b>", '<span class="destacado">').replace("</b>", "</span>"),
        img_teologia=_img_data_uri(imagenes["teologia"]),
        teologia_texto=contenido["teologia"]["texto"],
        teologia_frase=contenido["teologia"]["frase"],
        teologia_fuente=contenido["teologia"]["fuente"],
        img_psicologia=_img_data_uri(imagenes["psicologia"]),
        psicologia_texto=contenido["psicologia"]["texto"],
        psicologia_frase=contenido["psicologia"]["frase"],
        psicologia_fuente=contenido["psicologia"]["fuente"],
        img_neurociencia=_img_data_uri(imagenes["neurociencia"]),
        neurociencia_texto=contenido["neurociencia"]["texto"],
        neurociencia_frase=contenido["neurociencia"]["frase"],
        neurociencia_fuente=contenido["neurociencia"]["fuente"],
        practicas=[{"icono": _ICONOS.get(p["titulo"].upper(), "&#10024;"), "titulo": p["titulo"], "texto": p["texto"]} for p in contenido["practicas"]],
        frase_final="No nos acercamos a Dios porque somos santos sino todo lo opuesto.",
        img_cierre=_img_data_uri(imagenes["header"]),  # reutiliza el header, recortado por CSS
        fuente_evangelio=f"{gospel['fuente_principal']['nombre']}, {fecha.day} de {MESES[fecha.month-1]} de {fecha.year}.",
        fuente_segunda=(gospel["fuente_segunda"]["nombre"] if gospel.get("fuente_segunda") else "—"),
        fuente_otras="Catecismo de la Iglesia Católica.",
        ws_numero=calcular_ws(fecha),
    )
    return tpl.render(**data)


_ICONOS = {
    "ORAR": "&#128591;", "AGRADECER": "&#10084;", "ACOMPAÑAR": "&#129309;",
    "OBSERVAR": "&#128065;", "ESCUCHAR": "&#128066;", "PERDONAR": "&#128367;",
    "ESPERAR": "&#8987;", "PERSEVERAR": "&#128170;",
}


def renderizar_png(html: str, out_path: str) -> str:
    tmp_html = pathlib.Path(out_path).with_suffix(".html")
    tmp_html.write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 800}, device_scale_factor=2)
        page.goto(f"file://{tmp_html.resolve()}")
        page.wait_for_timeout(300)
        alto = page.evaluate("document.body.scrollHeight")
        page.set_viewport_size({"width": 1080, "height": alto})
        page.screenshot(path=out_path, full_page=True)
        browser.close()

    tmp_html.unlink(missing_ok=True)
    return out_path
