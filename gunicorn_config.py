import multiprocessing
import os

# Bind
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Workers
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "biddentalplataforma"

# Preload app
preload_app = True

# Graceful timeout
graceful_timeout = 30

print(f"Gunicorn configurado: {workers} workers na porta {bind.split(':')[1]}")
