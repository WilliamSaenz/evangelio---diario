"""
Obtención y verificación del Evangelio del día.

Diseño, y por qué:

El problema de fondo de la versión anterior era que las tres fuentes se pedían
por su página "de hoy". Eso hace que la votación por mayoría NO proteja contra
el caso más probable: que dos sitios estén desactualizados a la misma hora de la
madrugada y coincidan entre sí en el Evangelio de AYER. Dos fuentes rancias le
ganan por mayoría a una fresca, y la lámina sale mal.

La solución no es sumar fuentes, es anclar la fecha. Dos de las tres son
direccionables por fecha, así que se les pide el día explícitamente:

  dominicos.org   /predicacion/evangelio-del-dia/26-7-2026/    (sin ceros)
  dominicos.org   /predicacion/homilia/26-7-2026/lecturas/     (domingos)
  evangeli.net    /evangelio/dia/2026-07-26                    (con ceros)

Con eso el sitio no puede devolver otro día: o tiene esa fecha, o da 404.
Ciudad Redonda solo publica "hoy", así que queda como tercera fuente de
verificación, con doble chequeo de fecha.

Cualquiera de las dos primeras puede aportar el texto completo, así que si una
se cae la corrida sigue. Antes, si se caía dominicos, no había lámina.

ACI Prensa y Vatican News quedaron fuera por fallas recurrentes.
"""

from __future__ import annotations

import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import date

import requests
from bs4 import BeautifulSoup

from config import (
    CIUDAD_REDONDA_URL,
    DOMINICOS_DOMINGO,
    DOMINICOS_FERIA,
    EVANGELI_FECHA,
    HTTP_ESPERA_BASE,
    HTTP_REINTENTOS,
    HTTP_TIMEOUT,
    USER_AGENT,
)
from format_message import mes_abrev, slug_dominicos

# ---------------------------------------------------------------------------
# Normalización de citas bíblicas
# ---------------------------------------------------------------------------

LIBROS = {
    "mateo": "Mt", "mt": "Mt", "san mateo": "Mt",
    "marcos": "Mc", "mc": "Mc", "san marcos": "Mc",
    "lucas": "Lc", "lc": "Lc", "san lucas": "Lc",
    "juan": "Jn", "jn": "Jn", "san juan": "Jn",
}

NOMBRE_LARGO = {"Mt": "Mateo", "Mc": "Marcos", "Lc": "Lucas", "Jn": "Juan"}


def _sin_tildes(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


@dataclass
class Cita:
    """Cita del Evangelio, normalizada para poder comparar entre sitios."""

    libro: str  # "Mt"
    capitulo: int  # 13
    versiculos: str  # "44-52"
    crudo: str = ""

    @property
    def clave(self) -> tuple[str, int]:
        """
        Lo que se compara entre fuentes: libro + capítulo.

        A propósito NO se comparan los versículos: distintos leccionarios
        recortan la perícopa con un versículo de diferencia sin que eso
        signifique que estén hablando de otro Evangelio.
        """
        return (self.libro, self.capitulo)

    @property
    def nombre_largo(self) -> str:
        return NOMBRE_LARGO[self.libro]

    def bonita(self) -> str:
        return f"{self.nombre_largo} {self.capitulo}, {self.versiculos}"

    def __str__(self) -> str:
        return f"{self.libro} {self.capitulo},{self.versiculos}"


CITA_RE = re.compile(
    r"(?:seg[uú]n\s+)?(?:san\s+)?"
    r"(Mateo|Marcos|Lucas|Juan|Mt|Mc|Lc|Jn)"
    r"[\s\.]*\(?\s*(\d{1,2})\s*[,:]\s*"
    # Versículos posiblemente discontinuos: "44-52", "1-2.11-18", "1. 7-14"
    r"(\d+[a-c]?(?:\s*[-–.,]\s*\d+[a-c]?)*)",
    re.IGNORECASE,
)


def parsear_cita(texto: str) -> Cita | None:
    m = CITA_RE.search(texto)
    if not m:
        return None
    libro = LIBROS.get(_sin_tildes(m.group(1)).lower().strip())
    if not libro:
        return None
    vers = re.sub(r"\s+", "", m.group(3)).strip(".,-–")
    return Cita(
        libro=libro, capitulo=int(m.group(2)), versiculos=vers, crudo=m.group(0).strip()
    )


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def _get(url: str, intentos: int = HTTP_REINTENTOS) -> requests.Response | None:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "es-ES,es;q=0.9"}
    for i in range(intentos):
        try:
            r = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            if r.status_code == 200:
                r.encoding = r.apparent_encoding or "utf-8"
                return r
            if r.status_code == 404:
                print("    HTTP 404 — esa fecha no existe en esta ruta")
                return None
            print(f"    HTTP {r.status_code}")
        except requests.RequestException as e:
            print(f"    error de red: {e}")
        if i < intentos - 1:
            espera = HTTP_ESPERA_BASE * (2**i)
            print(f"    reintento en {espera}s...")
            time.sleep(espera)
    return None


def _texto_plano(html: str) -> str:
    sopa = BeautifulSoup(html, "html.parser")
    for tag in sopa(["script", "style", "nav", "footer", "svg"]):
        tag.decompose()
    return sopa.get_text("\n", strip=True)


def _meta(html: str, clave: str) -> str:
    for attr in ("property", "name"):
        m = re.search(
            rf"<meta[^>]+{attr}=[\"']{clave}[\"'][^>]+content=[\"']([^\"']+)",
            html, re.IGNORECASE,
        )
        if m:
            return m.group(1)
        m = re.search(
            rf"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+{attr}=[\"']{clave}[\"']",
            html, re.IGNORECASE,
        )
        if m:
            return m.group(1)
    return ""


# ---------------------------------------------------------------------------
# Estructuras
# ---------------------------------------------------------------------------


@dataclass
class Evangelio:
    fecha: date
    cita: Cita
    texto: str
    fuente_texto: str = ""
    titulo_liturgico: str = ""
    fuentes_ok: list[str] = field(default_factory=list)
    fuentes_fallidas: list[str] = field(default_factory=list)


@dataclass
class Lectura:
    """Lo que devuelve cada fuente. texto vacío = solo sirve para verificar."""

    fuente: str
    cita: Cita
    texto: str = ""
    titulo: str = ""


# ---------------------------------------------------------------------------
# Validación de fecha
# ---------------------------------------------------------------------------


def _fecha_presente(html: str, fecha: date) -> bool:
    plano = _sin_tildes(html).lower()
    d, m, y = fecha.day, fecha.month, fecha.year
    patrones = [
        rf"\b{d}\s+{mes_abrev(fecha)}\.?\s+{y}\b",  # 26 jul. 2026
        rf"\b{d}\s+de\s+\w+\s+de\s+{y}\b",          # 26 de julio de 2026
        rf"\b{d}\s+\w+\s+{y}\b",                    # domingo 26 Julio 2026
        rf"\b{d}-{m}-{y}\b",                        # 26-7-2026
        rf"\b{y}-{m:02d}-{d:02d}\b",                # 2026-07-26
    ]
    return any(re.search(p, plano) for p in patrones)


# ---------------------------------------------------------------------------
# 1. dominicos.org — por fecha, con texto
# ---------------------------------------------------------------------------


def _extraer_dominicos(html: str) -> tuple[Cita, str] | None:
    sopa = BeautifulSoup(html, "html.parser")

    encabezado = None
    for tag in sopa.find_all(["h1", "h2", "h3", "h4", "h5"]):
        # Ojo: el sitio alterna "santo Evangelio" y "santo evangelio", por eso
        # la búsqueda va sin distinguir mayúsculas.
        if re.search(r"Evangelio\s+seg[uú]n", tag.get_text(" ", strip=True), re.I):
            encabezado = tag
            break
    if encabezado is None:
        return None

    cita = parsear_cita(encabezado.get_text(" ", strip=True))
    if cita is None:
        return None

    partes: list[str] = []
    for elem in encabezado.find_all_next():
        if elem.name in {"h1", "h2", "h3", "h4", "h5"}:
            break
        if elem.name != "p":
            continue
        txt = elem.get_text("\n", strip=True)
        if not txt:
            continue
        if re.search(
            r"(Descargar|Suscribirme|Podcast|Imprimir|Reciba el Evangelio|"
            r"Ver otros a[nñ]os|Las lecturas siguen)", txt, re.I,
        ):
            break
        partes.append(txt)

    texto = re.sub(r"\n{3,}", "\n\n", "\n".join(partes).strip())
    return (cita, texto) if len(texto) >= 120 else None


def desde_dominicos(fecha: date) -> Lectura | None:
    slug = slug_dominicos(fecha)
    urls = [DOMINICOS_FERIA.format(**slug), DOMINICOS_DOMINGO.format(**slug)]
    if fecha.weekday() == 6:  # domingo: probamos primero la ruta de homilía
        urls.reverse()

    for url in urls:
        print(f"  → dominicos.org  {url}")
        r = _get(url)
        if r is None:
            continue
        if not _fecha_presente(r.text, fecha):
            print("    ✗ la página no menciona la fecha pedida — descartada")
            continue
        extraido = _extraer_dominicos(r.text)
        if extraido is None:
            print("    ✗ no se pudo extraer el Evangelio")
            continue
        cita, texto = extraido
        desc = _meta(r.text, "description") or _meta(r.text, "og:description")
        titulo = desc.split(",", 1)[1].split(".")[0].strip() if "," in desc else ""
        print(f"    ✓ {cita} · {len(texto)} caracteres")
        return Lectura("dominicos.org", cita, texto, titulo)
    return None


# ---------------------------------------------------------------------------
# 2. evangeli.net — por fecha, con texto. La cita viene en el og:title.
# ---------------------------------------------------------------------------


def desde_evangeli(fecha: date) -> Lectura | None:
    url = EVANGELI_FECHA.format(iso=fecha.isoformat())
    print(f"  → evangeli.net   {url}")
    r = _get(url, intentos=3)
    if r is None:
        return None
    if not _fecha_presente(r.text, fecha):
        print("    ✗ la página no menciona la fecha pedida — descartada")
        return None

    # og:title trae la cita limpia: "Lunes 17 del tiempo ordinario (Mt 13,31-35)"
    og = _meta(r.text, "og:title")
    cita = parsear_cita(og)
    titulo = re.sub(r"\s*\([^)]*\)\s*$", "", og).strip() if og else ""

    plano = _texto_plano(r.text)
    m = re.search(
        r"Texto del Evangelio\s*\(([^)]+)\)\s*:?\s*(.*?)"
        r"(?=\n\s*«[^»]{0,120}»\s*\n\s*Rev\.|\n\s*Rev\.|"
        r"Pensamientos para el Evangelio|\Z)",
        plano, re.DOTALL,
    )
    texto = ""
    if m:
        if cita is None:
            cita = parsear_cita(m.group(1))
        texto = re.sub(r"\n{2,}", "\n", m.group(2).strip())

    if cita is None:
        print("    ✗ no se encontró la cita")
        return None
    print(f"    ✓ {cita} · {len(texto)} caracteres")
    return Lectura("evangeli.net", cita, texto, titulo)


# ---------------------------------------------------------------------------
# 3. Ciudad Redonda — solo "hoy". Verificación únicamente.
# ---------------------------------------------------------------------------


def desde_ciudad_redonda(fecha: date) -> Lectura | None:
    print(f"  → ciudadredonda  {CIUDAD_REDONDA_URL}")
    r = _get(CIUDAD_REDONDA_URL, intentos=2)
    if r is None:
        return None

    # Doble chequeo de fecha. El link "occurrence=" es el que ya usabas; solo,
    # es débil, porque un calendario lateral puede traer el link de hoy aunque
    # el contenido mostrado sea el de ayer. Por eso se exige además que la
    # fecha aparezca escrita en la página.
    tiene_occurrence = f"occurrence={fecha.isoformat()}" in r.text
    tiene_fecha = _fecha_presente(r.text, fecha)
    if not (tiene_occurrence or tiene_fecha):
        print("    ✗ no corresponde a la fecha pedida — descartada")
        return None
    if not (tiene_occurrence and tiene_fecha):
        print("    ⚠ solo uno de los dos chequeos de fecha dio positivo")

    plano = _texto_plano(r.text)
    idx = _sin_tildes(plano).lower().find("evangelio segun")
    cita = parsear_cita(plano[idx : idx + 300] if idx != -1 else plano)
    if cita is None:
        print("    ✗ no se encontró la cita")
        return None
    print(f"    ✓ {cita}")
    return Lectura("ciudadredonda.org", cita, "")


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------

ORDEN_PREFERENCIA = {"dominicos.org": 0, "evangeli.net": 1, "ciudadredonda.org": 2}

# Fuentes que se piden por URL con la fecha adentro: no pueden devolver otro día.
# Ciudad Redonda queda afuera porque solo publica "hoy".
FUENTES_ANCLADAS = {"dominicos.org", "evangeli.net"}


FUENTES_DISPONIBLES = {
    "dominicos.org": desde_dominicos,
    "evangeli.net": desde_evangeli,
}


def obtener_evangelio(fecha: date, forzar_fuente: str | None = None) -> Evangelio:
    """Devuelve el Evangelio verificado, o levanta RuntimeError.

    forzar_fuente: solo para uso manual (workflow_dispatch), NUNCA en la
    corrida automática de las 4:30. Sirve para los días de doble opción
    litúrgica válida (ej. una memoria con dos lecturas oficiales), donde
    dos fuentes ancladas por fecha pueden "discrepar" sin que ninguna esté
    mal — cada una tomó una opción distinta. En ese caso no hay forma
    automática de decidir cuál mandar; la persona elige y lo fuerza acá.
    Toma el texto de la fuente indicada tal cual, sin cruce con las demás.
    """
    print(f"\n=== Evangelio del {fecha.isoformat()} ===")

    if forzar_fuente:
        fn = FUENTES_DISPONIBLES.get(forzar_fuente)
        if fn is None:
            raise RuntimeError(
                f"forzar_fuente={forzar_fuente!r} inválido. "
                f"Opciones: {', '.join(FUENTES_DISPONIBLES)}"
            )
        print(f"  ⚠ FORZADO MANUAL: se toma {forzar_fuente} sin cruzar con otras fuentes")
        lectura = fn(fecha)
        if lectura is None or len(lectura.texto) < 120:
            raise RuntimeError(f"{forzar_fuente} no devolvió el Evangelio de {fecha.isoformat()}")
        return Evangelio(
            fecha=fecha,
            cita=lectura.cita,
            texto=lectura.texto,
            fuente_texto=lectura.fuente,
            titulo_liturgico=lectura.titulo,
            fuentes_ok=[f"{lectura.fuente} (forzado a mano)"],
            fuentes_fallidas=[],
        )

    lecturas: list[Lectura] = []
    fallidas: list[str] = []
    for nombre, fn in (
        ("dominicos.org", desde_dominicos),
        ("evangeli.net", desde_evangeli),
        ("ciudadredonda.org", desde_ciudad_redonda),
    ):
        try:
            lectura = fn(fecha)
        except Exception as e:  # noqa: BLE001 — una fuente rota no tumba la corrida
            print(f"    ✗ error inesperado: {e}")
            lectura = None
        if lectura is None:
            fallidas.append(f"{nombre} (sin dato válido)")
        else:
            lecturas.append(lectura)

    if len(lecturas) < 2:
        raise RuntimeError(
            f"Solo {len(lecturas)} fuente(s) válida(s) para {fecha.isoformat()}. "
            f"Hacen falta 2 coincidentes. Fallaron: {'; '.join(fallidas)}"
        )

    # Antes esto abortaba directo si las dos fuentes ancladas discrepaban,
    # asumiendo que un desacuerdo solo podía ser por staleness. Pero como
    # ambas están ancladas por fecha (no pueden devolver otro día, ver
    # docstring del módulo), un desacuerdo entre ellas ya no puede ser por
    # eso — solo puede ser un día de doble opción litúrgica válida (ej. una
    # memoria con dos lecturas oficiales) o, más raro, un error de una de
    # las dos al parsear. En cualquiera de los dos casos, dejamos que
    # decida la votación de mayoría de las 3 fuentes de más abajo: si
    # Ciudad Redonda (que si puede estar rancia, por eso no cuenta como
    # ancla) coincide con una de las dos, esa gana; si no coincide con
    # ninguna, la votación no forma mayoría y aborta igual más abajo.

    # Mayoría por libro + capítulo
    conteo: dict[tuple[str, int], list[Lectura]] = {}
    for lectura in lecturas:
        conteo.setdefault(lectura.cita.clave, []).append(lectura)
    clave_ganadora, grupo = max(conteo.items(), key=lambda kv: len(kv[1]))

    print(f"\n  Coincidencias: {len(grupo)}/3 → {', '.join(l.fuente for l in grupo)}")
    for lectura in lecturas:
        if lectura.cita.clave != clave_ganadora:
            fallidas.append(f"{lectura.fuente} (dice {lectura.cita})")
    if fallidas:
        print(f"  Discrepancias: {'; '.join(fallidas)}")

    if len(grupo) < 2:
        detalle = ", ".join(f"{l.fuente}: {l.cita}" for l in lecturas)
        raise RuntimeError(
            f"Ninguna fuente coincide con otra para {fecha.isoformat()} ({detalle}). "
            "No se genera lámina."
        )

    # Defensa en profundidad. La validación de fecha de cada fuente ya debería
    # impedir que una página rancia llegue hasta acá, pero si por lo que sea
    # llegara, la mayoría podría formarse entre fuentes NO ancladas y publicar
    # el Evangelio de ayer. Exigimos que la mayoría incluya al menos una fuente
    # pedida por fecha explícita.
    ancladas_en_grupo = {l.fuente for l in grupo} & FUENTES_ANCLADAS
    if not ancladas_en_grupo:
        raise RuntimeError(
            f"La mayoría ({', '.join(l.fuente for l in grupo)}) no incluye ninguna "
            "fuente anclada por fecha. No se genera lámina: no hay forma de "
            "garantizar que sea el Evangelio del día correcto."
        )

    # De las fuentes que están en la mayoría, la que traiga texto completo.
    con_texto = [l for l in grupo if len(l.texto) >= 120]
    if not con_texto:
        raise RuntimeError(
            f"Hay acuerdo en {grupo[0].cita} pero ninguna fuente de la mayoría "
            "devolvió el texto completo. No se genera lámina."
        )
    elegida = min(con_texto, key=lambda l: ORDEN_PREFERENCIA.get(l.fuente, 9))
    print(f"  Texto tomado de: {elegida.fuente}")

    return Evangelio(
        fecha=fecha,
        cita=elegida.cita,
        texto=elegida.texto,
        fuente_texto=elegida.fuente,
        titulo_liturgico=next((l.titulo for l in grupo if l.titulo), ""),
        fuentes_ok=[l.fuente for l in grupo],
        fuentes_fallidas=fallidas,
    )


if __name__ == "__main__":
    from format_message import hoy_ar

    ev = obtener_evangelio(hoy_ar())
    print("\n" + "=" * 62)
    print(f"{ev.cita.bonita()} — {ev.titulo_liturgico}  [{ev.fuente_texto}]")
    print("=" * 62)
    print(ev.texto)
    sys.exit(0)
