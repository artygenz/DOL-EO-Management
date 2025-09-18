"""
Test for PMO rejection with assignee change functionality.
This test verifies that when PMO rejects a task and provides remarks to change the assignee,
the rewiring process correctly updates the assignee based on the new category_dept.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.workflow.tasks import handle_rejected_tasks
from src.workflow.repository import update_tasks_with_improved_data
from src.db.session import SessionLocal
from src.models.task import Task
from src.models.executive_order import ExecutiveOrder
from src.models.user import User
import uuid
import datetime

def test_assignee_change_workflow():
    """
    Test the complete workflow for PMO rejection with assignee change.
    This tests the integration between:
    1. LLM rewiring (mocked)
    2. assign_tasks() function call
    3. Repository update with new assignee
    """
    # Setup test data
    eo_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    rejected_ids = [task_id]
    
    # Mock the database and external dependencies
    with patch('src.workflow.repository.get_executive_order') as mock_get_eo, \
         patch('src.workflow.repository.get_tasks_by_ids') as mock_get_tasks, \
         patch('src.db.users.build_roles_with_members_text') as mock_roles, \
         patch('src.app.rewire_tasks.rewire_tasks_with_remarks') as mock_rewire, \
         patch('src.app.extract_directives.assign_tasks') as mock_assign, \
         patch('src.workflow.repository.update_tasks_with_improved_data') as mock_update, \
         patch('src.workflow.tasks.send_improved_tasks_to_pmo.delay') as mock_send:
        
        # Mock EO
        mock_eo = MagicMock()
        mock_eo.id = eo_id
        mock_eo.description = "Test EO for assignee change"
        mock_get_eo.return_value = mock_eo
        
        # Mock rejected task
        mock_task = MagicMock()
        mock_task.id = uuid.UUID(task_id)
        mock_task.title = "Original Task"
        mock_task.description = "Original description"
        mock_task.category = "Original Department"
        mock_task.due_date = None
        mock_task.created_at = datetime.datetime.now()
        mock_get_tasks.return_value = [mock_task]
        
        # Mock roles text
        mock_roles.return_value = """
        Treasury Department
        - Alice Smith
        - Bob Jones
        
        DOL Department  
        - Carol Wilson
        - David Brown
        """
        
        # Mock LLM rewiring result (with new category_dept)
        mock_rewire.return_value = {
            "tasks": [
                {
                    "id": 1,
                    "title": "Improved Task",
                    "description": "Improved description with assignee change",
                    "category_dept": "DOL Department",  # Changed from "Original Department"
                    "assignee": "",  # LLM leaves this empty
                    "status": "Pending",
                    "due_date": "TBD",
                    "created_at": "2024-01-01T00:00:00Z",
                    "remarks": "Task improved per PMO feedback"
                }
            ],
            "summary": "Changed assignee department from Treasury to DOL per PMO request"
        }
        
        # Mock assign_tasks result (assigns based on new category_dept)
        mock_assign.return_value = {
            "tasks": [
                {
                    "id": 1,
                    "title": "Improved Task", 
                    "description": "Improved description with assignee change",
                    "category_dept": "DOL Department",
                    "assignee": "Carol Wilson",  # assign_tasks fills this based on category_dept
                    "status": "Pending",
                    "due_date": "TBD",
                    "created_at": "2024-01-01T00:00:00Z",
                    "remarks": "Task improved per PMO feedback"
                }
            ],
            "summary": "Changed assignee department from Treasury to DOL per PMO request"
        }
        
        # Mock successful database update
        mock_update.return_value = 1
        
        # Run the function
        result = handle_rejected_tasks(
            eo_id=eo_id,
            rejected_ids=rejected_ids,
            global_remarks="Please change assignee to DOL Department",
            per_task_remarks={task_id: "Move this task to DOL team"}
        )
        
        # Verify the workflow executed correctly
        assert result["eo_id"] == eo_id
        assert result["rejected"] == 1
        assert result["rewired"] is True
        
        # Verify LLM rewiring was called with correct parameters
        mock_rewire.assert_called_once()
        rewire_call = mock_rewire.call_args
        assert "Please change assignee to DOL Department" in rewire_call[1]["remarks"]
        assert rewire_call[1]["tasks"]["tasks"][0]["category_dept"] == "Original Department"
        
        # Verify assign_tasks was called after LLM rewiring
        mock_assign.assert_called_once()
        assign_call = mock_assign.call_args
        # The assign_tasks should receive the LLM result
        assert assign_call[0][0]["tasks"][0]["category_dept"] == "DOL Department"
        assert assign_call[0][0]["tasks"][0]["assignee"] == ""  # Empty from LLM
        
        # Verify database update was called with assigned task
        mock_update.assert_called_once()
        update_call = mock_update.call_args[0][0]  # task_updates dict
        task_data = list(update_call.values())[0]
        assert task_data["assignee"] == "Carol Wilson"  # Assigned by assign_tasks
        assert task_data["category_dept"] == "DOL Department"
        
        # Verify follow-up email was queued
        mock_send.assert_called_once()

def test_repository_assignee_update():
    """
    Test that the repository correctly handles assignee updates from rewired tasks.
    """
    # Mock data
    task_id = str(uuid.uuid4())
    improved_data = {
        "title": "Updated Task",
        "description": "Updated description", 
        "category_dept": "DOL Department",
        "assignee": "Carol Wilson",
        "remarks": "Task updated per PMO feedback"
    }
    
    with patch('src.workflow.repository.SessionLocal') as mock_session, \
         patch('src.workflow.repository.resolve_assignee_name_to_id') as mock_resolve:
        
        # Mock database session and task
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        
        mock_task = MagicMock()
        mock_task.title = "Original Task"
        mock_task.description = "Original description"
        mock_task.category = "Original Department"
        mock_task.assignee_id = uuid.uuid4()  # Original assignee
        mock_db.get.return_value = mock_task
        
        # Mock assignee resolution
        new_assignee_id = uuid.uuid4()
        mock_resolve.return_value = new_assignee_id
        
        # Call the function
        result = update_tasks_with_improved_data({task_id: improved_data})
        
        # Verify task was updated
        assert result == 1
        assert mock_task.title == "Updated Task"
        assert mock_task.description == "Updated description"
        assert mock_task.category == "DOL Department"
        assert mock_task.assignee_id == new_assignee_id  # Updated assignee
        assert mock_task.status == "Pending PMO approval"
        assert mock_task.remarks == "Task updated per PMO feedback"
        
        # Verify assignee resolution was called
        mock_resolve.assert_called_once_with("Carol Wilson")
        
        # Verify database commit
        mock_db.commit.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
