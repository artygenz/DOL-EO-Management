"""
Monitoring Routes

This module provides API endpoints for monitoring Celery tasks and email queue operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import os
import redis
import time
import subprocess
import sys
import logging
from pathlib import Path
from celery import Celery

logger = logging.getLogger(__name__)

from src.core.dependencies import get_current_user
from src.core.client_hub import get_database_session_maker

def get_db():
    """Get database session generator for FastAPI dependency injection."""
    db = get_database_session_maker()()
    try:
        yield db
    finally:
        db.close()
from src.models.user import User
from src.models.celery_task_log import CeleryTaskLog
from src.models.email_queue_log import EmailQueueLog
from src.email.queue_logger import EmailQueueLogger

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/celery/tasks", response_model=Dict[str, Any])
def get_celery_task_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    task_name: Optional[str] = Query(None),
    eo_id: Optional[str] = Query(None)
):
    """Get Celery task execution logs"""
    
    # Only admins can view monitoring logs
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = db.query(CeleryTaskLog)
    
    # Apply filters
    if status:
        query = query.filter(CeleryTaskLog.status == status)
    if task_name:
        query = query.filter(CeleryTaskLog.task_name.ilike(f"%{task_name}%"))
    if eo_id:
        query = query.filter(CeleryTaskLog.eo_id == eo_id)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    tasks = query.order_by(desc(CeleryTaskLog.created_at)).offset(offset).limit(limit).all()
    
    # Convert to dict for JSON response
    task_logs = []
    for task in tasks:
        task_logs.append({
            "id": str(task.id),
            "task_id": task.task_id,
            "task_name": task.task_name,
            "status": task.status,
            "worker_name": task.worker_name,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration_seconds": task.duration_seconds,
            "error_message": task.error_message,
            "retry_count": task.retry_count,
            "eo_id": task.eo_id,
            "email_log_id": task.email_log_id,
            "created_at": task.created_at.isoformat()
        })
    
    return {
        "tasks": task_logs,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/celery/stats", response_model=Dict[str, Any])
def get_celery_task_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get Celery task statistics"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get stats for last 24 hours
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    
    # Status counts
    status_counts = {}
    for status in ["started", "success", "failure", "retry"]:
        count = db.query(CeleryTaskLog).filter(
            CeleryTaskLog.status == status,
            CeleryTaskLog.created_at >= yesterday
        ).count()
        status_counts[status] = count
    
    # Task type counts
    task_counts = db.query(
        CeleryTaskLog.task_name,
        func.count(CeleryTaskLog.id).label('count')
    ).filter(
        CeleryTaskLog.created_at >= yesterday
    ).group_by(CeleryTaskLog.task_name).all()
    
    task_type_counts = {task_name: count for task_name, count in task_counts}
    
    # Average duration for successful tasks
    avg_duration = db.query(func.avg(CeleryTaskLog.duration_seconds)).filter(
        CeleryTaskLog.status == "success",
        CeleryTaskLog.duration_seconds.isnot(None),
        CeleryTaskLog.created_at >= yesterday
    ).scalar()
    
    return {
        "period": "last_24_hours",
        "status_counts": status_counts,
        "task_type_counts": task_type_counts,
        "average_duration_seconds": float(avg_duration) if avg_duration else None,
        "total_tasks": sum(status_counts.values())
    }

@router.get("/email/queue", response_model=Dict[str, Any])
def get_email_queue_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    email_type: Optional[str] = Query(None),
    is_rate_limited: Optional[bool] = Query(None)
):
    """Get email queue logs"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = db.query(EmailQueueLog)
    
    # Apply filters
    if status:
        query = query.filter(EmailQueueLog.status == status)
    if email_type:
        query = query.filter(EmailQueueLog.email_type == email_type)
    if is_rate_limited is not None:
        query = query.filter(EmailQueueLog.is_rate_limited == is_rate_limited)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    emails = query.order_by(desc(EmailQueueLog.created_at)).offset(offset).limit(limit).all()
    
    # Convert to dict for JSON response
    email_logs = []
    for email in emails:
        email_logs.append({
            "id": str(email.id),
            "email_id": email.email_id,
            "to_addresses": email.to_addresses,
            "subject": email.subject,
            "email_type": email.email_type,
            "priority": email.priority,
            "status": email.status,
            "queued_at": email.queued_at.isoformat(),
            "started_processing_at": email.started_processing_at.isoformat() if email.started_processing_at else None,
            "completed_at": email.completed_at.isoformat() if email.completed_at else None,
            "smtp_response_code": email.smtp_response_code,
            "retry_count": email.retry_count,
            "is_rate_limited": email.is_rate_limited,
            "error_message": email.error_message,
            "outbox_saved": email.outbox_saved,
            "eo_id": email.eo_id,
            "celery_task_id": email.celery_task_id
        })
    
    return {
        "emails": email_logs,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/email/stats", response_model=Dict[str, Any])
def get_email_queue_stats(
    current_user: User = Depends(get_current_user)
):
    """Get email queue statistics"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return EmailQueueLogger.get_queue_stats()

@router.get("/dashboard", response_model=Dict[str, Any])
def get_monitoring_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get monitoring dashboard data"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get recent activity (last hour)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    
    # Recent Celery tasks
    recent_tasks = db.query(CeleryTaskLog).filter(
        CeleryTaskLog.created_at >= one_hour_ago
    ).count()
    
    failed_tasks = db.query(CeleryTaskLog).filter(
        CeleryTaskLog.status == "failure",
        CeleryTaskLog.created_at >= one_hour_ago
    ).count()
    
    # Recent emails
    recent_emails = db.query(EmailQueueLog).filter(
        EmailQueueLog.created_at >= one_hour_ago
    ).count()
    
    failed_emails = db.query(EmailQueueLog).filter(
        EmailQueueLog.status.in_(["failed", "abandoned"]),
        EmailQueueLog.created_at >= one_hour_ago
    ).count()
    
    rate_limited_emails = db.query(EmailQueueLog).filter(
        EmailQueueLog.is_rate_limited == True,
        EmailQueueLog.created_at >= one_hour_ago
    ).count()
    
    # Current queue status
    email_stats = EmailQueueLogger.get_queue_stats()
    
    return {
        "period": "last_hour",
        "celery": {
            "recent_tasks": recent_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": ((recent_tasks - failed_tasks) / recent_tasks * 100) if recent_tasks > 0 else 100
        },
        "email": {
            "recent_emails": recent_emails,
            "failed_emails": failed_emails,
            "rate_limited_emails": rate_limited_emails,
            "success_rate": ((recent_emails - failed_emails) / recent_emails * 100) if recent_emails > 0 else 100,
            "current_queue": email_stats
        }
    }

@router.get("/health/connections", response_model=Dict[str, Any])
def test_all_connections(
    current_user: User = Depends(get_current_user)
):
    """Test all client connections (Redis, Celery, Database, etc.)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": "healthy",
        "services": {}
    }
    
    # Test Redis Connection
    redis_status = test_redis_connection()
    results["services"]["redis"] = redis_status
    
    # Test Celery Connection
    celery_status = test_celery_connection()
    results["services"]["celery"] = celery_status
    
    # Test Database Connection
    db_status = test_database_connection()
    results["services"]["database"] = db_status
    
    # Test OpenAI Connection (if configured)
    openai_status = test_openai_connection()
    results["services"]["openai"] = openai_status
    
    # Test Email Configuration
    email_status = test_email_configuration()
    results["services"]["email"] = email_status
    
    # Determine overall status
    failed_services = [name for name, status in results["services"].items() if not status.get("connected", False)]
    if failed_services:
        results["overall_status"] = "degraded"
        results["failed_services"] = failed_services
    
    return results

def test_redis_connection() -> Dict[str, Any]:
    """Test Redis connection and basic operations"""
    try:
        # Get Redis configuration
        redis_host = os.getenv('REDIS_HOST', 'redis')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_url = os.getenv('REDIS_URL', f'redis://{redis_host}:{redis_port}/0')
        
        start_time = time.time()
        
        # Test connection
        r = redis.from_url(redis_url)
        r.ping()
        
        # Test basic operations
        test_key = f"health_check_{int(time.time())}"
        r.set(test_key, "test_value", ex=60)  # Expire in 60 seconds
        value = r.get(test_key)
        r.delete(test_key)
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "connected": True,
            "host": redis_host,
            "port": redis_port,
            "url": redis_url,
            "response_time_ms": response_time,
            "operations_tested": ["ping", "set", "get", "delete"],
            "status": "healthy"
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "status": "unhealthy"
        }

def test_celery_connection() -> Dict[str, Any]:
    """Test Celery broker and result backend connections"""
    try:
        # Get Celery configuration
        broker_url = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://redis:6379/0'))
        result_backend = os.getenv('CELERY_RESULT_BACKEND', broker_url)
        
        start_time = time.time()
        
        # Create Celery app
        celery_app = Celery(
            'health_check',
            broker=broker_url,
            backend=result_backend
        )
        
        # Test broker connection
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        # Test result backend
        backend_result = celery_app.backend.get('test_result')
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "connected": True,
            "broker_url": broker_url,
            "result_backend": result_backend,
            "response_time_ms": response_time,
            "worker_stats": stats,
            "status": "healthy"
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "status": "unhealthy"
        }

def test_database_connection() -> Dict[str, Any]:
    """Test database connection and basic query"""
    try:
        start_time = time.time()
        
        # Get database session
        db = get_database_session_maker()()
        
        try:
            # Test basic query
            result = db.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            
            # Test table access (try to query users table)
            user_count = db.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                "connected": True,
                "response_time_ms": response_time,
                "test_query_result": test_value,
                "user_count": user_count,
                "status": "healthy"
            }
            
        finally:
            db.close()
            
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "status": "unhealthy"
        }

def test_openai_connection() -> Dict[str, Any]:
    """Test OpenAI API connection"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return {
                "connected": False,
                "error": "OPENAI_API_KEY not configured",
                "status": "not_configured"
            }
        
        # Basic validation
        if len(api_key) < 20:
            return {
                "connected": False,
                "error": "Invalid API key format",
                "status": "unhealthy"
            }
        
        # Test actual API connection with a minimal request
        import openai
        start_time = time.time()
        
        client = openai.OpenAI(api_key=api_key)
        
        # Make a simple API call to test the key validity
        response = client.models.list()
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "connected": True,
            "api_key_valid": True,
            "response_time_ms": response_time,
            "models_available": len(response.data) if response.data else 0,
            "status": "healthy"
        }
        
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "invalid_api_key" in error_msg.lower():
            return {
                "connected": False,
                "error": "Invalid API key provided",
                "status": "unhealthy"
            }
        elif "403" in error_msg:
            return {
                "connected": False,
                "error": "API key lacks required permissions",
                "status": "unhealthy"
            }
        else:
            return {
                "connected": False,
                "error": f"API connection failed: {error_msg}",
                "status": "unhealthy"
            }

def test_email_configuration() -> Dict[str, Any]:
    """Test email configuration"""
    try:
        # Check required email environment variables
        required_vars = [
            'IMAP_HOST', 'IMAP_USERNAME', 'IMAP_PASSWORD',
            'SMTP_HOST', 'SMTP_USERNAME', 'SMTP_PASSWORD'
        ]
        
        missing_vars = []
        configured_vars = []
        
        for var in required_vars:
            value = os.getenv(var)
            if value and value != f"your_{var.lower()}" and "your_" not in value:
                configured_vars.append(var)
            else:
                missing_vars.append(var)
        
        if missing_vars:
            return {
                "connected": False,
                "missing_variables": missing_vars,
                "configured_variables": configured_vars,
                "status": "incomplete"
            }
        
        return {
            "connected": True,
            "configured_variables": configured_vars,
            "imap_host": os.getenv('IMAP_HOST'),
            "smtp_host": os.getenv('SMTP_HOST'),
            "status": "healthy"
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "status": "unhealthy"
        }

@router.post("/migrations/upgrade", response_model=Dict[str, Any])
def run_database_migrations():
    """Run Alembic database migrations to upgrade database schema"""
    
    try:
        # Get the project root directory - in Docker container, working dir is /app
        project_root = Path("/app")
        alembic_ini_path = project_root / "alembic.ini"
        
        # Debug: Log the paths being checked
        logger.warning(f"Project root: {project_root}")
        logger.warning(f"Alembic ini path: {alembic_ini_path}")
        logger.warning(f"Current working directory: {os.getcwd()}")
        logger.warning(f"Alembic ini exists: {alembic_ini_path.exists()}")
        
        if not alembic_ini_path.exists():
            # Try alternative paths
            alternative_paths = [
                Path("/app/alembic.ini"),
                Path("./alembic.ini"),
                Path("alembic.ini")
            ]
            
            for alt_path in alternative_paths:
                logger.warning(f"Checking alternative path: {alt_path} - exists: {alt_path.exists()}")
                if alt_path.exists():
                    alembic_ini_path = alt_path
                    project_root = alt_path.parent
                    break
            else:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Alembic configuration file not found. Checked paths: {[str(p) for p in alternative_paths]}"
                )
        
        # Change to project directory for alembic commands
        original_cwd = os.getcwd()
        os.chdir(project_root)
        
        try:
            # Run alembic upgrade head
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = f"Migration failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f"\nError output: {result.stderr}"
                raise HTTPException(status_code=500, detail=error_msg)
            
            # Get current revision after migration
            current_result = subprocess.run(
                [sys.executable, "-m", "alembic", "current"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            current_revision = "unknown"
            if current_result.returncode == 0:
                current_revision = current_result.stdout.strip()
            
            return {
                "success": True,
                "message": "Database migrations completed successfully",
                "output": result.stdout,
                "current_revision": current_revision,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
            
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500, 
            detail="Migration timed out after 5 minutes"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to run migrations: {str(e)}"
        )

@router.get("/migrations/status", response_model=Dict[str, Any])
def get_migration_status(
    current_user: User = Depends(get_current_user)
):
    """Get current database migration status"""
    
    # Only admins can check migration status
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get the project root directory
        project_root = Path(__file__).resolve().parents[3]
        alembic_ini_path = project_root / "alembic.ini"
        
        if not alembic_ini_path.exists():
            raise HTTPException(
                status_code=500, 
                detail="Alembic configuration file not found"
            )
        
        # Change to project directory for alembic commands
        original_cwd = os.getcwd()
        os.chdir(project_root)
        
        try:
            # Get current revision
            current_result = subprocess.run(
                [sys.executable, "-m", "alembic", "current"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Get history
            history_result = subprocess.run(
                [sys.executable, "-m", "alembic", "history", "--verbose"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Get head revision
            head_result = subprocess.run(
                [sys.executable, "-m", "alembic", "heads"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            current_revision = current_result.stdout.strip() if current_result.returncode == 0 else "unknown"
            head_revision = head_result.stdout.strip() if head_result.returncode == 0 else "unknown"
            is_up_to_date = current_revision == head_revision
            
            return {
                "current_revision": current_revision,
                "head_revision": head_revision,
                "is_up_to_date": is_up_to_date,
                "history": history_result.stdout if history_result.returncode == 0 else "Failed to get history",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get migration status: {str(e)}"
        )

@router.get("/health/database", response_model=Dict[str, Any])
def test_database_health(
    current_user: User = Depends(get_current_user)
):
    """Test database connection health with detailed diagnostics"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        start_time = time.time()
        
        # Get database session
        db = get_database_session_maker()()
        
        try:
            # Test basic connectivity
            result = db.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            
            # Test table access and get table counts
            table_counts = {}
            tables_to_check = ['users', 'executive_orders', 'tasks', 'email_logs', 'celery_task_logs']
            
            for table in tables_to_check:
                try:
                    count_result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    table_counts[table] = count_result.fetchone()[0]
                except Exception as e:
                    table_counts[table] = f"Error: {str(e)}"
            
            # Test database version and info
            version_result = db.execute(text("SELECT version()"))
            db_version = version_result.fetchone()[0]
            
            # Test connection pool status
            try:
                pool = db.bind.pool
                pool_status = {
                    "pool_size": getattr(pool, 'size', lambda: 'unknown')(),
                    "checked_in": getattr(pool, 'checkedin', lambda: 'unknown')(),
                    "checked_out": getattr(pool, 'checkedout', lambda: 'unknown')(),
                    "overflow": getattr(pool, 'overflow', lambda: 'unknown')()
                }
            except Exception as e:
                pool_status = {
                    "pool_size": "unknown",
                    "checked_in": "unknown", 
                    "checked_out": "unknown",
                    "overflow": "unknown",
                    "error": str(e)
                }
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                "connected": True,
                "response_time_ms": response_time,
                "test_query_result": test_value,
                "database_version": db_version,
                "table_counts": table_counts,
                "connection_pool": pool_status,
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        finally:
            db.close()
            
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@router.get("/health/redis", response_model=Dict[str, Any])
def test_redis_health(
    current_user: User = Depends(get_current_user)
):
    """Test Redis connection health with detailed diagnostics"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get Redis configuration
        redis_host = os.getenv('REDIS_HOST', 'redis')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_url = os.getenv('REDIS_URL', f'redis://{redis_host}:{redis_port}/0')
        
        start_time = time.time()
        
        # Test connection
        r = redis.from_url(redis_url)
        r.ping()
        
        # Test basic operations
        test_key = f"health_check_{int(time.time())}"
        r.set(test_key, "test_value", ex=60)  # Expire in 60 seconds
        value = r.get(test_key)
        r.delete(test_key)
        
        # Get Redis info
        redis_info = r.info()
        
        # Test different Redis operations
        operations_tested = []
        try:
            # Test string operations
            r.set("test_string", "value", ex=10)
            r.get("test_string")
            r.delete("test_string")
            operations_tested.append("string_ops")
        except Exception as e:
            operations_tested.append(f"string_ops_failed: {e}")
        
        try:
            # Test list operations
            r.lpush("test_list", "item1", "item2")
            r.lrange("test_list", 0, -1)
            r.delete("test_list")
            operations_tested.append("list_ops")
        except Exception as e:
            operations_tested.append(f"list_ops_failed: {e}")
        
        try:
            # Test hash operations
            r.hset("test_hash", "field1", "value1")
            r.hget("test_hash", "field1")
            r.delete("test_hash")
            operations_tested.append("hash_ops")
        except Exception as e:
            operations_tested.append(f"hash_ops_failed: {e}")
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "connected": True,
            "host": redis_host,
            "port": redis_port,
            "url": redis_url,
            "response_time_ms": response_time,
            "operations_tested": operations_tested,
            "redis_info": {
                "version": redis_info.get('redis_version'),
                "uptime_seconds": redis_info.get('uptime_in_seconds'),
                "connected_clients": redis_info.get('connected_clients'),
                "used_memory_human": redis_info.get('used_memory_human'),
                "keyspace_hits": redis_info.get('keyspace_hits'),
                "keyspace_misses": redis_info.get('keyspace_misses')
            },
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
@router.get("/logs/celery-worker", response_model=Dict[str, Any])
def get_celery_worker_logs(
    current_user: User = Depends(get_current_user),
    lines: int = Query(100, ge=1, le=1000)
):
    """Get last N lines of Celery worker logs"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        log_file = Path("logs/celery_worker.log")
        if not log_file.exists():
            return {
                "success": False,
                "error": "Celery worker log file not found",
                "logs": [],
                "total_lines": 0
            }
        
        # Read last N lines
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "success": True,
            "service": "celery-worker",
            "lines_requested": lines,
            "lines_returned": len(last_lines),
            "total_lines": len(all_lines),
            "logs": [line.rstrip() for line in last_lines],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read Celery worker logs: {str(e)}"
        )

@router.get("/logs/imap-listener", response_model=Dict[str, Any])
def get_imap_listener_logs(
    current_user: User = Depends(get_current_user),
    lines: int = Query(100, ge=1, le=1000)
):
    """Get last N lines of IMAP listener logs"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        log_file = Path("logs/imap_listener.log")
        if not log_file.exists():
            return {
                "success": False,
                "error": "IMAP listener log file not found",
                "logs": [],
                "total_lines": 0
            }
        
        # Read last N lines
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "success": True,
            "service": "imap-listener",
            "lines_requested": lines,
            "lines_returned": len(last_lines),
            "total_lines": len(all_lines),
            "logs": [line.rstrip() for line in last_lines],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read IMAP listener logs: {str(e)}"
        )

@router.get("/logs/celery-beat", response_model=Dict[str, Any])
def get_celery_beat_logs(
    current_user: User = Depends(get_current_user),
    lines: int = Query(100, ge=1, le=1000)
):
    """Get last N lines of Celery beat logs"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        log_file = Path("logs/celery_beat.log")
        if not log_file.exists():
            return {
                "success": False,
                "error": "Celery beat log file not found",
                "logs": [],
                "total_lines": 0
            }
        
        # Read last N lines
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "success": True,
            "service": "celery-beat",
            "lines_requested": lines,
            "lines_returned": len(last_lines),
            "total_lines": len(all_lines),
            "logs": [line.rstrip() for line in last_lines],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read Celery beat logs: {str(e)}"
        )

@router.get("/logs/all", response_model=Dict[str, Any])
def get_all_service_logs(
    current_user: User = Depends(get_current_user),
    lines: int = Query(100, ge=1, le=1000)
):
    """Get last N lines of all service logs"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    services = ["celery-worker", "imap-listener", "celery-beat"]
    results = {}
    
    for service in services:
        try:
            if service == "celery-worker":
                log_file = Path("logs/celery_worker.log")
            elif service == "imap-listener":
                log_file = Path("logs/imap_listener.log")
            elif service == "celery-beat":
                log_file = Path("logs/celery_beat.log")
            
            if not log_file.exists():
                results[service] = {
                    "success": False,
                    "error": f"{service} log file not found",
                    "logs": [],
                    "total_lines": 0
                }
                continue
            
            # Read last N lines
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            results[service] = {
                "success": True,
                "lines_requested": lines,
                "lines_returned": len(last_lines),
                "total_lines": len(all_lines),
                "logs": [line.rstrip() for line in last_lines]
            }
            
        except Exception as e:
            results[service] = {
                "success": False,
                "error": str(e),
                "logs": [],
                "total_lines": 0
            }
    
    return {
        "success": True,
        "services": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
