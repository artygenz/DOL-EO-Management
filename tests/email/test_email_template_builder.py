from types import SimpleNamespace
from src.email.email_template_builder import EmailTemplateBuilder

def test_pmo_review_email_contains_eo_identifiers():
    eo = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000000",
        title="Test EO",
        message_id="mid-42",
        received_at=None,
        source_email="origin@example.gov",
        description="Body",
    )
    built = EmailTemplateBuilder.build_pmo_review(eo, tasks=[])
    assert f"[EO:{eo.id}]" in built.subject
    assert built.headers.get("X-EO-ID") == eo.id
    assert built.headers.get("X-EO-Message-ID") == eo.message_id 