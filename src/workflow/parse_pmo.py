import re
from typing import Dict, List, Tuple

UUID_RE = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

_APPROVE_ALL_PATTERNS = [
    r"\b(approve|approved)\s+all\b",
    r"\b(full(?:y)?\s+approved?)\b",
]
_REJECT_ALL_PATTERNS = [
    r"\b(reject|rejected)\s+all\b",
    r"\b(full(?:y)?\s+rejected?)\b",
]

# Command-style lines we generate in outbound email
CMD_APPROVE = re.compile(r"#task_approve\s+TASK_ID=(?P<id>" + UUID_RE + r")(?:\s+REMARKS=(?P<remarks>.*))?", re.IGNORECASE)
CMD_REJECT = re.compile(r"#task_reject\s+TASK_ID=(?P<id>" + UUID_RE + r")(?:\s+REMARKS=(?P<remarks>.*))?", re.IGNORECASE)

# Natural style: "approve <uuid> ...", "reject <uuid> ..."
NAT_APPROVE = re.compile(r"\bapprove\s+(?P<id>" + UUID_RE + r")(?:[\s,:-]+(?P<remarks>[^\n\r]*))?", re.IGNORECASE)
NAT_REJECT = re.compile(r"\breject\s+(?P<id>" + UUID_RE + r")(?:[\s,:-]+(?P<remarks>[^\n\r]*))?", re.IGNORECASE)

SUBJECT_EO_ID = re.compile(r"\[EO:(?P<eo_id>" + UUID_RE + r")\]", re.IGNORECASE)


def _match_any(text: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            return True
    return False


def parse_pmo_email(body_text: str) -> Dict:
    """
    Returns a dict with keys:
      intent: APPROVE_ALL | APPROVE_SOME | REJECT_ALL
      approve_task_ids: list[str]
      reject_task_ids: list[str]
      remarks: str | None (global remarks)
      per_task_remarks: dict[str, str]
    """
    text = body_text or ""

    approve_ids: List[str] = []
    reject_ids: List[str] = []
    per_task_remarks: Dict[str, str] = {}

    # First pass: command-style lines
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = CMD_APPROVE.search(line)
        if m:
            tid = m.group("id")
            approve_ids.append(tid)
            rem = (m.group("remarks") or "").strip()
            if rem:
                per_task_remarks[tid] = rem
            continue
        m = CMD_REJECT.search(line)
        if m:
            tid = m.group("id")
            reject_ids.append(tid)
            rem = (m.group("remarks") or "").strip()
            if rem:
                per_task_remarks[tid] = rem
            continue

    # Second pass: natural phrases
    for m in NAT_APPROVE.finditer(text):
        tid = m.group("id")
        if tid not in approve_ids and tid not in reject_ids:
            approve_ids.append(tid)
            rem = (m.group("remarks") or "").strip()
            if rem:
                per_task_remarks[tid] = rem
    for m in NAT_REJECT.finditer(text):
        tid = m.group("id")
        if tid not in reject_ids and tid not in approve_ids:
            reject_ids.append(tid)
            rem = (m.group("remarks") or "").strip()
            if rem:
                per_task_remarks[tid] = rem

    # Global remarks heuristic: any free text after a line like "Remarks:" or at bottom
    global_remarks = None
    m = re.search(r"\bRemarks?\s*:\s*(.+)$", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        global_remarks = m.group(1).strip()

    # Intent decision
    if _match_any(text, _APPROVE_ALL_PATTERNS) and not reject_ids:
        intent = "APPROVE_ALL"
    elif _match_any(text, _REJECT_ALL_PATTERNS) and not approve_ids:
        intent = "REJECT_ALL"
    elif approve_ids or reject_ids:
        intent = "APPROVE_SOME"
    else:
        # Fallback: simple keyword sniff
        if re.search(r"\bapprove\b", text, flags=re.IGNORECASE):
            intent = "APPROVE_SOME"
        elif re.search(r"\breject\b", text, flags=re.IGNORECASE):
            intent = "REJECT_ALL"
        else:
            # Default conservatively to partial
            intent = "APPROVE_SOME"

    return {
        "intent": intent,
        "approve_task_ids": approve_ids,
        "reject_task_ids": reject_ids,
        "remarks": global_remarks,
        "per_task_remarks": per_task_remarks,
    }


def extract_eo_id_from_subject(subject: str | None) -> str | None:
    if not subject:
        return None
    m = SUBJECT_EO_ID.search(subject)
    return m.group("eo_id") if m else None 