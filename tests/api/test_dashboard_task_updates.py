"""
Test suite for the updated dashboard task update endpoints.
Tests the migration from daily_updates to task_updates table.
"""
import pytest
import datetime as dt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.main import app
from src.db.session import get_db, SessionLocal
from src.models.user import User
from src.models.executive_order import ExecutiveOrder
from src.models.task import Task
from src.models.task_update import TaskUpdate
from src.models.eo_pmo_assignment import EOPMOAssignment
from src.core.auth import create_access_token
import uuid

client = TestClient(app)

# Test data setup
def create_test_user(db: Session, role: str = "executor", email: str = None, name: str = None):
    """Create a test user with the specified role"""
    # Use unique identifiers to avoid conflicts
    test_id = str(uuid.uuid4())[:8]
    user = User(
        id=uuid.uuid4(),
        name=name or f"Test {role.title()} {test_id}",
        email=email or f"test.{role}.{test_id}@example.com",
        role=role,
        org_role="Test Department",
        is_active=True,
        password_hash="test_hash"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_test_eo(db: Session):
    """Create a test Executive Order"""
    test_id = str(uuid.uuid4())[:8]
    eo = ExecutiveOrder(
        id=uuid.uuid4(),
        title=f"Test Executive Order {test_id}",
        description="Test EO for task updates",
        message_id=f"test_msg_{test_id}",
        status="processed"
    )
    db.add(eo)
    db.commit()
    db.refresh(eo)
    return eo

def create_test_task(db: Session, eo_id: uuid.UUID, assignee_id: uuid.UUID):
    """Create a test task"""
    task = Task(
        id=uuid.uuid4(),
        eo_id=eo_id,
        title="Test Task for Updates",
        description="Test task description",
        status="in_progress",
        category="Test Category",
        assignee_id=assignee_id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def create_test_task_update(db: Session, eo_id: uuid.UUID, task_id: uuid.UUID, user_id: uuid.UUID):
    """Create a test task update"""
    task_update = TaskUpdate(
        id=uuid.uuid4(),
        eo_id=eo_id,
        task_id=task_id,
        user_id=user_id,
        date=dt.date.today(),
        progress_pct=50,
        status="InProgress",
        notes="Test update notes",
        blockers=["Test blocker"],
        risks=["Test risk"],
        spent_hours=4.0
    )
    db.add(task_update)
    db.commit()
    db.refresh(task_update)
    return task_update

def create_pmo_assignment(db: Session, eo_id: uuid.UUID, pmo_id: uuid.UUID):
    """Create PMO assignment for EO"""
    assignment = EOPMOAssignment(
        id=uuid.uuid4(),
        eo_id=eo_id,
        pmo_id=pmo_id,
        assigned_by=pmo_id,
        is_primary=True
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment

def get_auth_header(user: User):
    """Get authorization header for user"""
    token = create_access_token(data={"sub": str(user.id)})  # sub should be the user ID
    return {"Authorization": f"Bearer {token}"}

class TestEmployeeDailyUpdateEndpoints:
    """Test employee endpoints for creating and viewing updates"""
    
    def setup_method(self):
        """Setup test data"""
        self.db = SessionLocal()
        
        # Create test users
        self.executor = create_test_user(self.db, role="executor")
        self.pmo = create_test_user(self.db, role="reviewer")
        
        # Create test EO and task
        self.eo = create_test_eo(self.db)
        self.task = create_test_task(self.db, self.eo.id, self.executor.id)
        
        # Create PMO assignment
        self.pmo_assignment = create_pmo_assignment(self.db, self.eo.id, self.pmo.id)
        
    def teardown_method(self):
        """Clean up test data"""
        # Clean up in reverse order of dependencies
        self.db.query(TaskUpdate).delete()
        self.db.query(EOPMOAssignment).delete()
        self.db.query(Task).delete()
        self.db.query(ExecutiveOrder).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_create_daily_update_success(self):
        """Test successful creation of daily update"""
        headers = get_auth_header(self.executor)
        
        update_data = {
            "task_id": str(self.task.id),
            "update_text": "Made good progress on the task",
            "progress_pct": 75,
            "hours_spent": 6.0,
            "status_note": "in progress",
            "blockers": {"blocker1": "Waiting for approval"},
            "risks": {"risk1": "Timeline may slip"},
            "next_actions": {"action1": "Continue implementation"}
        }
        
        response = client.post("/dashboard/employee/daily-update", json=update_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Daily update created successfully"
        assert data["data"]["task_id"] == str(self.task.id)
        assert data["data"]["update_text"] == "Made good progress on the task"
        assert data["data"]["progress_pct"] == 75
        assert data["data"]["hours_spent"] == 6.0
        assert data["data"]["status_note"] == "InProgress"  # Should be mapped to enum
        assert data["data"]["blockers"] == ["Waiting for approval"]  # Converted from dict
        assert data["data"]["risks"] == ["Timeline may slip"]  # Converted from dict
        assert data["data"]["next_actions"] == []  # Empty as not supported
        
        # Verify data was stored in database
        task_update = self.db.query(TaskUpdate).filter(TaskUpdate.task_id == self.task.id).first()
        assert task_update is not None
        assert task_update.notes == "Made good progress on the task"
        assert task_update.progress_pct == 75
        assert task_update.spent_hours == 6.0
        assert task_update.status == "InProgress"

    def test_create_daily_update_status_mapping(self):
        """Test status mapping from free text to enum values"""
        headers = get_auth_header(self.executor)
        
        # Test various status mappings
        status_tests = [
            ("completed", "Completed"),
            ("done", "Completed"),
            ("finished", "Completed"),
            ("in progress", "InProgress"),
            ("working", "InProgress"),
            ("blocked", "Blocked"),
            ("stuck", "Blocked"),
            ("not started", "NotStarted"),
            ("pending", "NotStarted"),
            ("Completed", "Completed"),  # Direct enum value
            ("invalid_status", None)  # Invalid status should be None
        ]
        
        for input_status, expected_enum in status_tests:
            update_data = {
                "task_id": str(self.task.id),
                "update_text": f"Testing status: {input_status}",
                "status_note": input_status
            }
            
            response = client.post("/dashboard/employee/daily-update", json=update_data, headers=headers)
            assert response.status_code == 201
            
            data = response.json()
            if expected_enum:
                assert data["data"]["status_note"] == expected_enum
            else:
                assert data["data"]["status_note"] == ""

    def test_create_daily_update_unauthorized(self):
        """Test unauthorized access"""
        update_data = {
            "task_id": str(self.task.id),
            "update_text": "Unauthorized update"
        }
        
        response = client.post("/dashboard/employee/daily-update", json=update_data)
        assert response.status_code == 403  # FastAPI returns 403 when no auth header provided

    def test_create_daily_update_wrong_role(self):
        """Test access with wrong role (PMO trying to create update)"""
        headers = get_auth_header(self.pmo)
        
        update_data = {
            "task_id": str(self.task.id),
            "update_text": "PMO trying to create update"
        }
        
        response = client.post("/dashboard/employee/daily-update", json=update_data, headers=headers)
        assert response.status_code == 403
        assert "Employee role required" in response.json()["detail"]

    def test_create_daily_update_task_not_found(self):
        """Test update for non-existent task"""
        headers = get_auth_header(self.executor)
        
        update_data = {
            "task_id": str(uuid.uuid4()),  # Random task ID
            "update_text": "Update for non-existent task"
        }
        
        response = client.post("/dashboard/employee/daily-update", json=update_data, headers=headers)
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    def test_get_employee_updates_success(self):
        """Test retrieving employee's own updates"""
        # Create some test updates
        update1 = create_test_task_update(self.db, self.eo.id, self.task.id, self.executor.id)
        update2 = create_test_task_update(self.db, self.eo.id, self.task.id, self.executor.id)
        
        headers = get_auth_header(self.executor)
        response = client.get("/dashboard/employee/my-updates", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["updates"]) == 2
        
        # Check structure of returned updates
        update_data = data["data"]["updates"][0]
        assert "id" in update_data
        assert "task_id" in update_data
        assert "update_text" in update_data
        assert "progress_pct" in update_data
        assert "hours_spent" in update_data
        assert "status_note" in update_data
        assert "blockers" in update_data
        assert "risks" in update_data
        assert "next_actions" in update_data
        assert "created_at" in update_data
        assert "task" in update_data

    def test_get_employee_updates_unauthorized(self):
        """Test unauthorized access to employee updates"""
        response = client.get("/dashboard/employee/my-updates")
        assert response.status_code == 403  # FastAPI returns 403 when no auth header provided

    def test_get_employee_updates_wrong_role(self):
        """Test access with wrong role"""
        headers = get_auth_header(self.pmo)
        response = client.get("/dashboard/employee/my-updates", headers=headers)
        assert response.status_code == 403

class TestPMODailyUpdateEndpoints:
    """Test PMO endpoints for viewing employee updates"""
    
    def setup_method(self):
        """Setup test data"""
        self.db = SessionLocal()
        
        # Create test users
        self.executor = create_test_user(self.db, role="executor")
        self.pmo = create_test_user(self.db, role="reviewer")
        self.other_pmo = create_test_user(self.db, role="reviewer")
        
        # Create test EO and task
        self.eo = create_test_eo(self.db)
        self.task = create_test_task(self.db, self.eo.id, self.executor.id)
        
        # Create PMO assignment (only for self.pmo, not other_pmo)
        self.pmo_assignment = create_pmo_assignment(self.db, self.eo.id, self.pmo.id)
        
        # Create test updates
        self.update1 = create_test_task_update(self.db, self.eo.id, self.task.id, self.executor.id)
        self.update2 = create_test_task_update(self.db, self.eo.id, self.task.id, self.executor.id)
        
    def teardown_method(self):
        """Clean up test data"""
        self.db.query(TaskUpdate).delete()
        self.db.query(EOPMOAssignment).delete()
        self.db.query(Task).delete()
        self.db.query(ExecutiveOrder).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_get_pmo_daily_updates_success(self):
        """Test PMO retrieving updates from assigned EOs"""
        headers = get_auth_header(self.pmo)
        response = client.get("/dashboard/pmo/daily-updates", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["daily_updates"]) == 2
        
        # Check structure of returned updates
        update_data = data["data"]["daily_updates"][0]
        assert "id" in update_data
        assert "task_id" in update_data
        assert "user_id" in update_data
        assert "update_text" in update_data
        assert "progress_pct" in update_data
        assert "hours_spent" in update_data
        assert "status_note" in update_data
        assert "blockers" in update_data
        assert "risks" in update_data
        assert "next_actions" in update_data
        assert "created_at" in update_data
        assert "employee" in update_data
        assert "task" in update_data

    def test_get_pmo_daily_updates_filtered_by_assignment(self):
        """Test that PMO only sees updates from their assigned EOs"""
        headers = get_auth_header(self.other_pmo)  # PMO not assigned to this EO
        response = client.get("/dashboard/pmo/daily-updates", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["daily_updates"]) == 0  # Should see no updates

    def test_get_pmo_daily_updates_unauthorized(self):
        """Test unauthorized access to PMO updates"""
        response = client.get("/dashboard/pmo/daily-updates")
        assert response.status_code == 403  # FastAPI returns 403 when no auth header provided

    def test_get_pmo_daily_updates_wrong_role(self):
        """Test executor trying to access PMO updates"""
        headers = get_auth_header(self.executor)
        response = client.get("/dashboard/pmo/daily-updates", headers=headers)
        assert response.status_code == 403
        assert "PMO role required" in response.json()["detail"]

    def test_pagination_and_limits(self):
        """Test pagination parameters"""
        headers = get_auth_header(self.pmo)
        
        # Test with limit
        response = client.get("/dashboard/pmo/daily-updates?limit=1", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["daily_updates"]) == 1
        assert data["data"]["pagination"]["limit"] == 1
        assert data["data"]["pagination"]["total"] == 2
        
        # Test with offset
        response = client.get("/dashboard/pmo/daily-updates?offset=1&limit=1", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["daily_updates"]) == 1
        assert data["data"]["pagination"]["offset"] == 1

def test_field_mapping_consistency():
    """Test that field mappings are consistent across all endpoints"""
    db = SessionLocal()
    
    try:
        # Setup test data
        executor = create_test_user(db, role="executor")
        pmo = create_test_user(db, role="reviewer")
        eo = create_test_eo(db)
        task = create_test_task(db, eo.id, executor.id)
        create_pmo_assignment(db, eo.id, pmo.id)
        
        # Create update via POST endpoint
        headers = get_auth_header(executor)
        update_data = {
            "task_id": str(task.id),
            "update_text": "Consistency test",
            "progress_pct": 80,
            "hours_spent": 5.5,
            "status_note": "completed",
            "blockers": {"blocker": "Test blocker"},
            "risks": {"risk": "Test risk"}
        }
        
        post_response = client.post("/dashboard/employee/daily-update", json=update_data, headers=headers)
        assert post_response.status_code == 201
        created_update = post_response.json()["data"]
        
        # Retrieve via employee endpoint
        get_response = client.get("/dashboard/employee/my-updates", headers=headers)
        assert get_response.status_code == 200
        employee_updates = get_response.json()["data"]["updates"]
        employee_update = employee_updates[0]
        
        # Retrieve via PMO endpoint
        pmo_headers = get_auth_header(pmo)
        pmo_response = client.get("/dashboard/pmo/daily-updates", headers=pmo_headers)
        assert pmo_response.status_code == 200
        pmo_updates = pmo_response.json()["data"]["daily_updates"]
        pmo_update = pmo_updates[0]
        
        # Verify field consistency
        assert created_update["update_text"] == employee_update["update_text"] == pmo_update["update_text"]
        assert created_update["progress_pct"] == employee_update["progress_pct"] == pmo_update["progress_pct"]
        assert created_update["hours_spent"] == employee_update["hours_spent"] == pmo_update["hours_spent"]
        assert created_update["status_note"] == employee_update["status_note"] == pmo_update["status_note"] == "Completed"
        assert created_update["blockers"] == employee_update["blockers"] == pmo_update["blockers"] == ["Test blocker"]
        assert created_update["risks"] == employee_update["risks"] == pmo_update["risks"] == ["Test risk"]
        assert created_update["next_actions"] == employee_update["next_actions"] == pmo_update["next_actions"] == []
        
    finally:
        # Clean up
        db.query(TaskUpdate).delete()
        db.query(EOPMOAssignment).delete()
        db.query(Task).delete()
        db.query(ExecutiveOrder).delete()
        db.query(User).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
