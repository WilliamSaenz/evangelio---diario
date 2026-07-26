"""
Numeración de serie WS y utilidades de fecha en español.

La numeración es puramente matemática: se calcula a partir de la fecha, sin
contador guardado en ningún lado. Imposible que se desincronice.
"""

from datetime import date, datetime

from config import ANCLA_WS, DIAS, MESES, MESES_ABREV, TZ


def hoy_ar() -> date:
    """Fecha de hoy en hora argentina (no en UTC, que es donde corre Actions)."""
    return datetime.now(TZ).date()


def calcular_ws(fecha: date | None = None) -> str:
    """
    Número de serie de la lámina.

    ANCLA_WS = 01.WS, y suma un día por día, sin reiniciarse nunca por mes.
    A partir del día 100 pasa naturalmente a 100.WS.
    """
    if fecha is None:
        fecha = hoy_ar()
    n = (fecha - ANCLA_WS).days + 1
    if n < 1:
        # Fecha anterior al ancla: no debería pasar, pero no rompemos por eso.
        n = 1
    return f"{n:02d}.WS"


def dia_semana(fecha: date) -> str:
    """LUNES, MARTES, ... (Monday = 0)."""
    return DIAS[fecha.weekday()]


def mes_nombre(fecha: date) -> str:
    """JULIO, AGOSTO, ..."""
    return MESES[fecha.month - 1]


def mes_abrev(fecha: date) -> str:
    """jul, ago, ... (como los usa dominicos.org en sus metadatos)."""
    return MESES_ABREV[fecha.month - 1]


def fecha_larga(fecha: date) -> str:
    """26 de julio de 2026"""
    return f"{fecha.day} de {mes_nombre(fecha).lower()} de {fecha.year}"


def slug_dominicos(fecha: date) -> dict:
    """
    Componentes de URL de dominicos.org.

    IMPORTANTE: sin ceros a la izquierda. La URL válida es 26-7-2026,
    no 26-07-2026 (esta última da 404).
    """
    return {"d": fecha.day, "m": fecha.month, "y": fecha.year}


def caption(fecha: date, cita: str) -> str:
    """Pie corto para identificar la lámina de un vistazo."""
    return f"Evangelio de Hoy — {fecha_larga(fecha)} — {cita} — {calcular_ws(fecha)}"


if __name__ == "__main__":
    hoy = hoy_ar()
    print(f"Hoy en Argentina : {hoy}  ({dia_semana(hoy)})")
    print(f"Número de serie  : {calcular_ws(hoy)}")
    print(f"Fecha larga      : {fecha_larga(hoy)}")
