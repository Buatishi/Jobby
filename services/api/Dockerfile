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

# Copiar el resto del código
COPY --chown=appuser:appuser . .

USER appuser

# Exponer puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
