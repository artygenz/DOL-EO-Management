# src/services/email_service.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, Dict, Tuple, List
from datetime import datetime, timezone
import os, json, pathlib

@dataclass
class Attachment:
    filename: str
    content_type: str
    data: bytes

class EmailService:
    """
    Dev 'console' email sender: writes payloads to OUTBOX_DIR.
    Swap with real SMTP/Graph provider later; keep same interface.
    """
    def __init__(self, out_dir: Optional[str] = None):
        self.out_dir = out_dir or os.getenv("OUTBOX_DIR", "/tmp/outbox")
        pathlib.Path(self.out_dir).mkdir(parents=True, exist_ok=True)

    def send(
        self,
        to: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[Iterable[Attachment]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        ts = int(datetime.now(timezone.utc).timestamp())
        mid = f"local-{ts}"
        base = pathlib.Path(self.out_dir) / f"{mid}"
        payload = {
            "message_id": mid,
            "to": to,
            "subject": subject,
            "headers": headers or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (base.with_suffix(".subject.txt")).write_text(subject, encoding="utf-8")
        (base.with_suffix(".body.txt")).write_text(body_text or "", encoding="utf-8")
        if body_html:
            (base.with_suffix(".body.html")).write_text(body_html, encoding="utf-8")
        (base.with_suffix(".json")).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        for a in (attachments or []):
            (pathlib.Path(self.out_dir) / f"{mid}__{a.filename}").write_bytes(a.data)
        return mid