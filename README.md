# Evangelio de Hoy — lámina diaria por WhatsApp

Automatización 100% gratuita que todos los días a las **4:30 a.m. (hora Argentina)**:

1. Obtiene el Evangelio del día y lo verifica en **dos fuentes católicas independientes**
   (ACI Prensa como principal, Dominicos.org como segunda fuente).
2. Genera, con IA, la interpretación teológica, psicológica y neurocientífica de la
   idea central del Evangelio, más 3 prácticas concretas para ese día y las 4
   ilustraciones de la lámina — todo nuevo cada día, atado al Evangelio de esa
   fecha puntual.
3. Renderiza la lámina completa (mismo diseño que tu imagen modelo) en una imagen.
4. Te la manda a tu propio WhatsApp para que la revises **antes de subirla a tu
   estado**.
5. El número de serie (`01.WS`, `02.WS`, ...) se calcula solo contando los días
   desde el 19 de julio de 2026 — nunca hay que tocarlo a mano.

## Costo: $0

| Pieza | Herramienta | Por qué es gratis |
|---|---|---|
| Orquestación diaria | GitHub Actions | Gratis para repos personales, muy por debajo del límite de minutos/mes |
| Texto (3 columnas + prácticas + prompts de imagen) | Gemini API (Google AI Studio) | Free tier permanente, sin tarjeta: ~1.000-1.500 solicitudes/día |
| Las 4 ilustraciones | Pollinations.ai, modelo Flux | Gratis e ilimitado, sin cuenta ni API key |
| Render de la lámina (HTML → PNG) | Playwright (Chromium headless) | Corre dentro del propio runner de GitHub Actions, sin costo extra |
| Envío a WhatsApp | Wappfly | Plan gratis (~50 mensajes/mes); usamos 1/día = 30/mes |
| Fuente del Evangelio | ACI Prensa + Dominicos.org | Páginas web públicas, sin API key |

No hay ningún paso pago en este flujo.

## Estructura del repo

```
evangelio-diario/
├── scripts/
│   ├── fetch_gospel.py       # obtiene y cruza el Evangelio en 2 fuentes
│   ├── generate_content.py   # genera texto + prompts de imagen con Gemini
│   ├── generate_images.py    # genera las 4 ilustraciones con Pollinations/Flux
│   ├── render_lamina.py      # combina plantilla + imágenes -> PNG final
│   ├── format_message.py     # numeración WS + utilidades de fecha
│   ├── send_whatsapp.py      # envía la imagen por Wappfly
│   └── main.py                # orquesta todo (esto es lo que corre GitHub Actions)
├── templates/
│   └── template.html          # plantilla visual de la lámina (HTML/CSS)
├── requirements.txt
└── .github/workflows/daily.yml   # el cron diario
```

## Puesta en marcha (una sola vez)

### 1. Crear el repo
Subí esta carpeta a un repo de GitHub (puede ser privado, no hace falta que sea público).

### 2. Conseguir tu API key gratis de Gemini
1. Entrá a https://aistudio.google.com/apikey
2. "Create API key" — no pide tarjeta.
3. Copiá la key.

### 3. Conseguir tu token de Wappfly (gratis)
1. Entrá a https://wappfly.com y creá una cuenta.
2. Vinculá un número de WhatsApp escaneando el código QR (igual que WhatsApp Web).
   **Importante:** este número es el que *envía* la lámina — tiene que ser distinto
   al número que la *recibe* (el tuyo). Si solo tenés un número personal, necesitás
   un segundo número/línea (SIM extra, número virtual, WhatsApp Business en otro
   chip) para vincular acá.
3. Copiá el token de la sesión desde el dashboard.

### 4. Cargar los secrets en GitHub
En tu repo: **Settings → Secrets and variables → Actions → New repository secret**,
y cargá estos tres:

| Nombre | Valor |
|---|---|
| `GEMINI_API_KEY` | la key del paso 2 |
| `WAPPFLY_TOKEN` | el token del paso 3 |
| `WHATSAPP_TO` | tu número personal con código de país, sin "+" ni espacios (ej `5491122334455`) |

### 5. Probarlo
Andá a la pestaña **Actions** de tu repo → "Evangelio de Hoy - envío diario" →
**Run workflow**. Corré una vez a mano y revisá que te llegue la imagen a WhatsApp
(la primera corrida tarda un poco más porque instala Chromium). Si algo falla, el
log de Actions muestra el error exacto — decime qué dice y lo ajustamos.

### 6. Listo
A partir de ahí corre solo, todos los días a las 4:30 a.m. hora Argentina, y te
llega la lámina lista para revisar y subir a tu estado.

## Notas de diseño

- **Verificación en 2 fuentes:** si ACI Prensa y Dominicos.org no coinciden en
  libro/capítulo, la lámina se genera igual (con la fuente principal) pero
  `verificado_en_dos_fuentes` queda en `false` en los logs de Actions.
- **Numeración WS:** `format_message.calcular_ws()` la calcula matemáticamente
  a partir de la fecha (días desde el 19/07/2026 + 1). No hay ningún contador
  guardado en ningún archivo ni base de datos — imposible que se desincronice
  de la fecha o del Evangelio del día.
- **Contenido e ilustraciones siempre nuevos:** cada corrida le pasa a Gemini el
  Evangelio real de ese día (texto completo) y le pide elegir una sola idea
  central, desarrollarla en las 3 columnas + prácticas, y describir 4 escenas
  específicas de ese Evangelio para las ilustraciones — nunca reutiliza nada
  de días anteriores.
- **Por qué la imagen y no solo texto:** la lámina se manda como imagen (no
  como texto plano) porque el objetivo es que la revises tal cual va a quedar
  en tu estado de WhatsApp antes de publicarla.
- **Caption del mensaje:** junto con la imagen llega un pie corto con la cita
  y el número de serie, para identificarla rápido en el chat.
