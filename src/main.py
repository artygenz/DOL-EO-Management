import logging
import os
import time

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
from typing import Optional, Dict, Any
import time

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

# Import connection testing functions from monitoring module
from src.routes.monitoring import (
    test_redis_connection,
    test_celery_connection,
    test_database_connection,
    test_email_configuration,
    test_openai_connection
)

def test_imap_listener_connection() -> Dict[str, Any]:
    """Test IMAP listener service health"""
    try:
        # Check if IMAP listener process is running
        imap_healthy = bool(getattr(imap_listener_proc, "poll", None) is not None and imap_listener_proc.poll() is None) if imap_listener_proc else False
        
        # Use the existing email configuration test for IMAP settings
        email_config = test_email_configuration()
        
        return {
            "connected": imap_healthy and email_config.get("connected", False),
            "process_running": imap_healthy,
            "configuration": email_config,
            "status": "healthy" if imap_healthy and email_config.get("connected", False) else "unhealthy"
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "status": "unhealthy"
        }

def test_email_notification_service() -> Dict[str, Any]:
    """Test email notification service (SMTP configuration and Redis email queue)"""
    try:
        # Test Redis email queue
        redis_status = test_redis_connection()
        
        # Test SMTP configuration
        email_config = test_email_configuration()
        
        return {
            "connected": redis_status.get("connected", False) and email_config.get("connected", False),
            "redis_queue": redis_status,
            "smtp_configuration": email_config,
            "status": "healthy" if redis_status.get("connected", False) and email_config.get("connected", False) else "unhealthy"
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "status": "unhealthy"
        }

@app.get("/api/health")
def simple_health_check():
    """Simple health check for ALB - only checks if server is up"""
    return {
        "status": "healthy",
        "message": "Server is running",
        "timestamp": time.time()
    }

@app.get("/api/health_check")
def comprehensive_health_check():
    """Comprehensive health check that returns error if any critical service fails"""
    results = {
        "timestamp": time.time(),
        "overall_status": "healthy",
        "services": {}
    }
    
    # Test all critical services
    redis_status = test_redis_connection()
    results["services"]["redis"] = redis_status
    
    celery_status = test_celery_connection()
    results["services"]["celery"] = celery_status
    
    db_status = test_database_connection()
    results["services"]["database"] = db_status
    
    imap_status = test_imap_listener_connection()
    results["services"]["imap_listener"] = imap_status
    
    email_status = test_email_notification_service()
    results["services"]["email_notification"] = email_status
    
    # Test OpenAI connection
    openai_status = test_openai_connection()
    results["services"]["openai"] = openai_status
    
    # Check Celery worker and beat processes
    celery_worker_healthy = bool(getattr(celery_worker_proc, "poll", None) is not None and celery_worker_proc.poll() is None) if celery_worker_proc else False
    celery_beat_healthy = bool(getattr(celery_beat_proc, "poll", None) is not None and celery_beat_proc.poll() is None) if celery_beat_proc else False
    
    results["services"]["celery_worker"] = {
        "connected": celery_worker_healthy,
        "process_running": celery_worker_healthy,
        "status": "healthy" if celery_worker_healthy else "unhealthy"
    }
    
    results["services"]["celery_beat"] = {
        "connected": celery_beat_healthy,
        "process_running": celery_beat_healthy,
        "status": "healthy" if celery_beat_healthy else "unhealthy"
    }
    
    # Determine overall status
    failed_services = []
    for service_name, service_status in results["services"].items():
        if not service_status.get("connected", False):
            failed_services.append(service_name)
    
    if failed_services:
        results["overall_status"] = "unhealthy"
        results["failed_services"] = failed_services
        # Return 503 Service Unavailable if any service fails
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "One or more critical services are unavailable",
                "failed_services": failed_services,
                "services": results["services"]
            }
        )
    
    return results

# Email queue statistics removed - email processing handled entirely by Celery worker