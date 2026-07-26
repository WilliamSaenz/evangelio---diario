"""
Configuración central del proyecto "Evangelio de Hoy".

Todo lo que alguna vez haya que tocar a mano vive acá y en ningún otro archivo.
"""

from datetime import date
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Zona horaria y numeración de serie
# ---------------------------------------------------------------------------

TZ = ZoneInfo("America/Argentina/Buenos_Aires")

# Fecha en la que la serie vale 01.WS. Es lo ÚNICO que hay que cambiar
# si alguna vez querés reiniciar la numeración.
ANCLA_WS = date(2026, 7, 26)

# ---------------------------------------------------------------------------
# Fuentes del Evangelio
# ---------------------------------------------------------------------------
# Regla: se exige que coincidan al menos 2 de las 3 fuentes en libro + capítulo.
# dominicos.org es la fuente del TEXTO porque es la única direccionable por
# fecha (no depende de que el sitio "ya haya actualizado el hoy").

# Patrones de URL de dominicos.org. Ojo: SIN ceros a la izquierda (26-7-2026).
DOMINICOS_FERIA = "https://www.dominicos.org/predicacion/evangelio-del-dia/{d}-{m}-{y}/"
DOMINICOS_DOMINGO = "https://www.dominicos.org/predicacion/homilia/{d}-{m}-{y}/lecturas/"

EVANGELI_URL = "https://evangeli.net/evangelio"
# evangeli.net TAMBIÉN es direccionable por fecha, con la cita en el og:title.
# Acá el formato sí lleva ceros a la izquierda: 2026-07-26.
EVANGELI_FECHA = "https://evangeli.net/evangelio/dia/{iso}"
CIUDAD_REDONDA_URL = "https://www.ciudadredonda.org/evangelio-lecturas-hoy/"

HTTP_TIMEOUT = 30
HTTP_REINTENTOS = 4
HTTP_ESPERA_BASE = 5  # segundos; backoff exponencial
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

# OJO: gemini-2.0-flash topea en 8192 tokens de salida. Si el modelo se cambia
# a 2.0, hay que bajar GEMINI_MAX_TOKENS o la API rechaza el pedido.
GEMINI_MODELO = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
)
GEMINI_MAX_TOKENS = 65536
GEMINI_REINTENTOS = 3

# ---------------------------------------------------------------------------
# Imágenes (Pollinations / Flux — gratis, sin API key)
# ---------------------------------------------------------------------------

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
IMG_HEADER = (760, 420)
IMG_COLUMNA = (560, 400)
IMG_CIERRE = (420, 300)
IMG_REINTENTOS = 3

ESTILO_ILUSTRACION = (
    "warm painterly biblical illustration, soft golden light, muted earth tones, "
    "cream background, gentle reverent atmosphere, no text, no lettering, "
    "no watermark, no frame"
)

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

LAMINA_ANCHO = 1200  # px CSS; se renderiza a 2x => 2400 px reales
LAMINA_ESCALA = 2

# ---------------------------------------------------------------------------
# Frase de cierre (fija, nunca cambia)
# ---------------------------------------------------------------------------

FRASE_CIERRE = "No nos acercamos a Dios porque somos santos sino todo lo opuesto."

# ---------------------------------------------------------------------------
# Catálogo de iconos para las prácticas diarias.
# Gemini elige 3 claves de esta lista según el tema del Evangelio del día.
# Son SVG inline: no dependen de que el runner tenga fuentes de emoji.
# ---------------------------------------------------------------------------

ICONOS = {
    "orar": '<path d="M24 6c-3 0-5 2.5-5 6v13M24 6c3 0 5 2.5 5 6v13M19 25l-4 6a6 6 0 0 0 1 8l6 4h4l6-4a6 6 0 0 0 1-8l-4-6" />',
    "libro": '<path d="M8 11h11a5 5 0 0 1 5 5v21a5 5 0 0 0-5-5H8zM40 11H29a5 5 0 0 0-5 5v21a5 5 0 0 1 5-5h11z" />',
    "corazon": '<path d="M24 39s-13-8-13-17a7.5 7.5 0 0 1 13-5 7.5 7.5 0 0 1 13 5c0 9-13 17-13 17z" />',
    "manos": '<path d="M6 30l7-7 6 4h8M42 30l-7-7-6 4M14 23V13M34 23V13M6 30l8 8h20l8-8" />',
    "escuchar": '<path d="M16 20a8 8 0 0 1 16 0c0 6-6 7-6 12a4 4 0 0 1-8 0M22 34h4" />',
    "silencio": '<path d="M24 8v32M16 16v16M32 16v16M8 22v4M40 22v4" />',
    "caminar": '<circle cx="26" cy="10" r="4" /><path d="M26 16l-6 8 5 5 2 11M25 29l7 4 3 8M20 24l-8 3" />',
    "familia": '<circle cx="16" cy="15" r="5" /><circle cx="32" cy="15" r="5" /><path d="M8 38v-5a8 8 0 0 1 16 0v5M24 38v-5a8 8 0 0 1 16 0v5" />',
    "pan": '<path d="M10 22a8 6 0 0 1 28 0v12a4 4 0 0 1-4 4H14a4 4 0 0 1-4-4zM18 22v16M30 22v16" />',
    "luz": '<path d="M24 8c4 6 7 9 7 14a7 7 0 0 1-14 0c0-5 3-8 7-14zM17 36h14M20 41h8" />',
    "tiempo": '<circle cx="24" cy="24" r="15" /><path d="M24 14v10l7 5" />',
    "perdon": '<path d="M12 26l8 8 16-18" /><circle cx="24" cy="24" r="18" />',
    "semilla": '<path d="M24 40V22M24 22c0-7 5-12 12-12 0 7-5 12-12 12zM24 26c0-6-4-10-10-10 0 6 4 10 10 10z" />',
    "tesoro": '<path d="M8 20h32v18a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2zM8 20l4-8h24l4 8M24 20v20M20 26h8v6h-8z" />',
    "agua": '<path d="M24 8s11 13 11 20a11 11 0 0 1-22 0c0-7 11-20 11-20z" />',
    "cruz": '<path d="M24 8v32M14 18h20" />',
    "estrella": '<path d="M24 8l5 11 12 1.5-9 8 2.5 12L24 34l-10.5 6.5L16 28.5l-9-8L19 19z" />',
    "voz": '<path d="M20 16h-6v16h6l10 8V8zM36 18a9 9 0 0 1 0 12" />',
}

ICONO_POR_DEFECTO = "corazon"

# ---------------------------------------------------------------------------
# Meses y días en español, sin depender del locale del sistema
# (el runner de GitHub Actions no tiene es_ES instalado).
# ---------------------------------------------------------------------------

MESES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
]

MESES_ABREV = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]

DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
