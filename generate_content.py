"""
Orquestador de la lámina diaria "Evangelio de Hoy".

Uso:
    python scripts/main.py                # el Evangelio de hoy (hora Argentina)
    python scripts/main.py 2026-07-26     # una fecha puntual, para probar
    python scripts/main.py --sin-enviar   # genera la lámina pero no manda mail
"""

from __future__ import annotations

import sys
import traceback
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_gospel import obtener_evangelio  # noqa: E402
from format_message import caption, calcular_ws, fecha_larga, hoy_ar  # noqa: E402
from generate_content import generar_contenido  # noqa: E402
from generate_images import generar_imagenes  # noqa: E402
from render_lamina import generar_lamina  # noqa: E402
from send_email import enviar_alerta, enviar_lamina  # noqa: E402

SALIDA = Path(__file__).resolve().parent.parent / "salida"


def ejecutar(fecha: date, enviar: bool = True) -> Path:
    ws = calcular_ws(fecha)
    print("=" * 66)
    print(f"  EVANGELIO DE HOY — {fecha_larga(fecha)} — {ws}")
    print("=" * 66)

    print("\n[1/5] Evangelio del día")
    ev = obtener_evangelio(fecha)

    print("\n[2/5] Contenido (Gemini)")
    contenido = generar_contenido(ev)

    print("\n[3/5] Ilustraciones")
    imagenes = generar_imagenes(contenido["imagenes"], fecha)

    print("\n[4/5] Render")
    destino = SALIDA / f"evangelio_{fecha.isoformat()}_{ws.replace('.', '')}.png"
    lamina = generar_lamina(ev, contenido, imagenes, destino)

    print("\n[5/5] Envío")
    if enviar:
        enviar_lamina(
            lamina,
            asunto=f"Evangelio de Hoy — {ev.cita.bonita()} — {ws}",
            resumen=caption(fecha, ev.cita.bonita()),
        )
    else:
        print("    (--sin-enviar: no se manda correo)")

    print(f"\n✓ Listo. Lámina en {lamina}")
    return lamina


def main() -> int:
    args = [a for a in sys.argv[1:]]
    enviar = "--sin-enviar" not in args
    args = [a for a in args if not a.startswith("--")]

    if args:
        try:
            fecha = datetime.strptime(args[0], "%Y-%m-%d").date()
        except ValueError:
            print(f"Fecha inválida: {args[0]!r}. Formato esperado: AAAA-MM-DD")
            return 2
    else:
        fecha = hoy_ar()

    try:
        ejecutar(fecha, enviar=enviar)
        return 0
    except Exception as e:  # noqa: BLE001
        print("\n" + "!" * 66)
        print("LA CORRIDA FALLÓ")
        print("!" * 66)
        traceback.print_exc()
        if enviar:
            try:
                enviar_alerta(f"{type(e).__name__}: {e}")
            except Exception as e2:  # noqa: BLE001
                print(f"(tampoco se pudo enviar el aviso: {e2})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
