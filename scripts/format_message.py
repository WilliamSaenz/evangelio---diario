"""
format_message.py
Arma el mensaje de texto final para WhatsApp: corto, con *negritas* y
emojis de sección, sin bloques de texto densos (para que se lea bien
en pantalla chica).
"""
import re
from datetime import date

MESES = ["enero","febrero","marzo","abril","mayo","junio","julio",
         "agosto","septiembre","octubre","noviembre","diciembre"]
DIAS = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

FRASE_FINAL = "No nos acercamos a Dios porque somos santos sino todo lo opuesto."
FECHA_INICIO_SERIE = date(2026, 7, 19)


def calcular_ws(fecha: date) -> str:
    """01.WS, 02.WS, ... se calcula solo, contando dias desde el inicio.
    Nunca se guarda ni se reinicia manualmente: es pura funcion de la fecha."""
    dias = (fecha - FECHA_INICIO_SERIE).days + 1
    if dias < 1:
        dias = 1
    return f"{dias:02d}.WS"


def _negrita_html_a_whatsapp(texto: str) -> str:
    """Convierte <b>..</b> (que pide Gemini) al *asterisco* de WhatsApp."""
    return re.sub(r"</?b>", "*", texto)


def construir_mensaje(gospel: dict, contenido: dict) -> str:
    fecha = date.fromisoformat(gospel["fecha"])
    dia_semana = DIAS[fecha.weekday()]
    mes = MESES[fecha.month - 1]

    evangelio_txt = _negrita_html_a_whatsapp(contenido["evangelio_resumen"])

    partes = []
    partes.append(f"📅 *{dia_semana.upper()} {fecha.day} DE {mes.upper()} {fecha.year}*")
    if gospel.get("celebracion"):
        partes.append(f"_{gospel['celebracion']}_")
    partes.append(f"✝️ *{gospel['cita']}*")
    partes.append("")
    partes.append(f"“{evangelio_txt}”")
    partes.append("")
    partes.append("⛪ *TEOLOGÍA*")
    partes.append(contenido["teologia"]["texto"])
    partes.append(f"👉 _{contenido['teologia']['frase']}_")
    partes.append("")
    partes.append("🧠 *PSICOLOGÍA*")
    partes.append(contenido["psicologia"]["texto"])
    partes.append(f"👉 _{contenido['psicologia']['frase']}_")
    partes.append("")
    partes.append("🧬 *NEUROCIENCIA*")
    partes.append(contenido["neurociencia"]["texto"])
    partes.append(f"👉 _{contenido['neurociencia']['frase']}_")
    partes.append("")
    partes.append("✅ *PRÁCTICAS DE HOY*")
    for i, p in enumerate(contenido["practicas"], start=1):
        partes.append(f"{i}. *{p['titulo']}* — {p['texto']}")
    partes.append("")
    partes.append(f"❤️ _{FRASE_FINAL}_")
    partes.append("")
    partes.append("📚 *Fuentes*")
    partes.append(f"• Evangelio: {gospel['fuente_principal']['nombre']}, {fecha.day} de {mes} de {fecha.year}.")
    if gospel.get("fuente_segunda"):
        partes.append(f"• Segunda fuente: {gospel['fuente_segunda']['nombre']}.")
    partes.append(f"• Teología: {contenido['teologia']['fuente']}")
    partes.append(f"• Psicología: {contenido['psicologia']['fuente']}")
    partes.append(f"• Neurociencia: {contenido['neurociencia']['fuente']}")
    partes.append("")
    partes.append(calcular_ws(fecha))

    return "\n".join(partes)
