from src.workflow.dto import EOIn
from src.workflow import repository as repo
from src.workflow.ai import extract_tasks

def run_pipeline_sync(eo: EOIn):
    eo_row = repo.upsert_executive_order(eo)
    tasks = extract_tasks(eo.body_text)
    inserted = repo.insert_tasks(eo_row.id, tasks)
    repo.update_eo_status(eo_row.id, "processed")
    return {"eo_id": str(eo_row.id), "inserted": inserted}