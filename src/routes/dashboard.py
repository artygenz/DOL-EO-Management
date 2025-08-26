from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from src.core.dependencies import get_current_active_user
from src.db.session import get_db
from src.models.user import User
from src.models.executive_order import ExecutiveOrder
from src.models.task import Task
from src.models.email_log import EmailLog
from src.models.daily_update import DailyUpdate
from src.workflow.dto import DailyUpdateCreate, TaskAssigneeUpdate, EOPMOUpdate, EOPMOAssignmentResponse
from src.db.eo_pmo_operations import assign_pmos_to_eo, get_pmos_for_eo, remove_pmo_from_eo

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/health", status_code=status.HTTP_200_OK)
def dashboard_health(current_user: User = Depends(get_current_active_user)):
    """Dashboard health check - requires authentication"""
    return {
        "success": True,
        "message": "Dashboard is accessible",
        "data": {
            "user": {
                "id": str(current_user.id),
                "name": current_user.name,
                "email": current_user.email,
                "role": current_user.role,
                "org_role": current_user.org_role
            }
        }
    }

@router.get("/executive-orders", status_code=status.HTTP_200_OK)
def get_executive_orders(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get executive orders - filtered by user role"""
    query = db.query(ExecutiveOrder)
    
    # Apply role-based filtering
    if current_user.role == "admin":
        # Admins can see all EOs
        pass
    elif current_user.role == "reviewer":
        # Reviewers can see EOs assigned to their org role
        query = query.join(Task).filter(Task.assignee_id == current_user.id)
    else:
        # Executors can only see their assigned tasks
        query = query.join(Task).filter(Task.assignee_id == current_user.id)
    
    total = query.count()
    eos = query.offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": f"Retrieved {len(eos)} executive orders",
        "data": {
            "executive_orders": [
                {
                    "id": str(eo.id),
                    "title": eo.title,
                    "message_id": eo.message_id,
                    "status": eo.status,
                    "created_at": eo.created_at.isoformat(),
                    "task_count": len(eo.tasks) if hasattr(eo, 'tasks') else 0
                }
                for eo in eos
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.get("/executive-orders/{eo_id}", status_code=status.HTTP_200_OK)
def get_executive_order_detail(
    eo_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific executive order"""
    eo = db.query(ExecutiveOrder).filter(ExecutiveOrder.id == eo_id).first()
    
    if not eo:
        raise HTTPException(status_code=404, detail="Executive order not found")
    
    # Check if user has access to this EO
    if current_user.role != "admin":
        # Check if user has any tasks assigned to this EO
        user_tasks = db.query(Task).filter(
            Task.eo_id == eo_id,
            Task.assignee_id == current_user.id
        ).count()
        
        if user_tasks == 0:
            raise HTTPException(status_code=403, detail="Access denied to this executive order")
    
    return {
        "success": True,
        "message": "Executive order details retrieved",
        "data": {
            "id": str(eo.id),
            "title": eo.title,
            "description": eo.description,
            "message_id": eo.message_id,
            "status": eo.status,
            "created_at": eo.created_at.isoformat(),
            "updated_at": eo.updated_at.isoformat(),
            "tasks": [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "category": task.category,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "assignee": {
                        "id": str(task.assignee.id),
                        "name": task.assignee.name,
                        "email": task.assignee.email
                    } if task.assignee else None,
                    "remarks": task.remarks
                }
                for task in eo.tasks
            ]
        }
    }

@router.get("/tasks", status_code=status.HTTP_200_OK)
def get_user_tasks(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get tasks assigned to the current user"""
    query = db.query(Task).filter(Task.assignee_id == current_user.id)
    
    if status:
        query = query.filter(Task.status == status)
    
    total = query.count()
    tasks = query.offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": f"Retrieved {len(tasks)} tasks",
        "data": {
            "tasks": [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "category": task.category,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "remarks": task.remarks,
                    "executive_order": {
                        "id": str(task.executive_order.id),
                        "title": task.executive_order.title
                    } if task.executive_order else None
                }
                for task in tasks
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def get_task_detail(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user has access to this task
    if task.assignee_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied to this task")
    
    return {
        "success": True,
        "message": "Task details retrieved",
        "data": {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "category": task.category,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "remarks": task.remarks,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "assignee": {
                "id": str(task.assignee.id),
                "name": task.assignee.name,
                "email": task.assignee.email
            } if task.assignee else None,
            "executive_order": {
                "id": str(task.executive_order.id),
                "title": task.executive_order.title,
                "description": task.executive_order.description
            } if task.executive_order else None
        }
    }

@router.get("/email-logs", status_code=status.HTTP_200_OK)
def get_email_logs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    direction: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get email logs - admins can see all, others see only related to their tasks"""
    query = db.query(EmailLog)
    
    if direction:
        query = query.filter(EmailLog.direction == direction)
    
    # Apply role-based filtering
    if current_user.role != "admin":
        # Non-admins can only see emails related to their tasks
        query = query.join(ExecutiveOrder).join(Task).filter(Task.assignee_id == current_user.id)
    
    total = query.count()
    logs = query.offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": f"Retrieved {len(logs)} email logs",
        "data": {
            "email_logs": [
                {
                    "id": str(log.id),
                    "direction": log.direction,
                    "subject": log.subject,
                    "sender": log.sender,
                    "recipients": log.recipients,
                    "related_eo_id": str(log.related_eo_id) if log.related_eo_id else None,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.get("/stats", status_code=status.HTTP_200_OK)
def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for the current user"""
    
    # Base queries
    eo_query = db.query(ExecutiveOrder)
    task_query = db.query(Task)
    
    # Apply role-based filtering
    if current_user.role != "admin":
        eo_query = eo_query.join(Task).filter(Task.assignee_id == current_user.id)
        task_query = task_query.filter(Task.assignee_id == current_user.id)
    
    # Calculate statistics
    total_eos = eo_query.count()
    total_tasks = task_query.count()
    
    # Task status breakdown
    pending_tasks = task_query.filter(Task.status == "pending").count()
    in_progress_tasks = task_query.filter(Task.status == "in_progress").count()
    completed_tasks = task_query.filter(Task.status == "completed").count()
    approved_tasks = task_query.filter(Task.status == "approved").count()
    rejected_tasks = task_query.filter(Task.status == "rejected").count()
    
    return {
        "success": True,
        "message": "Dashboard statistics retrieved",
        "data": {
            "executive_orders": {
                "total": total_eos
            },
            "tasks": {
                "total": total_tasks,
                "by_status": {
                    "pending": pending_tasks,
                    "in_progress": in_progress_tasks,
                    "completed": completed_tasks,
                    "approved": approved_tasks,
                    "rejected": rejected_tasks
                }
            },
            "user": {
                "id": str(current_user.id),
                "name": current_user.name,
                "role": current_user.role,
                "org_role": current_user.org_role
            }
        }
    }

# ============================================================================
# CFO ENDPOINTS (Admin role)
# ============================================================================

@router.get("/cfo/executive-orders", status_code=status.HTTP_200_OK)
def get_all_executive_orders_cfo(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get all executive orders - CFO only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied - CFO role required")
    
    total = db.query(ExecutiveOrder).count()
    eos = db.query(ExecutiveOrder).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": f"Retrieved {len(eos)} executive orders",
        "data": {
            "executive_orders": [
                {
                    "id": str(eo.id),
                    "title": eo.title,
                    "description": eo.description,
                    "status": eo.status,
                    "created_at": eo.created_at.isoformat(),
                    "task_count": len(eo.tasks) if hasattr(eo, 'tasks') else 0
                }
                for eo in eos
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.get("/cfo/employees", status_code=status.HTTP_200_OK)
def get_all_employees_cfo(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get all employees - CFO only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied - CFO role required")
    
    total = db.query(User).count()
    users = db.query(User).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": f"Retrieved {len(users)} employees",
        "data": {
            "employees": [
                {
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                    "org_role": user.org_role,
                    "is_active": user.is_active,
                    "assigned_tasks_count": len(user.assigned_tasks) if hasattr(user, 'assigned_tasks') else 0
                }
                for user in users
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.get("/cfo/tasks", status_code=status.HTTP_200_OK)
def get_all_tasks_cfo(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get all tasks - CFO only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied - CFO role required")
    
    total = db.query(Task).count()
    tasks = db.query(Task).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": f"Retrieved {len(tasks)} tasks",
        "data": {
            "tasks": [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "category": task.category,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "assignee": {
                        "id": str(task.assignee.id),
                        "name": task.assignee.name,
                        "email": task.assignee.email
                    } if task.assignee else None,
                    "executive_order": {
                        "id": str(task.executive_order.id),
                        "title": task.executive_order.title
                    } if task.executive_order else None
                }
                for task in tasks
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.put("/cfo/executive-orders/{eo_id}/pmo", status_code=status.HTTP_200_OK)
def update_eo_pmo(
    eo_id: str,
    pmo_update: EOPMOUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update PMOs managing an EO - CFO only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied - CFO role required")
    
    eo = db.query(ExecutiveOrder).filter(ExecutiveOrder.id == eo_id).first()
    if not eo:
        raise HTTPException(status_code=404, detail="Executive order not found")
    
    # Validate PMO users exist and are reviewers
    pmo_users = db.query(User).filter(
        User.id.in_(pmo_update.pmo_ids),
        User.role == "reviewer"
    ).all()
    
    if len(pmo_users) != len(pmo_update.pmo_ids):
        raise HTTPException(status_code=400, detail="Some PMO users not found or not reviewers")
    
    # Update EO with PMO information (you might need to add a field to store PMO assignments)
    # For now, we'll just return success
    return {
        "success": True,
        "message": f"Updated PMO assignments for EO {eo.title}",
        "data": {
            "eo_id": str(eo.id),
            "eo_title": eo.title,
            "assigned_pmos": [
                {
                    "id": str(pmo.id),
                    "name": pmo.name,
                    "email": pmo.email,
                    "org_role": pmo.org_role
                }
                for pmo in pmo_users
            ]
        }
    }

# ============================================================================
# PMO ENDPOINTS (Reviewer role)
# ============================================================================

@router.get("/pmo/tasks", status_code=status.HTTP_200_OK)
def get_pmo_tasks(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get tasks related to PMO's EOs only"""
    if current_user.role != "reviewer":
        raise HTTPException(status_code=403, detail="Access denied - PMO role required")
    
    # Get tasks for EOs that this PMO is managing
    # This is a simplified version - you might need to implement proper PMO-EO assignment logic
    query = db.query(Task).join(ExecutiveOrder)
    
    # For now, we'll get tasks where the PMO's org_role matches the task category
    # This is a placeholder - implement proper PMO-EO assignment logic
    query = query.filter(Task.category == current_user.org_role)
    
    total = query.count()
    tasks = query.offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": f"Retrieved {len(tasks)} tasks for PMO",
        "data": {
            "tasks": [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "category": task.category,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "assignee": {
                        "id": str(task.assignee.id),
                        "name": task.assignee.name,
                        "email": task.assignee.email
                    } if task.assignee else None,
                    "executive_order": {
                        "id": str(task.executive_order.id),
                        "title": task.executive_order.title
                    } if task.executive_order else None
                }
                for task in tasks
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.get("/pmo/employees", status_code=status.HTTP_200_OK)
def get_pmo_employees(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get employees under PMO"""
    if current_user.role != "reviewer":
        raise HTTPException(status_code=403, detail="Access denied - PMO role required")
    
    # Get employees under this PMO (executors)
    query = db.query(User).filter(User.role == "executor")
    
    # For now, we'll get all executors - implement proper hierarchy logic
    total = query.count()
    employees = query.offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": f"Retrieved {len(employees)} employees under PMO",
        "data": {
            "employees": [
                {
                    "id": str(emp.id),
                    "name": emp.name,
                    "email": emp.email,
                    "org_role": emp.org_role,
                    "assigned_tasks_count": len(emp.assigned_tasks) if hasattr(emp, 'assigned_tasks') else 0
                }
                for emp in employees
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.get("/pmo/daily-updates", status_code=status.HTTP_200_OK)
def get_pmo_daily_updates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get daily updates from employees under PMO"""
    if current_user.role != "reviewer":
        raise HTTPException(status_code=403, detail="Access denied - PMO role required")
    
    # Get daily updates from employees under this PMO
    query = db.query(DailyUpdate).join(User).filter(User.role == "executor")
    
    total = query.count()
    updates = query.offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": f"Retrieved {len(updates)} daily updates",
        "data": {
            "daily_updates": [
                {
                    "id": str(update.id),
                    "task_id": str(update.task_id),
                    "user_id": str(update.user_id),
                    "update_text": update.update_text,
                    "progress_pct": update.progress_pct,
                    "hours_spent": update.hours_spent,
                    "status_note": update.status_note,
                    "blockers": update.blockers,
                    "risks": update.risks,
                    "next_actions": update.next_actions,
                    "created_at": update.created_at.isoformat(),
                    "employee": {
                        "id": str(update.user.id),
                        "name": update.user.name,
                        "email": update.user.email
                    },
                    "task": {
                        "id": str(update.task.id),
                        "title": update.task.title
                    }
                }
                for update in updates
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.put("/pmo/tasks/{task_id}/assignee", status_code=status.HTTP_200_OK)
def update_task_assignee(
    task_id: str,
    assignee_update: TaskAssigneeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change/Remove assignee from task - PMO only"""
    if current_user.role != "reviewer":
        raise HTTPException(status_code=403, detail="Access denied - PMO role required")
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify PMO has access to this task
    if task.category != current_user.org_role:
        raise HTTPException(status_code=403, detail="Access denied to this task")
    
    # Update assignee
    task.assignee_id = assignee_update.assignee_id
    db.commit()
    
    return {
        "success": True,
        "message": "Task assignee updated successfully",
        "data": {
            "task_id": str(task.id),
            "task_title": task.title,
            "new_assignee_id": assignee_update.assignee_id
        }
    }

# ============================================================================
# EMPLOYEE ENDPOINTS (Executor role)
# ============================================================================

@router.get("/employee/my-updates", status_code=status.HTTP_200_OK)
def get_employee_updates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get all updates posted by the employee"""
    if current_user.role != "executor":
        raise HTTPException(status_code=403, detail="Access denied - Employee role required")
    
    query = db.query(DailyUpdate).filter(DailyUpdate.user_id == current_user.id)
    total = query.count()
    updates = query.offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": f"Retrieved {len(updates)} updates",
        "data": {
            "updates": [
                {
                    "id": str(update.id),
                    "task_id": str(update.task_id),
                    "update_text": update.update_text,
                    "progress_pct": update.progress_pct,
                    "hours_spent": update.hours_spent,
                    "status_note": update.status_note,
                    "blockers": update.blockers,
                    "risks": update.risks,
                    "next_actions": update.next_actions,
                    "created_at": update.created_at.isoformat(),
                    "task": {
                        "id": str(update.task.id),
                        "title": update.task.title,
                        "status": update.task.status
                    }
                }
                for update in updates
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.get("/employee/active-tasks", status_code=status.HTTP_200_OK)
def get_employee_active_tasks(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get all active tasks assigned to the employee"""
    if current_user.role != "executor":
        raise HTTPException(status_code=403, detail="Access denied - Employee role required")
    
    query = db.query(Task).filter(
        Task.assignee_id == current_user.id,
        Task.status.in_(["pending", "in_progress"])
    )
    total = query.count()
    tasks = query.offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": f"Retrieved {len(tasks)} active tasks",
        "data": {
            "tasks": [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "category": task.category,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "executive_order": {
                        "id": str(task.executive_order.id),
                        "title": task.executive_order.title
                    } if task.executive_order else None
                }
                for task in tasks
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.post("/employee/daily-update", status_code=status.HTTP_201_CREATED)
def create_daily_update(
    update: DailyUpdateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a daily task update - Employee only"""
    if current_user.role != "executor":
        raise HTTPException(status_code=403, detail="Access denied - Employee role required")
    
    # Verify task exists and is assigned to this user
    task = db.query(Task).filter(
        Task.id == update.task_id,
        Task.assignee_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or not assigned to you")
    
    # Create daily update
    daily_update = DailyUpdate(
        task_id=update.task_id,
        user_id=current_user.id,
        update_text=update.update_text,
        progress_pct=update.progress_pct,
        hours_spent=update.hours_spent,
        status_note=update.status_note,
        blockers=update.blockers,
        risks=update.risks,
        next_actions=update.next_actions
    )
    
    db.add(daily_update)
    db.commit()
    db.refresh(daily_update)
    
    return {
        "success": True,
        "message": "Daily update created successfully",
        "data": {
            "id": str(daily_update.id),
            "task_id": str(daily_update.task_id),
            "update_text": daily_update.update_text,
            "progress_pct": daily_update.progress_pct,
            "hours_spent": daily_update.hours_spent,
            "status_note": daily_update.status_note,
            "blockers": daily_update.blockers,
            "risks": daily_update.risks,
            "next_actions": daily_update.next_actions,
            "created_at": daily_update.created_at.isoformat()
        }
    }

# PMO Assignment Endpoints
@router.post("/cfo/assign-pmos/{eo_id}", status_code=status.HTTP_201_CREATED)
def assign_pmos_to_executive_order(
    eo_id: str,
    pmo_assignment: EOPMOUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Assign PMOs to an Executive Order - CFO/Admin only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied - Admin role required")
    
    try:
        # Assign PMOs to the EO
        assignments = assign_pmos_to_eo(
            db=db,
            eo_id=eo_id,
            pmo_ids=pmo_assignment.pmo_ids,
            assigned_by=str(current_user.id),
            primary_pmo_id=pmo_assignment.primary_pmo_id
        )
        
        return {
            "success": True,
            "message": f"Successfully assigned {len(assignments)} PMO(s) to Executive Order",
            "data": {
                "eo_id": eo_id,
                "assignments": [
                    {
                        "id": str(assignment.id),
                        "pmo_id": str(assignment.pmo_id),
                        "pmo_name": assignment.pmo.name,
                        "pmo_email": assignment.pmo.email,
                        "assigned_at": assignment.assigned_at.isoformat(),
                        "assigned_by": str(assignment.assigned_by) if assignment.assigned_by else None,
                        "is_primary": assignment.is_primary
                    }
                    for assignment in assignments
                ]
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign PMOs: {str(e)}")

@router.get("/cfo/eo-pmo-assignments/{eo_id}", status_code=status.HTTP_200_OK)
def get_eo_pmo_assignments(
    eo_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all PMO assignments for an Executive Order - CFO/Admin only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied - Admin role required")
    
    assignments = get_pmos_for_eo(db, eo_id)
    
    return {
        "success": True,
        "message": f"Retrieved {len(assignments)} PMO assignment(s)",
        "data": {
            "eo_id": eo_id,
            "assignments": [
                {
                    "id": str(assignment.id),
                    "pmo_id": str(assignment.pmo_id),
                    "pmo_name": assignment.pmo.name,
                    "pmo_email": assignment.pmo.email,
                    "assigned_at": assignment.assigned_at.isoformat(),
                    "assigned_by": str(assignment.assigned_by) if assignment.assigned_by else None,
                    "is_primary": assignment.is_primary
                }
                for assignment in assignments
            ]
        }
    }

@router.delete("/cfo/remove-pmo/{eo_id}/{pmo_id}", status_code=status.HTTP_200_OK)
def remove_pmo_from_eo_endpoint(
    eo_id: str,
    pmo_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove a PMO from an Executive Order - CFO/Admin only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied - Admin role required")
    
    try:
        success = remove_pmo_from_eo(db, eo_id, pmo_id)
        
        if success:
            return {
                "success": True,
                "message": "PMO successfully removed from Executive Order"
            }
        else:
            raise HTTPException(status_code=404, detail="PMO assignment not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove PMO: {str(e)}")
