# src/main.py (or src/app/main.py depending on your project)
from fastapi import FastAPI, status
from src.workflow.tasks import store_email
from src.workflow.dto import EOIn

app = FastAPI()

@app.post("/workflow/eo", status_code=status.HTTP_202_ACCEPTED)
def queue_eo(eo: EOIn):
    store_email.delay(eo.model_dump())
    return {"queued": True, "message_id": eo.message_id}