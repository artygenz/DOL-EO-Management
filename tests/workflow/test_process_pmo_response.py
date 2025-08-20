from unittest.mock import patch
from src.workflow.tasks import process_pmo_response


def test_process_pmo_response_approve_all_routes_to_repo():
    email_payload = {
        "message_id": "mid-1",
        "subject": "[PMO ACTION][EO:00000000-0000-0000-0000-000000000000]",
        "sender": "pmo@example.gov",
        "recipients": ["workflow@example.gov"],
        "body_text": "Fully approved.",
        "related_eo_id": None,
    }
    with patch("src.workflow.tasks.extract_eo_id_from_subject", return_value="00000000-0000-0000-0000-000000000000"), \
         patch("src.workflow.tasks.parse_pmo_email", return_value={"intent": "APPROVE_ALL", "approve_task_ids": [], "reject_task_ids": [], "remarks": None, "per_task_remarks": {}}), \
         patch("src.workflow.repository.get_task_ids_by_eo", return_value=["11111111-1111-1111-1111-111111111111"]) as mock_ids, \
         patch("src.workflow.repository.update_tasks_status_and_remarks") as mock_update:
        result = process_pmo_response(email_payload)
        assert result["intent"] == "APPROVE_ALL"
        mock_ids.assert_called_once()
        mock_update.assert_called_once() 