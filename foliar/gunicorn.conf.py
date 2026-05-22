# ── Gunicorn — configuración de producción ────────────────────────────────────
# Uso: gunicorn -c gunicorn.conf.py app:app

import multiprocessing

# Workers: fórmula recomendada = (2 × núcleos) + 1
# Con 8 núcleos → 17, pero 4-6 es más conservador para una app con threads
workers = 4

# Threads por worker (útil para SSE y requests lentos)
threads = 2

# Socket interno (Nginx se conecta acá)
bind = "127.0.0.1:8001"

# Timeout amplio para el procesamiento de PDFs con Claude (puede tardar 60-90s)
timeout = 180
graceful_timeout = 30
keepalive = 5

# Logs
accesslog = "/var/log/foliar/access.log"
errorlog  = "/var/log/foliar/error.log"
loglevel  = "info"

# Worker class — sync es suficiente con threads
worker_class = "sync"

# Reiniciar workers cada N requests (evita memory leaks)
max_requests = 500
max_requests_jitter = 50
