name: Evangelio de Hoy — envío diario

on:
  schedule:
    # 07:30 UTC = 04:30 hora Argentina. Argentina no cambia de hora, así que
    # este valor sirve todo el año.
    #
    # OJO: el scheduler de GitHub es "mejor esfuerzo". Se atrasa seguido (a
    # veces una hora o más) y en horas pico puede saltearse corridas. Por eso
    # conviene además el disparador externo de cron-job.org. El bloque
    # concurrency de más abajo evita que salgan dos láminas si ambos disparan.
    - cron: "30 7 * * *"

  workflow_dispatch:
    inputs:
      fecha:
        description: "Fecha a generar (AAAA-MM-DD). Vacío = hoy."
        required: false
        type: string
      sin_enviar:
        description: "Generar la lámina sin mandar el correo"
        required: false
        type: boolean
        default: false

  # Es lo que llama cron-job.org vía la API de GitHub.
  repository_dispatch:
    types: [evangelio-diario]

concurrency:
  group: evangelio-diario
  cancel-in-progress: false

permissions:
  contents: read

jobs:
  lamina:
    runs-on: ubuntu-latest
    timeout-minutes: 25

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      # Falla acá, con un mensaje claro, en vez de reventar más adelante.
      - name: Verificar que estén los secrets
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
        run: |
          faltan=""
          [ -z "$GEMINI_API_KEY" ] && faltan="$faltan GEMINI_API_KEY"
          [ -z "$SMTP_USER" ]      && faltan="$faltan SMTP_USER"
          [ -z "$SMTP_PASS" ]      && faltan="$faltan SMTP_PASS"
          if [ -n "$faltan" ]; then
            echo "::error::Faltan estos secrets:$faltan"
            echo "Cargalos en Settings → Secrets and variables → Actions."
            exit 1
          fi
          echo "Secrets presentes."

      - name: Instalar dependencias
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Instalar Chromium para Playwright
        run: python -m playwright install --with-deps chromium

      - name: Generar y enviar la lámina
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
          EMAIL_TO: ${{ secrets.EMAIL_TO }}
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          # Los inputs van por variable de entorno, NO interpolados dentro del
          # comando: así una fecha con espacios o comillas no rompe el shell.
          FECHA: ${{ inputs.fecha }}
          SIN_ENVIAR: ${{ inputs.sin_enviar && '--sin-enviar' || '' }}
        run: python scripts/main.py $FECHA $SIN_ENVIAR

      # Queda descargable desde la corrida aunque el correo falle.
      - name: Guardar la lámina como artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: lamina
          path: salida/*.png
          if-no-files-found: warn
          retention-days: 14
