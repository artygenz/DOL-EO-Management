from dotenv import load_dotenv

load_dotenv()

# ...existing code...
# src/main.py (or src/app/main.py depending on your project)
from fastapi import FastAPI, status
from src.workflow.dto import EOIn

app = FastAPI()

@app.post("/workflow/eo", status_code=status.HTTP_202_ACCEPTED)
def queue_eo(eo: EOIn):
    from src.workflow.tasks import store_email
    store_email.delay(eo.model_dump())
    print("Sent the request")
    return {"queued": True, "message_id": eo.message_id}

@app.get("/health_check", status_code=status.HTTP_200_OK)
def check_health():
    return {
        "Server is up and running"
    }