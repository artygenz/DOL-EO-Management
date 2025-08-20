# src/services/email_template_builder.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import date, datetime, timezone
import csv, io, json, html

@dataclass
class BuiltEmail:
    subject: str
    body_text: str
    body_html: str
    attachments: List[Tuple[str, str, bytes]]  # (filename, content_type, data)
    headers: Dict[str, str]

class EmailTemplateBuilder:
    """
    Pure template builder (no I/O). Takes EO + tasks and returns 
    subject, text, html, and attachments (CSV + JSON).
    """

    @staticmethod
    def build_pmo_review(eo, tasks: List[dict | object]) -> BuiltEmail:
        rows = EmailTemplateBuilder._rows_from_tasks(tasks)
        subject = f"[PMO ACTION][EO:{eo.id}] {eo.title or 'Executive Order'} — {len(rows)} pending tasks"
        body_text, body_html = EmailTemplateBuilder._build_email_bodies(eo, rows)

        csv_bytes = EmailTemplateBuilder._build_csv(rows)
        json_bytes = EmailTemplateBuilder._build_json(rows)


        eo_txt = EmailTemplateBuilder._build_eo_text_attachment(eo)
        attachments = [
            (f"eo_{eo.id}_tasks_pending.csv", "text/csv", csv_bytes),
            (f"eo_{eo.id}_tasks_pending.json", "application/json", json_bytes),
            (f"eo_{eo.id}.txt", "text/plain", eo_txt.encode("utf-8")),  # 👈 EO itself
        ]

       

        headers = {
            "X-EO-Message-ID": eo.message_id or "",
            "X-EO-ID": str(eo.id),
            "X-DOL-Intent": "#task_approve/#task_reject",
        }

        return BuiltEmail(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            headers=headers,
        )

    # ---------- helpers (pure) ----------

    @staticmethod
    def _fmt_dt(dt) -> str:
        if isinstance(dt, (datetime, date)):
            # Always serialize as ISO 8601
            try:
                return dt.isoformat()
            except Exception:
                return str(dt)
        return str(dt) if dt is not None else "—"

    @staticmethod
    def _to_primitive(v):
        """Coerce common non-JSON types to JSON-safe primitives."""
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        # add more custom coercions if needed
        return v

    @staticmethod
    def _rows_from_tasks(tasks: List[dict | object]) -> List[Dict]:
        rows: List[Dict] = []
        for t in tasks or []:
            # normalize to dict
            if hasattr(t, "model_dump"):
                td = t.model_dump()                         # Pydantic → dict
            elif isinstance(t, dict):
                td = t
            else:
                td = getattr(t, "__dict__", {}) or {}

            due = td.get("due_date")
            rows.append({
                "id": str(td.get("id") or td.get("task_id") or td.get("uuid") or td.get("external_id", "")),
                "title": td.get("title") or "",
                "owner": td.get("owner") or "",
                "assignee": td.get("assignee") or "",
                "due_date": EmailTemplateBuilder._fmt_dt(due) if due else "",
                "status": td.get("status") or "pending",
                "description": td.get("description") or "",
            })
        return rows

    @staticmethod
    def _build_quick_lines(rows: List[Dict]) -> List[str]:
        lines = []
        for r in rows:
            tid = r.get("id")
            if not tid:
                continue
            lines.append(f"#task_approve TASK_ID={tid} REMARKS=")
            lines.append(f"#task_reject  TASK_ID={tid} REMARKS=")
        return lines

    @staticmethod
    def _build_csv(rows: List[Dict]) -> bytes:
        # csv module will call str() on values; our rows already have strings for dates
        buf = io.StringIO()
        fieldnames = ["id", "title", "owner", "assignee", "due_date", "status", "description"]
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue().encode("utf-8")

    @staticmethod
    def _build_json(rows: List[Dict]) -> bytes:
        # ensure anything unexpected (if it sneaks in) is coerced via default
        return json.dumps(rows, indent=2, default=EmailTemplateBuilder._to_primitive).encode("utf-8")

    @staticmethod
    def _build_html_table(rows: List[Dict]) -> str:
        head = (
            "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
            "<thead><tr>"
            "<th>Task ID</th><th>Title</th><th>Owner</th><th>Assignee</th><th>Due</th><th>Status</th>"
            "</tr></thead><tbody>"
        )
        body = []
        for r in rows:
            body.append(
                "<tr>"
                f"<td>{html.escape(r.get('id') or '—')}</td>"
                f"<td>{html.escape((r.get('title') or '')[:120])}</td>"
                f"<td>{html.escape(r.get('owner') or '—')}</td>"
                f"<td>{html.escape(r.get('assignee') or '—')}</td>"
                f"<td>{html.escape(str(r.get('due_date') or '—'))}</td>"
                f"<td>{html.escape(r.get('status') or 'pending')}</td>"
                "</tr>"
            )
        tail = "</tbody></table>"
        return head + "".join(body) + tail

    @staticmethod
    def _build_email_bodies(eo, rows: List[Dict]) -> tuple[str, str]:
        # TEXT
        lines = [
            f"Subject EO: {eo.title or '(no subject)'}",
            f"EO ID: {eo.id}",
            f"EO Message-ID: {eo.message_id}",
            f"Received: {EmailTemplateBuilder._fmt_dt(eo.received_at)}",
            "",
            "Below are the PENDING tasks for PMO action.",
            "Approve/Reject by replying and including one line per decision:",
            "  #task_approve TASK_ID=<uuid> REMARKS=<optional>",
            "  #task_reject  TASK_ID=<uuid> REMARKS=<optional>",
            ""
        ]
        for idx, r in enumerate(rows[:10], start=1):
            desc = r.get("description") or ""
            desc_skim = (desc[:120] + "…") if len(desc) > 120 else desc
            lines += [
                f"{idx}. {r.get('title') or '(untitled)'}",
                f"    Task ID: {r.get('id') or '—'} | Owner: {r.get('owner') or '—'} | Assignee: {r.get('assignee') or '—'} | Due: {r.get('due_date') or '—'}",
                f"    {desc_skim}",
                ""
            ]
        quick = EmailTemplateBuilder._build_quick_lines(rows)
        lines += ["---", "Quick copy lines:"] + quick
        body_text = "\n".join(lines)

        # HTML
        body_html = (
            f"<p><strong>Subject EO:</strong> {html.escape(eo.title or '(no subject)')}<br>"
            f"<strong>EO ID:</strong> {html.escape(str(eo.id))}<br>"
            f"<strong>EO Message-ID:</strong> {html.escape(eo.message_id or '')}<br>"
            f"<strong>Received:</strong> {html.escape(EmailTemplateBuilder._fmt_dt(eo.received_at))}</p>"
            "<p>Below are the <strong>PENDING</strong> tasks for PMO action.</p>"
            "<p>Approve/Reject by replying and including one line per decision:<br>"
            "<code>#task_approve TASK_ID=&lt;uuid&gt; REMARKS=&lt;optional&gt;</code><br>"
            "<code>#task_reject&nbsp;&nbsp;TASK_ID=&lt;uuid&gt; REMARKS=&lt;optional&gt;</code></p>"
            + EmailTemplateBuilder._build_html_table(rows) +
            "<p><strong>Quick copy lines:</strong><br>"
            "<pre style='white-space:pre-wrap;'>"
            + html.escape("\n".join(quick))
            + "</pre></p>"
        )
        return body_text, body_html
    

    # --- NEW helper ---
    @staticmethod
    def _build_eo_text_attachment(eo) -> str:
        """
        Produce a human-readable text rendition of the EO,
        including title, source meta, and full description.
        """
        title = getattr(eo, "title", "") or "(no subject)"
        msgid = getattr(eo, "message_id", "") or "N/A"
        received = EmailTemplateBuilder._fmt_dt(getattr(eo, "received_at", None))
        sender = getattr(eo, "source_email", "") or "N/A"
        desc = getattr(eo, "description", "") or "(no description)"

        return (
            f"Executive Order\n"
            f"Title: {title}\n"
            f"EO ID: {eo.id}\n"
            f"Message-ID: {msgid}\n"
            f"Received: {received}\n"
            f"Sender: {sender}\n"
            f"\n"
            f"=== EO BODY START ===\n"
            f"{desc}\n"
            f"=== EO BODY END ===\n")