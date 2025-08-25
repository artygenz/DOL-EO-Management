from dotenv import load_dotenv

load_dotenv()

# src/main.py
from fastapi import FastAPI, status, HTTPException
from src.routes import auth, application, dashboard

app = FastAPI(
    title="DOL EO Management API",
    description="API for managing Executive Orders and related workflows",
    version="1.0.0"
)

# Include modular routes
app.include_router(auth.router)
app.include_router(application.router)
app.include_router(dashboard.router)

@app.get("/health_check", status_code=status.HTTP_200_OK)
def check_health():
    return {
        "success": True,
        "message": "Server is up and running"
    }