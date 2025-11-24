import re
from typing import Dict

def parse_pmo_email(body_text: str) -> Dict:
    """
    Parse PMO email response to extract task decisions.
    
    Uses regex as primary method, falls back to LLM parsing.
    """
    text = body_text or ""
    
    # Handle escaped characters
    text = text.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
    
    # Parse PMO email
    
    # Try regex parsing first (faster)
    regex_result = parse_pmo_with_regex(text)
    if regex_result and regex_result.get("intent") != "UNKNOWN":
        return regex_result
    # Fall back to LLM parsing
    llm_result = parse_pmo_with_llm(text)
    # LLM parsing completed
    return llm_result

def parse_pmo_with_llm(body_text: str) -> Dict:
    """
    Use LLM to parse PMO email response.
    """
    try:
        from src.ai.langchain_utils import _build_llm
        from src.ai.prompts import PMO_PARSING_SYSTEM_PROMPT, PMO_PARSING_HUMAN_TEMPLATE
        
        llm = _build_llm()
        
        # Build prompt
        prompt = f"{PMO_PARSING_SYSTEM_PROMPT}\n\n{PMO_PARSING_HUMAN_TEMPLATE.format(email_body=body_text)}"
        
        # Call LLM
        response = llm.invoke(prompt)
        
        # Parse JSON response - handle markdown code blocks
        import json
        import re
        
        content = response.content.strip()
        # LLM response received
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
            # Extracted JSON from markdown
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_content = json_match.group(0)
                # Found JSON object directly
            else:
                # No JSON found in LLM response
                return {"intent": "UNKNOWN", "approve_task_ids": [], "reject_task_ids": [], "remarks": None, "per_task_remarks": {}}
        
        try:
            result = json.loads(json_content)
            # Successfully parsed JSON
            return result
        except json.JSONDecodeError as e:
            # JSON parsing failed
            return {"intent": "UNKNOWN", "approve_task_ids": [], "reject_task_ids": [], "remarks": None, "per_task_remarks": {}}
            
    except Exception as e:
        # LLM parsing failed
        return {"intent": "UNKNOWN", "approve_task_ids": [], "reject_task_ids": [], "remarks": None, "per_task_remarks": {}}

def parse_pmo_with_regex(body_text: str) -> Dict:
    """
    Parse PMO response using regex (fallback method).
    """
    # Try new table format first
    table_result = parse_pmo_table_format(body_text)
    if table_result:
        return table_result
    
    # Fall back to old command format
    return parse_pmo_command_format(body_text)

def parse_pmo_table_format(body_text: str) -> Dict:
    """
    Parse PMO response in table format with Status and Remarks columns.
    Supports both tab-separated and pipe-separated formats.
    """
    # Parse PMO table format
    
    # Look for table pattern (both tab and pipe formats)
    table_patterns = [
        r'Task ID\s*\|\s*Title\s*\|\s*Owner\s*\|\s*Assignee\s*\|\s*Due\s*\|\s*Status\s*\|\s*Remarks',
        r'Task ID\s+Title\s+Owner\s+Assignee\s+Due\s+Status\s+Remarks'
    ]
    
    table_found = False
    separator = None
    
    for i, pattern in enumerate(table_patterns):
        if re.search(pattern, body_text, re.IGNORECASE):
            table_found = True
            separator = '|' if i == 0 else '\t'  # First pattern is pipe, second is tab
            # Table pattern matched
            break
    
    if not table_found:
        # No table pattern found
        return None
    
    # Extract table rows - be more flexible with line detection
    lines = body_text.split('\n')
    table_started = False
    table_rows = []
    
    # Processing table lines
    
    for line in lines:
        line = line.strip()
        if re.search(table_patterns[0] if separator == '|' else table_patterns[1], line, re.IGNORECASE):
            table_started = True
            # Table header found
            continue
        elif table_started and separator in line and not line.startswith('---'):
            # This is a data row
            table_rows.append(line)
            # Added table row
        elif table_started and not line:
            # Empty line might end the table
            # Empty line, ending table
            break
    
    # Found table rows
    
    if not table_rows:
        # No table rows found
        return None
    
    # Parse table rows
    approve_ids = []
    reject_ids = []
    per_task_remarks = {}
    
    for row in table_rows:
        parts = [part.strip() for part in row.split(separator)]
        # Row split into parts
        if len(parts) >= 7:
            task_id = parts[0].strip()
            status = parts[5].strip().lower()
            remarks = parts[6].strip()
            
            # Processing task row
            
            if task_id.isdigit():
                if status == 'approve':
                    approve_ids.append(task_id)
                    # Added approve_id
                elif status == 'reject':
                    reject_ids.append(task_id)
                    # Added reject_id
                
                if remarks and remarks not in ['[Fill Here]', '']:
                    per_task_remarks[task_id] = remarks
                    # Added remarks
            else:
                # task_id is not a digit
                pass
        else:
            # Row has insufficient parts
            pass
    
    # Determine intent
    if approve_ids and reject_ids:
        intent = "APPROVE_SOME"
    elif approve_ids:
        intent = "APPROVE_ALL"
    elif reject_ids:
        intent = "REJECT_ALL"
    else:
        intent = "UNKNOWN"
    
    result = {
        "intent": intent,
        "approve_task_ids": approve_ids,
        "reject_task_ids": reject_ids,
        "remarks": None,  # No global remarks in table format
        "per_task_remarks": per_task_remarks,
    }
    
    # Table parsing completed
    return result

def parse_pmo_command_format(body_text: str) -> Dict:
    """
    Parse PMO response in old command format (#task_approve/#task_reject).
    """
    # Original parsing logic for backward compatibility
    UUID_RE = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    TASK_ID_RE = r"(" + UUID_RE + r"|\d+)"  # Match either UUID or simple numbers

    # Command-style lines we generate in outbound email
    CMD_APPROVE = re.compile(r"#task_approve\s+TASK_ID=(?P<id>" + TASK_ID_RE + r")(?:\s+REMARKS=(?P<remarks>.*))?", re.IGNORECASE)
    CMD_REJECT = re.compile(r"#task_reject\s+TASK_ID=(?P<id>" + TASK_ID_RE + r")(?:\s+REMARKS=(?P<remarks>.*))?", re.IGNORECASE)

    # Natural style: "approve <task_id> ...", "reject <task_id> ..."
    NAT_APPROVE = re.compile(r"\bapprove\s+(?P<id>" + TASK_ID_RE + r")(?:[\s,:-]+(?P<remarks>[^\n\r]*))?", re.IGNORECASE)
    NAT_REJECT = re.compile(r"\breject\s+(?P<id>" + TASK_ID_RE + r")(?:[\s,:-]+(?P<remarks>[^\n\r]*))?", re.IGNORECASE)

    # Global patterns
    APPROVE_ALL = re.compile(r"\bapprove\s+all\b", re.IGNORECASE)
    REJECT_ALL = re.compile(r"\breject\s+all\b", re.IGNORECASE)

    text = body_text or ""
    approve_ids = []
    reject_ids = []
    per_task_remarks = {}
    global_remarks = None

    # Check for approve/reject all
    if APPROVE_ALL.search(text):
        return {
            "intent": "APPROVE_ALL",
            "approve_task_ids": [],
            "reject_task_ids": [],
            "remarks": None,
            "per_task_remarks": {},
        }
    elif REJECT_ALL.search(text):
        # Try to extract global remarks
        global_match = re.search(r"GLOBAL REMARKS?:\s*(.*?)(?:\n\n|\n[A-Z]|$)", text, re.IGNORECASE | re.DOTALL)
        if global_match:
            global_remarks = global_match.group(1).strip()
        
        return {
            "intent": "REJECT_ALL",
            "approve_task_ids": [],
            "reject_task_ids": [],
            "remarks": global_remarks,
            "per_task_remarks": {},
        }

    # Parse individual task commands
    for match in CMD_APPROVE.finditer(text):
        task_id = match.group("id")
        remarks = match.group("remarks")
        approve_ids.append(task_id)
        if remarks:
            per_task_remarks[task_id] = remarks.strip()

    for match in CMD_REJECT.finditer(text):
        task_id = match.group("id")
        remarks = match.group("remarks")
        reject_ids.append(task_id)
        if remarks:
            per_task_remarks[task_id] = remarks.strip()

    for match in NAT_APPROVE.finditer(text):
        task_id = match.group("id")
        remarks = match.group("remarks")
        approve_ids.append(task_id)
        if remarks:
            per_task_remarks[task_id] = remarks.strip()

    for match in NAT_REJECT.finditer(text):
        task_id = match.group("id")
        remarks = match.group("remarks")
        reject_ids.append(task_id)
        if remarks:
            per_task_remarks[task_id] = remarks.strip()

    # Try to extract global remarks
    global_match = re.search(r"GLOBAL REMARKS?:\s*(.*?)(?:\n\n|\n[A-Z]|$)", text, re.IGNORECASE | re.DOTALL)
    if global_match:
        global_remarks = global_match.group(1).strip()

    # Determine intent
    if approve_ids and reject_ids:
        intent = "APPROVE_SOME"
    elif approve_ids:
        intent = "APPROVE_ALL"
    elif reject_ids:
        intent = "REJECT_ALL"
    else:
        intent = "UNKNOWN"

    return {
        "intent": intent,
        "approve_task_ids": approve_ids,
        "reject_task_ids": reject_ids,
        "remarks": global_remarks,
        "per_task_remarks": per_task_remarks,
    }


def extract_eo_id_from_subject(subject: str) -> str | None:
    """
    Extract EO UUID from subject line with various formats:
    - [EO:<uuid>]
    - [EO ID: <uuid>]
    - [EO ID:<uuid>]
    - EO ID: <uuid>
    - EO:<uuid>
    - Any UUID pattern in the subject
    """
    if not subject:
        return None
    
    UUID_RE = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    
    # Try various patterns in order of specificity
    patterns = [
        r"\[EO\s+ID:\s*(?P<eo_id>" + UUID_RE + r")\]",  # [EO ID: <uuid>]
        r"\[EO:\s*(?P<eo_id>" + UUID_RE + r")\]",        # [EO: <uuid>]
        r"EO\s+ID:\s*(?P<eo_id>" + UUID_RE + r")",       # EO ID: <uuid>
        r"EO:\s*(?P<eo_id>" + UUID_RE + r")",            # EO: <uuid>
        r"(?P<eo_id>" + UUID_RE + r")",                  # Any UUID in subject
    ]
    
    for pattern in patterns:
        match = re.search(pattern, subject, re.IGNORECASE)
        if match:
            return match.group("eo_id")
    
    return None 