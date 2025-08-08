"""
extract_directives.py
Author: Dev 2 (Joel) — AI/NLP – LangChain, prompt design, parsing logic

Purpose:
- Provide the Week 1 "EO directives extraction" pipeline that works purely with STRINGS.
- Hardcode demo EO text and roles inputs for local testing as instructed.
- Orchestrate LangChain (gpt-4.1) to extract a list of tasks (without assignees).
- Implement assign_tasks(...) to map category/dept to a role and randomly choose a member.

IMPORTANT IMPLEMENTATION RULES (per team lead):
1) This file does NOT care where strings originate (Gmail, S3, DB). It only consumes strings.
2) Primary function extract_directives(...) expects two string parameters: eo_pdf_text and roles_text.
3) The LLM MUST return assignee as an empty string (""). Actual assignment is performed here by assign_tasks(...).
4) Use GPT-4.1 via LangChain and centralized prompts from app/prompts.py.

Task schema (normalized for Python/Pydantic compatibility):
- We use 'category_dept' instead of 'category/dept' because slashes are awkward as keys.
- The returned top-level structure is {"tasks": [ Task, Task, ... ]}.

Task fields:
- id: int
- title: string
- description: string
- category_dept: string
- assignee: string
- status: string
- due_date: string (YYYY-MM-DD or "TBD")
- created_at: string (ISO 8601 Date-time)
"""

from __future__ import annotations

import json
import random
import re
from typing import Dict, List, Optional, Tuple

# Make 'app' importable whether running as a module or a script
if __package__ is None or __package__ == "":
    # Running as a script (e.g., 'python app/extract_directives.py'):
    # add the project root to sys.path so that 'import app.*' works.
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    # Preferred absolute import (works from project root)
    from app.langchain_utils import extract_tasks as lc_extract_tasks, TasksModel
except ImportError:
    # Fallback when running from inside the 'app' directory
    from langchain_utils import extract_tasks as lc_extract_tasks, TasksModel

# --------------------------------------------------------------------------------------
# HARDCODED DEMO INPUTS (for Week 1 testing only)
# In production, these will be passed in as strings from the calling layer (e.g., Gmail/S3/DB).
# --------------------------------------------------------------------------------------

EO_PDF_DEMO = """Presidential Actions
Protecting America’s Bank Account Against Fraud, Waste, and Abuse
Executive Orders
March 25, 2025
 By the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered:

Section 1. Purpose.  Promoting financial integrity and operational efficiency are critical responsibilities of the Federal Government.  The Federal Government processes trillions of dollars annually in disbursements to individuals, businesses, and organizations, and in receipts from taxes, fees, and other payments to finance daily and long-term Government operations.  These transactions flow into and out of the United States General Fund (General Fund), which might be thought of as America’s bank account.  In Fiscal Year 2024, $33.9 trillion flowed into the General Fund and $33.6 trillion flowed out of the account, including $5.87 trillion (less net interest) in benefits, grants, loans, vendor payments, and other disbursements. 

The Department of the Treasury is the largest financial payment manager of the Federal Government and is responsible for safeguarding the General Fund, but lacks sufficient controls to track transactions flowing through the General Fund to determine if they were proper.  To enforce sufficient controls and ensure accountability to American taxpayers, the Department of the Treasury requires financial information from executive departments and agencies (agencies) beyond what they currently provide.

Financial fraud threatens the integrity of Federal programs and undermines trust in Government.  Agencies’ past underinvestment in technology and longstanding challenges with access to accurate data has prevented them from more fully safeguarding taxpayer dollars against fraud and improper payments.  The Government Accountability Office estimates that the Federal Government loses between $233 and $521 billion annually to fraud.

In addition to being an efficient steward of taxpayer funds, the Federal Government, on behalf of the American public, must seek to ensure that financial information is accurate and that there is transparency with respect to how taxpayer dollars are being used.  Today, Federal funds are disbursed both by the Department of the Treasury and various Federal Government entities that are authorized to issue their own disbursements known as Non-Treasury Disbursing Offices (NTDOs).  In Fiscal Year 2024, NTDOs were estimated to be responsible for 181 million payments totaling over $1.5 trillion (approximately 22 percent of all Federal Government dollars disbursed). This fragmentation of disbursing authority, together with the proliferation of non-standard financial management systems across the Federal Government, leads to expensive, disjointed, and duplicative financial reporting, lack of financial traceability, complicated financial management, opacity, increased operational risks, and decreased ability of the Department of the Treasury to provide centralized oversight.

This order promotes financial integrity by enabling the Department of the Treasury to more easily conduct improper payment and fraud prevention screening prior to disbursing funds on behalf of agencies.  This order increases transparency and accountability by requiring agencies to provide the Department of the Treasury with the information needed to track transactions through the General Fund in greater detail.  This order also promotes operational efficiency by returning disbursing functions to the Department of the Treasury when possible and consolidating and standardizing core Federal financial systems.

Sec. 2.  Policy.  It is the policy of the United States to defend against financial fraud and improper payments, increase transparency and accountability around the Federal Government’s operations and financial condition, increase efficiency, reduce costs, and enhance the security of Federal payments.

Sec. 3.  Treasury Verification of Agency Payments Information.  (a)  The Secretary of the Treasury, in consultation with the Director of the Office of Management and Budget (OMB Director), shall update guidance and enhance systems to ensure that all payments made by the Department of the Treasury on behalf of agencies pursuant to the Secretary of the Treasury’s disbursing authority, including 31 U.S.C. 3321, are subject to pre-certification verification processes established by the Secretary of the Treasury and conducted by agencies and the Department of the Treasury for the purposes of defending against financial fraud and improper payments, to the greatest extent permitted by law.  Such guidance shall set forth guidelines for compliance with the Do Not Pay Working System as described in 31 U.S.C. 3351 et seq., and such other payment, account, and payee validation programs and services that the Secretary of the Treasury and the OMB Director determine to be beneficial for reducing financial fraud and improper payments.

(b)  In accordance with 31 U.S.C. 3354, the heads of all agencies shall cooperate with the Secretary of the Treasury to fulfill their obligations to determine payment or award eligibility through pre-certification and pre-award procedures, as determined by the Secretary of the Treasury, including pursuant to subsection (a) of this section and section 4 of this order to prevent fraud and improper payments.

(c)  The Secretary of the Treasury is directed to minimize administrative barriers to accessing and using data to prevent fraud and improper payments by exercising the authority in 31 U.S.C. 3351 et seq. to waive the requirements of 5 U.S.C. 552a(o), in consultation with the OMB Director, in any case or class of cases for computer matching activities, to the extent permissible by law.

(d)  Within 90 days of the date of this order, agency heads shall review and modify, as applicable, their relevant system of records notices under the Privacy Act of 1974 to include a “routine use” that allows for the disclosure of records to the Department of the Treasury for the purposes of identifying, preventing, or recouping fraud and improper payments, to the extent permissible by law. 

(e)  The Secretary of the Treasury, in consultation with the OMB Director, shall issue guidance to agency heads on the circumstances in which agency heads, to the extent permissible by law, may provide the Secretary of the Treasury with access to data necessary for the purposes of detecting and preventing fraud and improper payments, as well as data for payment information verification (and not, for example, data such as health records).

Sec. 4.  Implementation and Compliance of Payment Verification.  (a)  Agency heads, through designated agency officials (Certifying Officers or COs), who are responsible for verifying that disbursements made by the Federal Government are legal, proper, and correct, and for performing the duties in 31 U.S.C. 3528, shall comply with the disbursement requirements and instructions, including pre-certification requirements, published by the Secretary of the Treasury.

(b)  The Secretary of the Treasury shall consider, as appropriate, issuing instructions to agencies to enforce the following pre-certification criteria for disbursement requests submitted by COs (Vouchers) before they are certified for payment by the CO:

(i)     Funds are available at the time the obligation is incurred.  If an obligation is incurred when funds are not available, then the CO shall not certify the payment.

(ii)    The amount of the payment and the name of the payee on the Voucher are correct, in conformance with the Department of the Treasury’s prescribed standard format.

(iii)   A proper Social Security Number, Taxpayer Identification Number, Employer Identification Number, Individual Taxpayer Identification Number, or Payee ID Number is provided for each payee on the Voucher, as applicable.

(iv)    The appropriation or fund from which the payment will be made is available for the purpose set forth in the Voucher and indicated with the appropriate Treasury Account Symbol/Business Event Type Code.

(v)     Payees are not deceased individuals, to the greatest extent permitted by law.

(vi)    The account number provided on the Voucher is held at a financial institution and is open, valid, and belongs to the payee or valid designee of payee.

(vii)   Contracts or agreements are referenced on the Voucher by providing the contract number, referred to as the Procurement Instrument Identifier, where applicable.

(viii)  Financial assistance awards (non-aggregate) are referenced on the Voucher by providing the award number, referred to as the Federal Award Identification Number, where applicable.

(ix)    For summary schedules, the payments on the Voucher are submitted in conformance with the Department of the Treasury prescribed standard formats for such schedules.

(c)  Agency heads shall submit payment files other than with respect to same-day payments to the Secretary of the Treasury or the Secretary’s designee with sufficient lead time prior to the date of disbursement as determined by the Department of the Treasury and provided in the requirements and instructions issued pursuant to subsections (a) and (b) of this section, to allow for fraud and improper payment screening, to the extent permissible by law.  With respect to same-day payments, agency heads shall submit payment files to the Secretary of the Treasury or the Secretary’s designee as much in advance as reasonably practicable.

(d)  In issuing requirements and instructions pursuant to subsection (a) of this section, the Secretary of the Treasury shall consider whether it would be appropriate to provide that the Department of the Treasury’s Chief Disbursing Officer return to the relevant agency for reconciliation any payments that do not pass the pre-certification verification processes established pursuant to section 3(a) of this order and notify the designated CO.  

(e)  The Secretary of the Treasury shall include in the guidance issued pursuant to subsection (a) of this section, or in other regulations or guidance, a transparent process for agencies to request exemptions from some or all of the payment verification requirements for specific payments or categories of payments.

Sec. 5.  Core Financial System Consolidation.  (a)  Within 180 days of the date of this order, the OMB Director shall issue guidance that directs agencies described in 31 U.S.C. 901(b) (CFO Act agencies) to consolidate their core financial systems.

(b)  As soon as practicable, but not later than 180 days of the date of this order, the OMB Director, in consultation with the Secretary of the Treasury, shall issue guidance directing all non-CFO Act agencies to consolidate transactional financial management services under a single provider approved by the Department of the Treasury.

(c)  As soon as practicable, all heads of CFO Act agencies shall use standard financial management solutions available through the Financial Management Marketplace, administered by the Financial Management Quality Service Management Office.

(d)  Agency heads shall ensure that core financial systems comply with Federal accounting and financial reporting standards and relevant regulations, orders, guidance documents, policy statements, and other agency actions published by the Department of the Treasury from time to time.

Sec. 6.  Reduction of NTDOs.  (a)  Within 30 days of the date of this order, the Secretary of the Treasury shall assess whether to maintain disbursing authority that it has delegated to agencies pursuant to 31 U.S.C. 3321(b) and issue notices to revoke such delegations, as appropriate, in accordance with applicable law.  

(b)  The heads of agencies with disbursing authority under 31 U.S.C. 3321(c), including the Secretary of Defense, the Secretary of Homeland Security, and the Attorney General (but excluding, for the avoidance of doubt, the Supreme Court and other entities of the Federal Government outside the Executive Branch) will work with the Secretary of the Treasury to delegate the performance of their disbursing activities, other than with respect to classified payments, to the Department of the Treasury’s Chief Disbursing Officer in accordance with applicable law. 

(c)  Notwithstanding subsections (a) or (b) of this section, the Secretary of the Treasury may continue to delegate disbursing authority to NTDOs at other agencies when doing so would align with significant Government priorities.  Any remaining NTDOs are required to report daily to the Department of the Treasury’s centralized accounting and reporting system in accordance with then-current Department of the Treasury guidance and applicable law.

(d)  The Secretary of the Treasury shall develop a plan to centralize and manage all payments previously disbursed by NTDOs, ensuring seamless continuity of Government payments.

(e)  The Secretary of the Treasury, in coordination with agency heads, shall establish a transition plan for agencies currently operating as NTDOs, including staffing adjustments, system integrations, and legal or regulatory modifications necessary for full consolidation.

(f)  The heads of agencies with disbursing authority delegated to the agency under 33 U.S.C. 3321(b) shall decommission all internal payment systems and use the Department of the Treasury’s disbursement systems, except and to the extent authorized by the Department of the Treasury or otherwise required by applicable law.

Sec. 7.  Reporting and Implementation Requirements.  (a)  The heads of all agencies shall submit a compliance plan to the OMB Director within 90 days of the date of this order detailing their strategy for:

(i)    transitioning disbursing authority to the Department of the Treasury, as applicable and as contemplated by this order;

(ii)   updating and integrating systems with Department of the Treasury platforms;

(iii)  procedures to verify payment information as contemplated by this order; and

(iv)   transmitting information associated with improper payments to the Department of the Treasury in accordance with standards and reporting specifications established by the OMB Director in coordination with the Secretary of the Treasury as contemplated by this order.

(b)  The Secretary of the Treasury shall submit an implementation report to the President through the Assistant to the President for Economic Policy within 180 days of the date of this order detailing progress on the matters set forth in this order.

(c)  The Secretary of the Treasury and agency heads shall take all necessary steps to protect classified information and systems, as well as personally identifiable information and tax return information, through the implementation of this order.

Sec. 8.  General Provisions.  (a)  Nothing in this order shall be construed to impair or otherwise affect:

(i)   the authority granted by law to an executive department or agency, or the head thereof; or

(ii)  the functions of the Director of the Office of Management and Budget relating to budgetary, administrative, or legislative proposals.

(b)  This order shall be implemented consistent with applicable law and subject to the availability of appropriations.

(c)  This order is not intended to, and does not, create any right or benefit, substantive or procedural, enforceable at law or in equity by any party against the United States, its departments, agencies, or entities, its officers, employees, or agents, or any other person.

DONALD J. TRUMP

THE WHITE HOUSE,

    March 25, 2025.
"""

# Newline-delimited ROLES catalog used by the LLM to set category_dept (verbatim when possible).
ROLES_DEMO = """Secretary of the Treasury (in consultation with OMB Director)
All Agency Heads
Secretary of the Treasury
Agency Heads / Certifying Officers
Secretary of the Treasury & Agency Certifying Officers
OMB Director
OMB Director (in consultation with Secretary of the Treasury)
CFO Act Agency Heads
Heads of agencies with disbursing authority under 31 U.S.C. 3321(c) (e.g., DoD, DHS, DOJ) + Secretary of the Treasury
Secretary of the Treasury & NTDOs remaining after consolidation process
Secretary of the Treasury (in coordination with agency heads)
Agency Heads with authority under 31 U.S.C. 3321(b)
"""

# Roles-with-members mapping as a single free-form string (hardcoded for now).
# Format requested by the team (example):
# Role Name
# 1.Charlie
# 2.James
#
# Each role section is separated by a blank line.
ROLES_WITH_MEMBERS_DEMO = """All Agency Heads
1. Charlie
2. James
3. Priya

Secretary of the Treasury
1. Alex Cole
2. Dana Rivera
3. Morgan Lee

Secretary of the Treasury (in consultation with OMB Director)
1. Taylor Brooks
2. Jordan Kim
3. Casey Nguyen

Agency Heads / Certifying Officers
1. Robin Clark
2. Jamie Patel
3. Avery Chen

Secretary of the Treasury & Agency Certifying Officers
1. Sam Torres
2. Riley Gupta
3. Cameron Ortiz

OMB Director
1. Leslie Park
2. Drew Sullivan
3. Quinn Foster

OMB Director (in consultation with Secretary of the Treasury)
1. Peyton Adams
2. Skyler Romero
3. Rowan Blake

CFO Act Agency Heads
1. Harper Singh
2. Elliot Murphy
3. Reagan Shah

Heads of agencies with disbursing authority under 31 U.S.C. 3321(c) (e.g., DoD, DHS, DOJ) + Secretary of the Treasury
1. Chris Johnson
2. Pat O'Neal
3. Jordan Alvarez

Secretary of the Treasury & NTDOs remaining after consolidation process
1. Frankie Gomez
2. Taylor Diaz
3. Robin Lewis

Secretary of the Treasury (in coordination with agency heads)
1. Parker Allen
2. Jamie Brooks
3. Alex Ramirez

Agency Heads with authority under 31 U.S.C. 3321(b)
1. Casey Brown
2. Drew Carter
3. Morgan Davis
"""

# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------


def extract_directives(eo_pdf_text: str, roles_text: str) -> Dict:
    """
    Extract a list of tasks from the EO text using LangChain + OpenAI (gpt-4.1).

    Parameters
    ----------
    eo_pdf_text : str
        The entire Executive Order text, already converted to a string. Source agnostic.
    roles_text : str
        Newline-delimited roles catalog. The LLM will choose 'category_dept' from these labels.

    Returns
    -------
    Dict
        A JSON-serializable dictionary in the shape:
        {
          "tasks": [
            {
              "id": int,
              "title": str,
              "description": str,
              "category_dept": str,
              "assignee": "",                 # intentionally empty at this stage
              "status": "Pending",
              "due_date": "YYYY-MM-DD"|"TBD",
              "created_at": "ISO-8601"
            },
            ...
          ]
        }
    """
    try:
        # Delegate to our LangChain orchestrator that binds prompts and structured parsing.
        tasks_model: TasksModel = lc_extract_tasks(
            eo_text=eo_pdf_text,
            roles_text=roles_text,
            # eo_date and now_utc are auto-detected/filled when omitted.
        )
        # Convert to a plain dict for downstream assignment logic / transport.
        result = tasks_model.model_dump()
        # Validate that result is a dict with a "tasks" key that is a list of dicts
        if not isinstance(result, dict) or "tasks" not in result or not isinstance(result["tasks"], list):
            raise ValueError("Malformed output: missing or invalid 'tasks' key")
        cleaned_tasks = []
        seen_ids = set()
        for task in result["tasks"]:
            if not isinstance(task, dict):
                continue
            # Check for required fields and duplicates
            required_fields = ["id", "title", "description", "category_dept", "status", "due_date", "created_at"]
            if not all(field in task for field in required_fields):
                continue
            if task["id"] in seen_ids:
                continue
            seen_ids.add(task["id"])
            cleaned_tasks.append(task)
        result["tasks"] = cleaned_tasks
        return result
    except Exception as e:
        print(f"[ERROR] Failed to extract directives: {e}")
        return {"tasks": []}


def assign_tasks(tasks_dict: Dict, roles_with_members_text: str) -> Dict:
    """
    Deterministically assign an 'assignee' to each task based on its 'category_dept' by:
    - Parsing the roles-with-members free-form string into a mapping: role -> [members...]
    - Attempting an exact match between task.category_dept and role keys
    - Falling back to a substring-based best-effort match when no exact key is present
    - Selecting a random member from the matched role's pool

    Parameters
    ----------
    tasks_dict : Dict
        The half-finished LLM result (assignee fields are empty). Shape documented above.
    roles_with_members_text : str
        Free-form string that enumerates roles and members under each role.

    Returns
    -------
    Dict
        The same dictionary with 'assignee' populated where a role match was found.
        If no role match can be determined, 'assignee' remains "" (Unassigned).
    """
    role_map = _parse_roles_with_members(roles_with_members_text)

    for task in tasks_dict.get("tasks", []):
        role_label = (task.get("category_dept") or "").strip()
        if not role_label:
            # No category/dept to map — leave unassigned.
            task["assignee"] = ""
            continue

        members = _resolve_role_to_pool(role_label, role_map)
        if members:
            # Choose a random member. The randomness is acceptable for Week 1.
            task["assignee"] = random.choice(members)
        else:
            # No clear match — leave blank; upstream PMO can adjust if needed.
            task["assignee"] = ""

    return tasks_dict


# --------------------------------------------------------------------------------------
# Helpers (roles-with-members parsing and matching)
# --------------------------------------------------------------------------------------


def _parse_roles_with_members(text: str) -> Dict[str, List[str]]:
    """
    Parse the roles-with-members string into a dict: role -> [members...].

    Input format expectations (lenient):
    - A role heading is any non-empty line that does NOT start with a number.
    - Member lines start with a number and a period (e.g., '1. Name' or '2.Name').
    - Blank lines may separate sections.

    Example:
        Role X
        1. Alice
        2. Bob

        Role Y
        1. Eve

    Returns
    -------
    Dict[str, List[str]]
    """
    role_map: Dict[str, List[str]] = {}
    current_role: Optional[str] = None

    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            # Blank line — close current section
            current_role = None
            continue

        if re.match(r"^\d+\.\s*", line):
            # Member line
            if current_role is None:
                # Malformed input; ignore this orphaned member
                continue
            # Remove the leading numbering prefix '1.' or '2. '
            member = re.sub(r"^\d+\.\s*", "", line).strip()
            if member:
                role_map.setdefault(current_role, []).append(member)
        else:
            # New role heading
            current_role = line
            role_map.setdefault(current_role, [])

    return role_map


def _resolve_role_to_pool(category_dept: str, role_map: Dict[str, List[str]]) -> List[str]:
    """
    Resolve the best member pool for a given category_dept string.

    Matching strategy:
    1) Exact key match
    2) Case-insensitive exact match
    3) Substring heuristics: if a role_map key is contained within category_dept, prefer the longest match.
    4) If still no match: try to match common key fragments like 'Secretary of the Treasury' or 'OMB Director'.

    Parameters
    ----------
    category_dept : str
        The task's category/dept text as produced by the LLM.
    role_map : Dict[str, List[str]]
        Parsed mapping from roles-with-members text.

    Returns
    -------
    List[str]
        Member list to sample from, or empty list if no suitable role can be found.
    """
    if not category_dept:
        return []

    # 1) Exact key match
    if category_dept in role_map:
        return role_map[category_dept]

    # 2) Case-insensitive exact match
    lowered_keys = {k.lower(): k for k in role_map.keys()}
    if category_dept.lower() in lowered_keys:
        return role_map[lowered_keys[category_dept.lower()]]

    # 3) Substring heuristic — prefer the longest matching key contained in category_dept
    best_key: Optional[str] = None
    cat_low = category_dept.lower()
    for key in role_map.keys():
        if key.lower() in cat_low:
            if best_key is None or len(key) > len(best_key):
                best_key = key
    if best_key:
        return role_map[best_key]

    # 4) Common fragments
    fragments = [
        "Secretary of the Treasury",
        "OMB Director",
        "All Agency Heads",
        "Certifying Officers",
        "NTDOs",
        "CFO Act Agency Heads",
        "Agency Heads",
        "disbursing authority",
    ]
    for frag in fragments:
        for key in role_map.keys():
            if frag.lower() in key.lower() and frag.lower() in cat_low:
                return role_map[key]

    # No match found
    return []


# --------------------------------------------------------------------------------------
# CLI entrypoint for quick local testing with hardcoded demo data (Week 1)
# --------------------------------------------------------------------------------------

def _pretty(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _demo_run() -> None:
    """
    Runs the pipeline end-to-end on hardcoded demo strings:
    - Extract tasks with empty assignees
    - Assign members based on category_dept
    - Print the final JSON payload
    """
    # Step 1: extract tasks (assignee fields will be "")
    tasks_no_assignees = extract_directives(EO_PDF_DEMO, ROLES_DEMO)

    # Step 2: assign members based on roles-with-members mapping
    final_payload = assign_tasks(tasks_no_assignees, ROLES_WITH_MEMBERS_DEMO)

    # Print for verification
    print(_pretty(final_payload))


if __name__ == "__main__":
    # Optionally seed randomness for reproducibility during local testing
    # random.seed(42)
    _demo_run()
