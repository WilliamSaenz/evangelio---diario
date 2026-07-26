# Evangelio de Hoy — lámina diaria

Automatización que todos los días a las **4:30 a.m. (hora Argentina)**:

1. Obtiene el Evangelio del día **pidiéndolo por fecha explícita** y lo verifica
   cruzando tres fuentes católicas independientes.
2. Genera con IA la interpretación teológica, psicológica y neurocientífica de
   la idea central, 3 prácticas concretas para ese día y 5 ilustraciones —
   todo nuevo cada día, atado al Evangelio de esa fecha puntual.
3. Renderiza la lámina completa en un PNG de 2400 px de ancho.
4. Te la manda por email para que la revises antes de subirla a tu estado.

El número de serie (`01.WS`, `02.WS`, ...) se calcula solo, contando los días
desde el **26 de julio de 2026**.

---

## Qué cambió respecto de la versión anterior

Estos son los tres problemas que venían apareciendo y cómo quedaron resueltos.

### 1. El Evangelio del día equivocado

**Causa:** las tres fuentes se pedían por su página "de hoy", y `fetch_from_dominicos()`
ni siquiera recibía la fecha objetivo — no tenía nada que comparar. Si a las 4:30 ART
un sitio todavía no había rotado el contenido, devolvía el Evangelio del día anterior
con un HTTP 200 perfectamente normal.

Y acá está lo importante: **la votación por mayoría no protege contra eso**. Si dos
sitios están desactualizados a la misma hora de la madrugada, coinciden entre sí en el
Evangelio de ayer y le ganan por mayoría a la única fuente fresca. Sumar fuentes no
arregla este problema; lo empeora.

**Solución:** anclar la fecha en la URL. Dos de las tres fuentes son direccionables por
fecha, así que se les pide el día explícitamente y no pueden devolver otro:

| Fuente | URL por fecha | Formato |
|---|---|---|
| dominicos.org (ferias) | `/predicacion/evangelio-del-dia/26-7-2026/` | **sin** ceros a la izquierda |
| dominicos.org (domingos) | `/predicacion/homilia/26-7-2026/lecturas/` | **sin** ceros a la izquierda |
| evangeli.net | `/evangelio/dia/2026-07-26` | **con** ceros a la izquierda |

Los dos formatos son distintos: `26-07-2026` da 404 en dominicos, y `2026-7-26` da 404
en evangeli. Además se valida que la página devuelta mencione la fecha pedida antes de
aceptarla.

Sobre esto se agregan dos reglas de seguridad:

- Si las dos fuentes ancladas se contradicen, **se aborta**. No se deja que Ciudad
  Redonda (que solo publica "hoy") desempate, porque ese es justamente el mecanismo
  que puede publicar el Evangelio de ayer.
- La mayoría tiene que incluir al menos una fuente anclada por fecha.

### 2. El JSON inválido de Gemini

**Causa:** se le pedía a Gemini "respondé solo JSON" y se parseaba el texto a
mano. Cuando la respuesta salía cortada o con backticks, reventaba. Subir
`maxOutputTokens` ayudaba pero no lo eliminaba, porque el problema no era solo
de longitud.

**Solución:** salida estructurada real (`responseMimeType: application/json` +
`responseSchema`). La API garantiza JSON válido y conforme al esquema. Ya no hay
limpieza de backticks ni parseo defensivo.

### 3. La lámina que nunca llegaba

**Causa:** Wappfly aceptaba el envío (200/202) pero las imágenes quedaban en
`queued` para siempre. Era un problema del lado del proveedor.

**Solución:** envío por SMTP. Si el servidor acepta el mensaje, se entrega. La
lámina va dos veces en el mismo correo: embebida en el cuerpo para verla de una,
y adjunta como PNG para guardarla y subirla al estado.

Además: si la corrida falla por cualquier motivo, ahora te llega un **correo de
aviso**. Antes te enterabas por ausencia, al día siguiente.

---

## Fuentes del Evangelio

| Fuente | Anclada por fecha | Aporta texto | Rol |
|---|---|---|---|
| **dominicos.org** | Sí | Sí | Fuente principal del texto |
| **evangeli.net** | Sí | Sí | Verificación + respaldo del texto |
| **ciudadredonda.org** | No (solo "hoy") | No | Solo verificación de la cita |

Se exige que **al menos 2 de las 3** coincidan en libro + capítulo. Los versículos
no se comparan a propósito: distintos leccionarios recortan la perícopa con un
versículo de diferencia sin que eso signifique otro Evangelio.

Como dominicos y evangeli aportan texto completo, **si una se cae la corrida
sigue**. Antes, si se caía dominicos no había lámina, porque era la única con texto.

Si no hay mayoría, o si las dos ancladas se contradicen, **no se genera lámina** y
te llega el aviso. Es preferible un día sin lámina a un día con el Evangelio
equivocado.

ACI Prensa y Vatican News quedaron **descartadas** por fallas recurrentes.

Nota: dominicos.org sigue el Calendario Litúrgico del Vaticano con variaciones
propias de la Conferencia Episcopal Española y de la Orden de Predicadores. En
días de memoria opcional, distintos sitios pueden diferir legítimamente entre la
lectura propia del santo y la ferial. Por eso la comparación es sobre libro y
capítulo, no sobre el versículo exacto.

---

## Estructura

```
evangelio-diario/
├── scripts/
│   ├── config.py           # TODO lo configurable vive acá
│   ├── format_message.py   # numeración WS + fechas en español
│   ├── fetch_gospel.py     # Evangelio por fecha + verificación 2 de 3
│   ├── generate_content.py # Gemini con salida estructurada
│   ├── generate_images.py  # 5 ilustraciones (Pollinations / Flux)
│   ├── render_lamina.py    # plantilla -> PNG
│   ├── send_email.py       # envío SMTP + aviso de fallo
│   └── main.py             # orquestador
├── templates/
│   └── template.html       # diseño de la lámina
├── requirements.txt
└── .github/workflows/daily.yml
```

---

## Puesta en marcha

### 1. Subir los archivos

Subí todo el contenido de esta carpeta a la **rama por defecto** del repo
(normalmente `main`). Importante: GitHub solo ejecuta workflows programados si
el archivo `.github/workflows/daily.yml` está en la rama por defecto. En una
rama secundaria el `schedule` nunca dispara.

### 2. Contraseña de aplicación de Gmail

La contraseña normal de tu cuenta **no funciona** con SMTP. Necesitás una
contraseña de aplicación:

1. Entrá a https://myaccount.google.com/security
2. Activá la **verificación en 2 pasos** si no la tenés (es requisito).
3. Buscá "Contraseñas de aplicaciones" y generá una nueva.
4. Google te muestra 16 letras en 4 grupos (`abcd efgh ijkl mnop`). Podés
   pegarla con o sin espacios: el script los saca solo.

### 3. Secrets del repo

**Settings → Secrets and variables → Actions → New repository secret**

Obligatorios, los tres:

| Nombre | Valor |
|---|---|
| `GEMINI_API_KEY` | key de https://aistudio.google.com/apikey (gratis, sin tarjeta) |
| `SMTP_USER` | tu Gmail completo, el que envía (ej. `tucuenta@gmail.com`) |
| `SMTP_PASS` | la contraseña de aplicación del paso 2 |

Opcionales, solo si querés cambiar el comportamiento por defecto:

| Nombre | Por defecto si no lo creás |
|---|---|
| `EMAIL_TO` | el mismo `SMTP_USER` (te lo mandás a vos) |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `465` |

A diferencia de otros proveedores, Gmail funciona con la misma cuenta como
remitente y destinatario, así que con `SMTP_USER` alcanza: no hace falta una
segunda casilla. Esto es distinto de lo que pasaba con WhatsApp, donde sí
necesitabas dos números.

El workflow chequea que los tres obligatorios estén cargados **antes** de
hacer nada, y si falta alguno corta con un mensaje que dice cuál.

### 4. Probar a mano

Pestaña **Actions** → "Evangelio de Hoy — envío diario" → **Run workflow**.
Podés pasarle una fecha puntual y tildar "sin enviar" para generar sin mandar
correo. La lámina queda siempre descargable como *artifact* de la corrida,
aunque el correo falle.

### 5. Disparador externo

El `schedule` de GitHub Actions es **best-effort**: en horarios de mucha carga se
atrasa (a veces una hora o más) y a veces directamente no corre. Además, GitHub
**deshabilita los workflows programados** en repos sin actividad durante 60 días.
Por eso conviene el cronjob externo en cron-job.org.

El workflow acepta `repository_dispatch`, que es lo más simple de configurar:

- **URL:** `https://api.github.com/repos/USUARIO/REPO/dispatches`
- **Método:** POST
- **Headers:**
  - `Accept: application/vnd.github+json`
  - `Authorization: Bearer TU_TOKEN` (token con permiso `contents: write`)
  - `Content-Type: application/json`
- **Body:** `{"event_type": "evangelio-diario"}`
- **Horario:** 04:30, zona `America/Argentina/Buenos_Aires`

El workflow tiene un `concurrency` group, así que si el cron interno de GitHub y
el externo de cron-job.org disparan los dos, no salen dos láminas.

---

## Uso local

```bash
pip install -r requirements.txt
python -m playwright install --with-deps chromium

python scripts/main.py                 # el Evangelio de hoy
python scripts/main.py 2026-08-15      # una fecha puntual
python scripts/main.py --sin-enviar    # genera sin mandar correo

python scripts/format_message.py       # ver qué número de serie toca hoy
python scripts/fetch_gospel.py         # probar solo la cadena de fuentes
```

---

## Notas de diseño

- **El Evangelio va completo e intacto.** Lo único que se le hace es envolver la
  frase clave en negrita. Si la frase que devuelve Gemini no coincide literal, se
  busca la coincidencia más larga; si tampoco aparece, se deja sin resaltar antes
  que alterar el texto.
- **Prácticas rotativas.** Las 3 prácticas cambian cada día según el tema del
  Evangelio, y cada una lleva su propio ícono elegido de un catálogo de 18. Son
  SVG inline, no emojis: el runner de GitHub Actions no siempre tiene fuentes de
  emoji instaladas y salían como cuadrados vacíos.
- **La ilustración de cierre es siempre distinta** de las otras cuatro, con
  alusión explícita a Jesús mostrando misericordia con alguien.
- **Semilla determinística por día y bloque.** Si hay que reintentar la corrida
  entera, salen las mismas imágenes; días distintos dan imágenes distintas, y
  los 5 bloques nunca comparten semilla.
- **Si una ilustración falla**, ese bloque sale con un panel liso del color
  correspondiente. La lámina se genera igual.

## Costo

| Pieza | Herramienta | Costo |
|---|---|---|
| Orquestación | GitHub Actions | Gratis en repos personales |
| Texto | Gemini API (AI Studio) | Free tier permanente |
| Ilustraciones | Pollinations.ai / Flux | Gratis, sin API key |
| Render | Playwright + Chromium | Corre en el propio runner |
| Envío | SMTP | Gratis |
| Fuentes | Webs públicas | Sin API key |
