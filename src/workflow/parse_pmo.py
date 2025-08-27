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
    
    print(f"DEBUG: Parsing PMO email, length: {len(text)}")
    
    # Try regex parsing first (faster)
    regex_result = parse_pmo_with_regex(text)
    if regex_result and regex_result.get("intent") != "UNKNOWN":
        print(f"DEBUG: Regex parsing successful: {regex_result}")
        return regex_result
    
    print("DEBUG: Regex parsing failed, trying LLM")
    # Fall back to LLM parsing
    llm_result = parse_pmo_with_llm(text)
    print(f"DEBUG: LLM parsing result: {llm_result}")
    return llm_result

def parse_pmo_with_llm(body_text: str) -> Dict:
    """
    Use LLM to parse PMO email response.
    """
    try:
        from src.app.langchain_utils import _build_llm
        from src.app.prompts import PMO_PARSING_SYSTEM_PROMPT, PMO_PARSING_HUMAN_TEMPLATE
        
        llm = _build_llm()
        
        # Build prompt
        prompt = f"{PMO_PARSING_SYSTEM_PROMPT}\n\n{PMO_PARSING_HUMAN_TEMPLATE.format(email_body=body_text)}"
        
        # Call LLM
        response = llm.invoke(prompt)
        
        # Parse JSON response - handle markdown code blocks
        import json
        import re
        
        content = response.content.strip()
        print(f"DEBUG: LLM raw response: {content}")
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
            print(f"DEBUG: Extracted JSON from markdown: {json_content}")
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_content = json_match.group(0)
                print(f"DEBUG: Found JSON object directly: {json_content}")
            else:
                print(f"DEBUG: No JSON found in LLM response")
                return {"intent": "UNKNOWN", "approve_task_ids": [], "reject_task_ids": [], "remarks": None, "per_task_remarks": {}}
        
        try:
            result = json.loads(json_content)
            print(f"DEBUG: Successfully parsed JSON: {result}")
            return result
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON parsing failed: {e}")
            print(f"DEBUG: JSON content: {json_content}")
            return {"intent": "UNKNOWN", "approve_task_ids": [], "reject_task_ids": [], "remarks": None, "per_task_remarks": {}}
            
    except Exception as e:
        print(f"DEBUG: LLM parsing failed: {e}")
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
    print(f"DEBUG: parse_pmo_table_format called, body length: {len(body_text)}")
    
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
            print(f"DEBUG: Table pattern {i} matched, separator: '{separator}'")
            break
    
    if not table_found:
        print("DEBUG: No table pattern found")
        return None
    
    # Extract table rows - be more flexible with line detection
    lines = body_text.split('\n')
    table_started = False
    table_rows = []
    
    print(f"DEBUG: Processing {len(lines)} lines")
    
    for line in lines:
        line = line.strip()
        if re.search(table_patterns[0] if separator == '|' else table_patterns[1], line, re.IGNORECASE):
            table_started = True
            print(f"DEBUG: Table header found: {line}")
            continue
        elif table_started and separator in line and not line.startswith('---'):
            # This is a data row
            table_rows.append(line)
            print(f"DEBUG: Added table row: {line}")
        elif table_started and not line:
            # Empty line might end the table
            print("DEBUG: Empty line, ending table")
            break
    
    print(f"DEBUG: Found {len(table_rows)} table rows")
    
    if not table_rows:
        print("DEBUG: No table rows found")
        return None
    
    # Parse table rows
    approve_ids = []
    reject_ids = []
    per_task_remarks = {}
    
    for row in table_rows:
        parts = [part.strip() for part in row.split(separator)]
        print(f"DEBUG: Row '{row}' split into {len(parts)} parts: {parts}")
        if len(parts) >= 7:
            task_id = parts[0].strip()
            status = parts[5].strip().lower()
            remarks = parts[6].strip()
            
            print(f"DEBUG: task_id='{task_id}', status='{status}', remarks='{remarks}'")
            
            if task_id.isdigit():
                if status == 'approve':
                    approve_ids.append(task_id)
                    print(f"DEBUG: Added approve_id: {task_id}")
                elif status == 'reject':
                    reject_ids.append(task_id)
                    print(f"DEBUG: Added reject_id: {task_id}")
                
                if remarks and remarks not in ['[Fill Here]', '']:
                    per_task_remarks[task_id] = remarks
                    print(f"DEBUG: Added remarks for {task_id}: {remarks}")
            else:
                print(f"DEBUG: task_id '{task_id}' is not a digit")
        else:
            print(f"DEBUG: Row has only {len(parts)} parts, need at least 7")
    
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
    
    print(f"DEBUG: Table parsing result: {result}")
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
    """Extract EO UUID from subject line like [EO:<uuid>]."""
    if not subject:
        return None
    UUID_RE = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    SUBJECT_EO_ID = re.compile(r"\[EO:(?P<eo_id>" + UUID_RE + r")\]", re.IGNORECASE)
    match = SUBJECT_EO_ID.search(subject)
    return match.group("eo_id") if match else None 