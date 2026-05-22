FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements desde la carpeta correcta
COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY . .

RUN mkdir -p /app/uploads /app/logs

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 ENVIRONMENT=production

HEALTHCHECK CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]