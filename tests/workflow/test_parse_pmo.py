import uuid
from src.workflow.parse_pmo import parse_pmo_email, extract_eo_id_from_subject


def test_approve_all_detection():
    body = "Please proceed. Fully approved."
    parsed = parse_pmo_email(body)
    assert parsed["intent"] == "APPROVE_ALL"
    assert parsed["approve_task_ids"] == []
    assert parsed["reject_task_ids"] == []


def test_reject_all_with_global_remarks():
    body = "Rejected all.\nRemarks: Reduce scope across the board"
    parsed = parse_pmo_email(body)
    assert parsed["intent"] == "REJECT_ALL"
    assert parsed["remarks"] == "Reduce scope across the board"


def test_partial_with_command_lines_per_task_remarks():
    t1 = str(uuid.uuid4())
    t2 = str(uuid.uuid4())
    body = f"""
    #task_approve TASK_ID={t1} REMARKS=Looks good
    #task_reject  TASK_ID={t2} REMARKS=Needs legal review
    """.strip()
    parsed = parse_pmo_email(body)
    assert parsed["intent"] == "APPROVE_SOME"
    assert parsed["approve_task_ids"] == [t1]
    assert parsed["reject_task_ids"] == [t2]
    assert parsed["per_task_remarks"][t1] == "Looks good"
    assert parsed["per_task_remarks"][t2] == "Needs legal review"


def test_extract_eo_id_from_subject():
    eo_id = str(uuid.uuid4())
    subj = f"[PMO ACTION][EO:{eo_id}] Something"
    assert extract_eo_id_from_subject(subj) == eo_id 