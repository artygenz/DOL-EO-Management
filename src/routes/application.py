from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.exc import IntegrityError
from src.workflow.dto import EOIn, PMOEmailIn, UserCreate
from src.workflow import repository as repo
from src.workflow.parse_pmo import extract_eo_id_from_subject
from src.db.users import create_user as db_create_user, create_users_bulk as db_create_users_bulk
from src.db.user_operations import create_user_with_password
from src.core.client_hub import get_database_session_maker

SessionLocal = get_database_session_maker()

router = APIRouter(prefix="/api/app", tags=["Application"])

@router.post("/workflow/eo", status_code=status.HTTP_202_ACCEPTED)
def queue_eo(eo: EOIn):
    """Queue EO for processing"""
    from src.workflow.chains.eo_processing_chain import process_eo_chain
    try:
        process_eo_chain.delay(eo.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to queue EO for processing")
    return {
        "success": True,
        "message": "EO received and queued for processing",
        "data": {
            "message_id": eo.message_id
        }
    }

@router.post("/webhook/pmo_email", status_code=status.HTTP_202_ACCEPTED)
def webhook_pmo_email(email: PMOEmailIn):
    """PMO email webhook for processing responses"""
    from src.workflow.chains.pmo_response_chain import process_pmo_response_chain
    
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
        process_pmo_response_chain.delay(email_payload)
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

@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    """Create a new user with default password"""
    db = SessionLocal()
    
    try:
        # Use the new function that handles password hashing
        created = create_user_with_password(
            db=db,
            name=user.name,
            email=user.email,
            password="Lumen@2025",  # Default password
            role=user.role,
            org_role=user.org_role
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    except Exception as e:
        print(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    return {
        "success": True,
        "message": "User created with default password 'Lumen@2025'",
        "data": {
            "id": str(created.id),
            "name": created.name,
            "email": created.email,
            "role": created.role,
            "org_role": created.org_role,
            "is_active": created.is_active,
        }
    }

@router.post("/users/bulk", status_code=status.HTTP_201_CREATED)
def create_users_bulk(users: list[UserCreate]):
    """Create multiple users in bulk"""
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
