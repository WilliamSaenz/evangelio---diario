"""
main.py
Orquesta la corrida diaria completa:
  1. Fecha de hoy (America/Argentina/Buenos_Aires)
  2. Obtener + verificar el Evangelio en 2 fuentes
  3. Generar el contenido y los prompts de imagen (Gemini, gratis)
  4. Generar las 4 ilustraciones (Pollinations/Flux, gratis)
  5. Renderizar la lámina final (PNG)
  6. Enviarla como imagen a WhatsApp (Wappfly, gratis) para que la revises
     antes de subirla a tu estado.

Se ejecuta una vez al día vía GitHub Actions (ver .github/workflows/daily.yml).
"""
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from fetch_gospel import verificar_y_obtener, FuenteNoDisponible
from generate_content import generar_contenido, GeminiError
from generate_images import generar_todas, ImagenError
from render_lamina import armar_html, renderizar_png
from format_message import calcular_ws
from send_whatsapp import enviar_imagen, EnvioError

TZ = ZoneInfo("America/Argentina/Buenos_Aires")
SALIDA_PNG = "/tmp/lamina_hoy.png"


def run():
    hoy = datetime.now(TZ).date()
    print(f"[main] Fecha objetivo (ART): {hoy.isoformat()}")

    print("[main] Obteniendo Evangelio del día...")
    gospel = verificar_y_obtener(hoy)
    print(f"[main] Celebración: {gospel['celebracion']} | Cita: {gospel['cita']}")
    print(f"[main] Verificado en 2 fuentes: {gospel['verificado_en_dos_fuentes']}")

    print("[main] Generando contenido con Gemini...")
    contenido = generar_contenido(gospel)
    print(f"[main] Idea central: {contenido.get('idea_central')}")

    print("[main] Generando las 4 ilustraciones (Pollinations/Flux)...")
    imagenes = generar_todas(contenido, hoy)

    print("[main] Renderizando la lámina...")
    html = armar_html(gospel, contenido, imagenes)
    renderizar_png(html, SALIDA_PNG)

    ws = calcular_ws(hoy)
    caption = f"✝️ {gospel['cita']} — {ws}\nRevisá y subila a tu estado si te gusta 🙌"

    print("[main] Enviando la lámina por WhatsApp...")
    with open(SALIDA_PNG, "rb") as f:
        resultado = enviar_imagen(f.read(), caption=caption, mimetype="image/png")
    print(f"[main] Enviado OK: {resultado}")


if __name__ == "__main__":
    try:
        run()
    except (FuenteNoDisponible, GeminiError, ImagenError, EnvioError) as e:
        print(f"[ERROR conocido] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception:
        print("[ERROR inesperado]", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
