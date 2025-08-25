from dotenv import load_dotenv

load_dotenv()

# ...existing code...
# src/main.py (or src/app/main.py depending on your project)
from fastapi import FastAPI, status, HTTPException
from src.workflow.dto import EOIn

app = FastAPI()

@app.post("/workflow/eo", status_code=status.HTTP_202_ACCEPTED)
def queue_eo(eo: EOIn):
    from src.workflow.tasks import store_email
    try:
        store_email.delay(eo.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to queue EO for processing")
    return {
        "success": True,
        "message": "EO received and queued for processing",
        "data": {
            "message_id": eo.message_id
        }
    }

@app.get("/health_check", status_code=status.HTTP_200_OK)
def check_health():
    return {
        "success": True,
        "message": "Server is up and running"
    }

# --- NEW: PMO inbound webhook ---
from src.workflow.dto import PMOEmailIn
from src.workflow import repository as repo
from sqlalchemy.exc import IntegrityError

@app.post("/webhook/pmo_email", status_code=status.HTTP_202_ACCEPTED)
def webhook_pmo_email(email: PMOEmailIn):
    from src.workflow.tasks import process_pmo_response
    from src.workflow.parse_pmo import extract_eo_id_from_subject
    
    # Extract EO ID from subject if not provided
    related_eo_id = email.related_eo_id or extract_eo_id_from_subject(email.subject)
    
    # Validate EO exists before processing
    if related_eo_id:
        eo = repo.get_executive_order(related_eo_id)
        if not eo:
            error_msg = f"EO with ID '{related_eo_id}' not found in database. Please check the EO ID and try again."
            print(f"ERROR: {error_msg}")
            raise HTTPException(
                status_code=404, 
                detail={
                    "error": "EO not found",
                    "message": error_msg,
                    "eo_id": related_eo_id
                }
            )
        print(f"Validated EO exists: {related_eo_id} - {eo.title}")
    else:
        error_msg = "No EO ID found in PMO email (neither in related_eo_id nor subject). Cannot process PMO response."
        print(f"ERROR: {error_msg}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Missing EO ID",
                "message": error_msg
            }
        )
    
    # Persist inbound PMO email for audit
    email_log_id = None
    try:
        email_log = repo.save_email_log(
            direction="incoming",
            subject=email.subject,
            sender=email.sender,
            recipients=email.recipients,
            raw_content=email.body_text,
            related_eo_id=related_eo_id,
        )
        email_log_id = str(email_log.id)
        print(f"Saved PMO email log with ID: {email_log_id}")
    except Exception as e:
        print(f"Warning: Could not save PMO email log: {e}")
        # Non-fatal: still try to process
    
    # Add email log ID to the payload for organized file structure
    email_payload = email.model_dump()
    email_payload["email_log_id"] = email_log_id
    email_payload["related_eo_id"] = related_eo_id  # Ensure EO ID is set
    
    try:
        process_pmo_response.delay(email_payload)
    except Exception as e:
        print(f"ERROR: Failed to queue PMO email for processing: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue PMO email for processing")
    
    return {
        "success": True,
        "message": "PMO email queued for processing",
        "data": {
            "message_id": email.message_id,
            "related_eo_id": related_eo_id,
            "email_log_id": email_log_id
        }
    }

# --- NEW: Users ---
from src.workflow.dto import UserCreate
from src.db.users import create_user as db_create_user, create_users_bulk as db_create_users_bulk

@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    try:
        created = db_create_user(user.name, user.email, user.role, user.org_role)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to create user")
    return {
        "success": True,
        "message": "User created",
        "data": {
            "id": str(created.id),
            "name": created.name,
            "email": created.email,
            "role": created.role,
            "org_role": created.org_role,
            "is_active": created.is_active,
        }
    }

@app.post("/users/bulk", status_code=status.HTTP_201_CREATED)
def create_users_bulk(users: list[UserCreate]):
    if not users:
        raise HTTPException(status_code=400, detail="No users provided")
    try:
        created = db_create_users_bulk([u.model_dump() for u in users])
    except IntegrityError:
        raise HTTPException(status_code=409, detail="One or more emails already exist")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to create users")
    return {
        "success": True,
        "message": f"Created {len(created)} users",
        "data": [
            {
                "id": str(u.id),
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "org_role": u.org_role,
                "is_active": u.is_active,
            }
            for u in created
        ]
    }