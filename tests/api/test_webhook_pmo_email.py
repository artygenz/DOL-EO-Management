from fastapi.testclient import TestClient
from unittest.mock import patch
from src.main import app

client = TestClient(app)


def test_webhook_pmo_email_enqueues_and_logs():
    payload = {
        "message_id": "mid-123",
        "subject": "[PMO ACTION][EO:00000000-0000-0000-0000-000000000000] Review",
        "sender": "pmo@example.gov",
        "recipients": ["workflow@example.gov"],
        "body_text": "approve all",
        "related_eo_id": None,
    }
    with patch("src.workflow.tasks.process_pmo_response.delay") as mock_delay, \
         patch("src.workflow.repository.save_email_log") as mock_log:
        resp = client.post("/webhook/pmo_email", json=payload)
        assert resp.status_code == 202
        mock_delay.assert_called_once()
        mock_log.assert_called_once() 