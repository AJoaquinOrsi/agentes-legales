# Dockerfile para FOLIAR
# Agente de rellenado de formularios ART (Anexo I, Telegrama)

FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de FOLIAR
COPY . .

# Crear directorio para bases de datos y archivos temporales
RUN mkdir -p /app/instance /app/uploads /app/generated

# Exponer puerto (Flask)
EXPOSE 5000

# Environment variables por defecto
ENV FLASK_ENV=production
ENV FOLIAR_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)" || exit 1

# Comando para ejecutar con gunicorn (producción)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--worker-class", "gthread", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "app:app"]