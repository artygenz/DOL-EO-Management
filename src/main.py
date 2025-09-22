import logging
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Configure logging with file handler for API
log_dir = os.getenv("APP_LOG_DIR", "/app/logs")
try:
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir, exist_ok=True)
except Exception:
    log_dir = "/app/logs"

api_log_path = os.path.join(log_dir, "api.log")
handlers = [logging.StreamHandler()]
try:
    file_handler = logging.FileHandler(api_log_path)
    handlers.append(file_handler)
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers,
)

# src/main.py
from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.routes import auth, application, dashboard, email_webhook, monitoring, chat
# Redis email processor runs in Celery worker, not API
from typing import Optional

# Modular process starters
from src.app.processes import (
    start_celery_worker,
    stop_celery_worker,
    start_celery_beat,
    stop_celery_beat,
    start_imap_listener,
    stop_imap_listener,
)

app = FastAPI(
    title="DOL EO Management API",
    description="API for managing Executive Orders and related workflows",
    version="1.0.0"
)
@app.middleware("http")
async def request_logging_middleware(request, call_next):
    """Log each API request to the api.log file via root logger."""
    start_time = time.time()
    response = await call_next(request)
    process_ms = int((time.time() - start_time) * 1000)
    try:
        logging.info(
            "API %s %s -> %s (%d ms)",
            request.method,
            request.url.path,
            getattr(response, "status_code", "-"),
            process_ms,
        )
    except Exception:
        # Never block request on logging issues
        pass
    return response


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include modular routes
app.include_router(auth.router)
app.include_router(application.router)
app.include_router(dashboard.router)
app.include_router(email_webhook.router)
app.include_router(monitoring.router)
app.include_router(chat.router)

celery_worker_proc: Optional[object] = None
celery_beat_proc: Optional[object] = None
imap_listener_proc: Optional[object] = None


@app.on_event("startup")
async def startup_event():
    """API startup: start background services (worker, beat, imap)."""
    global celery_worker_proc, celery_beat_proc, imap_listener_proc
    try:
        celery_worker_proc = start_celery_worker()
    except Exception as e:
        logging.error(f"Failed to start Celery worker: {e}")
    try:
        celery_beat_proc = start_celery_beat()
    except Exception as e:
        logging.error(f"Failed to start Celery beat: {e}")
    try:
        imap_listener_proc = start_imap_listener()
    except Exception as e:
        logging.error(f"Failed to start IMAP listener: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """API shutdown: stop background services."""
    try:
        stop_imap_listener(imap_listener_proc)
    except Exception as e:
        logging.error(f"Failed to stop IMAP listener: {e}")
    try:
        stop_celery_beat(celery_beat_proc)
    except Exception as e:
        logging.error(f"Failed to stop Celery beat: {e}")
    try:
        stop_celery_worker(celery_worker_proc)
    except Exception as e:
        logging.error(f"Failed to stop Celery worker: {e}")

@app.get("/health_check", status_code=status.HTTP_200_OK)
def check_health():
    return {
        "success": True,
        "message": "Server is up and running",
        "services": {
            "celery_worker": bool(getattr(celery_worker_proc, "poll", None) is not None and celery_worker_proc.poll() is None) if celery_worker_proc else False,
            "celery_beat": bool(getattr(celery_beat_proc, "poll", None) is not None and celery_beat_proc.poll() is None) if celery_beat_proc else False,
            "imap_listener": bool(getattr(imap_listener_proc, "poll", None) is not None and imap_listener_proc.poll() is None) if imap_listener_proc else False,
        },
    }

# Email queue statistics removed - email processing handled entirely by Celery worker