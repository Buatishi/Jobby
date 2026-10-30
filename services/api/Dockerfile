FROM python:3.13-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar Poetry
RUN pip install poetry==2.4.1

# Copiar archivos de dependencias primero (para cache de Docker)
COPY pyproject.toml poetry.lock* ./

# Instalar dependencias sin crear virtualenv (estamos en Docker)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Usuario sin privilegios: si alguien lograra ejecutar código dentro del contenedor, no
# sería root. Las dependencias ya quedaron instaladas arriba (como root, solo lectura aquí).
RUN useradd --create-home --uid 10001 appuser

# Chromium para el análisis de un puesto por URL (Playwright). Las librerías del sistema
# se instalan como root; el navegador, como appuser, en su ~/.cache/ms-playwright, que es
# donde Playwright lo busca al ejecutar. Solo el "headless shell" (lo que usa
# headless=True): suma unos 230 MB a la imagen comprimida. Va antes de copiar el código
# para que un cambio de código no lo vuelva a descargar. Ver Decisión 38.
RUN playwright install-deps chromium \
    && rm -rf /var/lib/apt/lists/*
USER appuser
RUN playwright install --only-shell chromium

# Copiar el resto del código
COPY --chown=appuser:appuser . .

USER appuser

# Exponer puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
