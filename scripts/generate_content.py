"""
generate_content.py
Genera, a partir del Evangelio del día, el contenido de las 3 columnas
(Teología / Psicología / Neurociencia) + 3 prácticas + frase dorada,
usando Gemini (Google AI Studio, free tier — sin costo).

Requiere la variable de entorno GEMINI_API_KEY (gratis, sin tarjeta,
se obtiene en https://aistudio.google.com/apikey).
"""
import os
import re
import json
import requests

GEMINI_MODEL = "gemini-flash-latest"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

SYSTEM_INSTRUCTIONS = """\
Actuás como un equipo integrado por: sacerdote católico especialista en \
Sagrada Escritura, teólogo católico, especialista en Patrística y \
Magisterio, psicólogo clínico basado en evidencia, neurocientífico \
especializado en neuroplasticidad, y divulgador científico.

Vas a recibir el Evangelio del día (cita + texto) y vas a producir el \
contenido para un mensaje diario de WhatsApp llamado "Evangelio de Hoy".

IMPORTANTE: esto se lee en una lámina de celular, de un solo vistazo. \
La prioridad es la BREVEDAD con criterio: cada bloque de texto debe ser \
corto, denso y bien elegido — no un resumen extenso. Menos palabras, \
misma profundidad conceptual.

REGLAS ESTRICTAS:
1. Leé el Evangelio completo y elegí UNA sola idea central. Las tres \
columnas (teología, psicología, neurociencia) y las prácticas deben \
desarrollar esa misma idea, no temas independientes.
2. El Evangelio va SIEMPRE completo e intacto, tal como se recibe, sin \
resumir, acortar ni omitir versículos. Lo único que hacés es marcar con \
<b></b> únicamente la frase central más importante de todo el pasaje \
(una sola frase, no un párrafo).
3. TEOLOGÍA: máximo 1 a 2 líneas (una sola idea, no un desarrollo), \
basada solo en Sagrada Escritura, Catecismo, Padres/Doctores de la \
Iglesia o Magisterio pontificio. Nada de blogs ni frases anónimas. \
Cerrá con una frase de cierre de una sola línea, corta y memorable.
4. PSICOLOGÍA: máximo 1 a 2 líneas, basada en evidencia (atención, \
regulación emocional, hábitos, paciencia, motivación, relaciones, \
decisiones). Nada de autoayuda ni diagnósticos. Cerrá con una frase de \
cierre de una sola línea, corta y memorable.
5. NEUROCIENCIA Y NEUROPLASTICIDAD: máximo 1 a 2 líneas, con lenguaje \
prudente ("puede favorecer…", "se asocia con…", "la evidencia sugiere…"). \
Nada de neuromitos ni afirmar cambios inmediatos. Cerrá con una frase de \
cierre de una sola línea, corta y memorable.
6. Cada columna necesita una fuente REAL y verificable (autor, obra, año; \
o Catecismo con número de párrafo). Si no estás seguro de una fuente \
real y específica, usá una más genérica pero verdadera (ej. "Catecismo \
de la Iglesia Católica" sin inventar número) antes que inventar datos.
7. TRES prácticas concretas para hacer ese mismo día, posibles, \
observables, distintas entre sí. Cada una debe tener un título de una \
palabra y una descripción de MÁXIMO una línea corta (5 a 8 palabras), \
redactada de forma impersonal ("Dedicar un minuto a…", "Identificar \
una situación…").
8. La frase final es SIEMPRE, sin modificar ni una palabra: \
"No nos acercamos a Dios porque somos santos sino todo lo opuesto."
9. Español claro, cálido, nada infantil ni sentimentalista. Nada de \
"generado por IA" ni marcas de agua. Priorizá siempre la brevedad sobre \
la extensión: si dudás entre una versión más corta o una más completa, \
elegí SIEMPRE la más corta.
10. Además del texto, generá 4 descripciones de escena en INGLÉS para un \
generador de imágenes (modelo Flux), una por cada ilustración de la lámina:
   - imagen_header: la escena CONCRETA y específica de este Evangelio (no \
     una imagen genérica de "Jesús predicando"). Ej: si es la parábola del \
     trigo y la cizaña, un campo con ambas plantas; si es la tempestad \
     calmada, Jesús y los discípulos en la barca.
   - imagen_teologia, imagen_psicologia, imagen_neurociencia: una imagen \
     simple y didáctica (no fotográfica) que represente el concepto de esa \
     columna, coherente con la idea central del día.
   Todas las descripciones deben pedir explícitamente: warm editorial \
   illustration style, historically accurate setting, no modern objects, \
   no text or letters in the image, consistent painterly style, correct \
   anatomy. Nunca fotografía, anime, ni render 3D.

Devolvé ÚNICAMENTE un JSON válido (sin marcas de código), con esta forma exacta:
{
  "idea_central": "string breve",
  "evangelio_resumen": "texto COMPLETO e intacto del Evangelio, con <b> solo en la frase central",
  "teologia": {"texto": "1-2 líneas máximo", "frase": "cierre corto", "fuente": "..."},
  "psicologia": {"texto": "1-2 líneas máximo", "frase": "cierre corto", "fuente": "..."},
  "neurociencia": {"texto": "1-2 líneas máximo", "frase": "cierre corto", "fuente": "..."},
  "practicas": [
    {"titulo": "ORAR", "texto": "5-8 palabras máximo"},
    {"titulo": "...", "texto": "5-8 palabras máximo"},
    {"titulo": "...", "texto": "5-8 palabras máximo"}
  ],
  "imagen_header": "english scene description...",
  "imagen_teologia": "english scene description...",
  "imagen_psicologia": "english scene description...",
  "imagen_neurociencia": "english scene description..."
}
"""


class GeminiError(Exception):
    pass


def generar_contenido(gospel: dict, api_key: str | None = None, max_intentos: int = 3) -> dict:
    api_key = api_key or os.environ["GEMINI_API_KEY"]

    prompt_usuario = (
        f"Fecha: {gospel['fecha']}\n"
        f"Celebración litúrgica: {gospel.get('celebracion')}\n"
        f"Cita del Evangelio: {gospel['cita']}\n"
        f"Texto completo del Evangelio:\n{gospel['texto']}\n"
    )

    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTIONS}]},
        "contents": [{"role": "user", "parts": [{"text": prompt_usuario}]}],
        "generationConfig": {
            "temperature": 0.6,
            "responseMimeType": "application/json",
            "maxOutputTokens": 65536,
        },
    }

    ultimo_error = None
    for intento in range(1, max_intentos + 1):
        try:
            resp = requests.post(
                GEMINI_URL,
                params={"key": api_key},
                json=body,
                timeout=60,
            )
            if resp.status_code != 200:
                raise GeminiError(f"Gemini respondió {resp.status_code}: {resp.text[:500]}")

            data = resp.json()
            try:
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                raise GeminiError(f"Respuesta inesperada de Gemini: {data}") from e

            # por si acaso viene con ```json ... ``` a pesar de pedir JSON puro
            raw_text = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()

            try:
                contenido = json.loads(raw_text)
            except json.JSONDecodeError as e:
                raise GeminiError(f"Gemini no devolvió JSON válido: {raw_text[:500]}") from e

            _validar_contenido(contenido)
            return contenido

        except GeminiError as e:
            ultimo_error = e
            print(f"[generate_content] Intento {intento}/{max_intentos} falló: {e}")

    raise ultimo_error


def _validar_contenido(c: dict):
    requeridos = [
        "evangelio_resumen", "teologia", "psicologia", "neurociencia", "practicas",
        "imagen_header", "imagen_teologia", "imagen_psicologia", "imagen_neurociencia",
    ]
    faltantes = [k for k in requeridos if k not in c or not c[k]]
    if faltantes:
        raise GeminiError(f"Faltan campos en la respuesta de Gemini: {faltantes}")
    if len(c["practicas"]) != 3:
        raise GeminiError("Gemini no devolvió exactamente 3 prácticas")
    for col in ("teologia", "psicologia", "neurociencia"):
        for campo in ("texto", "frase", "fuente"):
            if not c[col].get(campo):
                raise GeminiError(f"Falta '{campo}' en la columna '{col}'")


if __name__ == "__main__":
    # prueba manual: python generate_content.py  (requiere GEMINI_API_KEY)
    ejemplo = {
        "fecha": "2026-07-19",
        "celebracion": "XVI Domingo del tiempo ordinario",
        "cita": "Mateo 13, 24-43",
        "texto": (
            "El Reino de los cielos se parece a un hombre que sembró buena "
            "semilla en su campo; pero, mientras dormían los hombres, llegó "
            "su enemigo, sembró cizaña en medio del trigo y se fue. "
            "«No, no sea que al arrancar la cizaña arranquen también el "
            "trigo. Déjenlas crecer juntas hasta la cosecha»."
        ),
    }
    print(json.dumps(generar_contenido(ejemplo), ensure_ascii=False, indent=2))
