import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# src/main.py
from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.routes import auth, application, dashboard, email_webhook, monitoring, chat
# Redis email processor runs in Celery worker, not API

app = FastAPI(
    title="DOL EO Management API",
    description="API for managing Executive Orders and related workflows",
    version="1.0.0"
)

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

@app.on_event("startup")
async def startup_event():
    """API startup - Redis email processor runs in Celery worker"""
    pass

@app.on_event("shutdown")
async def shutdown_event():
    """API shutdown"""
    pass

@app.get("/health_check", status_code=status.HTTP_200_OK)
def check_health():
    return {
        "success": True,
        "message": "Server is up and running"
    }

# Email queue statistics removed - email processing handled entirely by Celery worker