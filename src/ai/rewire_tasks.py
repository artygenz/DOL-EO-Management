"""
rewire_tasks.py

Standalone functions for EO task rewiring, update extraction, and summary generation.
Each function is parameterized and can be called independently. All AI prompt logic is in prompts.py,
and LLM orchestration is in langchain_utils.py
"""

from typing import Dict, List, Any

try:
    from .langchain_utils import (
        rewire_tasks_llm,
        rewire_tasks_conscience_check_llm,
        generate_task_update_llm,
        generate_task_summaries_llm,
        generate_eo_weekly_summary_llm,
    )
except ImportError:
    # Allow running as a script: fallback to absolute import
    from langchain_utils import (
        rewire_tasks_llm,
        rewire_tasks_conscience_check_llm,
        generate_task_update_llm,
        generate_task_summaries_llm,
        generate_eo_weekly_summary_llm,
    )

# -------------------- 1. Rewire Tasks With Remarks --------------------

def rewire_tasks_with_remarks(eo: str, remarks: str, tasks: dict, roles_text: str) -> dict:
    """
    Rewrites EO tasks based on PMO remarks, checks for hallucination/conscience, and returns results.

    Parameters
    ----------
    eo : str
        The full Executive Order text.
    remarks : str
        PMO's remarks (unstructured, from email body).
    tasks : dict
        Original tasks dict (see example in doc).
    roles_text : str
        The roles catalog string for task assignment.

    Returns
    -------
    dict
        The final dict with revised tasks and summary.
    """
    # First LLM call: rewrite tasks and summarize changes
    first_result = rewire_tasks_llm(eo, remarks, tasks, roles_text)
    revised_tasks = first_result.get("tasks", [])
    summary = first_result.get("summary", "")

    # Second LLM call: conscience check
    check_result = rewire_tasks_conscience_check_llm(
        eo=eo,
        remarks=remarks,
        original_tasks=tasks,
        summary=summary,
        revised_tasks=revised_tasks,
    )
    score = check_result.get("score", 100)
    verdict = check_result.get("verdict", "")

    if score >= 80:
        print("=== Final Output (from first LLM call, conscience score: {}%) ===".format(score))
        print(first_result)
        print("Source: first LLM call, conscience score: {}%".format(score))
        return first_result
    else:
        print("=== Final Output (from second LLM call, conscience score: {}%) ===".format(score))
        # Use the corrected tasks/summary from the check LLM
        output = {
            "tasks": check_result.get("tasks", []),
            "summary": check_result.get("summary", ""),
        }
        print(output)
        print("Source: second LLM call, conscience score: {}%".format(score))
        return output

# -------------------- 2. Generate Task Update From Update Email --------------------

def generate_task_update_from_update_email(employee_role: str, raw_update: str, task: dict) -> Dict:
    """
    Extracts a structured task update from an employee's email update.

    Parameters
    ----------
    employee_role : str
        The employee's role (e.g., "Secretary of the Treasury (in consultation with OMB Director)").
    raw_update : str
        The raw email update text.
    task : dict
        The original task dict.

    Returns
    -------
    Dict
        Structured task update dict.
    """
    return generate_task_update_llm(employee_role, raw_update, task)

# -------------------- 3. Generate Summary From List of Task Updates --------------------

def generate_summary_from_list_of_task_updates(task_update_list: List[Dict], EO: str) -> List[Dict]:
    """
    Adds a 'summary' field to each task update in the list, summarizing progress, blockers, and risks.

    Parameters
    ----------
    task_update_list : List[Dict]
        List of structured task update dicts.
    EO : str
        The full Executive Order text.

    Returns
    -------
    List[Dict]
        List of task updates, each with a 'summary' field.
    """
    return generate_task_summaries_llm(task_update_list, EO)

# -------------------- 4. EO Weekly Summary Maker --------------------

def generate_eo_weekly_summary(six_day_summary: List[Dict], EO: str, tasks: List[Dict]) -> Dict:
    """
    Generates a comprehensive weekly summary report for a single EO.

    Parameters
    ----------
    six_day_summary : List[Dict]
        List of daily summaries for the week.
    EO : str
        The full Executive Order text.
    tasks : List[Dict]
        The original assigned tasks for the EO.

    Returns
    -------
    Dict
        Weekly summary report dict.
    """
    return generate_eo_weekly_summary_llm(six_day_summary, EO, tasks)

# -------------------- Demo Main --------------------

if __name__ == "__main__":
    # 1. Demo for rewire_tasks_with_remarks
    EOstring = """ 
 Presidential Actions
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
"""  # Replace with actual EO text for real use

    remarks = (
        "Hello Team,\n"
        "After reviewing the generated tasks for this Executive Order, I am requesting the following corrections before approval:\n"
        "1. Task “Update guidance and enhance payment verification systems” (Sec. 3(a))\n"
        "   - The description is too general. Please clarify which specific systems must be updated (e.g., Do Not Pay integration, pre-certification platform).\n"
        "   - Add a due date in line with the EO’s 90-day timeline.\n"
        "2. Task “Cooperate with Treasury on pre-certification and pre-award procedures” (Sec. 3(b))\n"
        "   - Assigned owner “All Agency Heads” is too broad. Please list responsible sub-agencies or groups.\n"
        "3. Task “Submit compliance plan to OMB Director within 90 days” (Sec. 7(a))\n"
        "   - The deadline is June 23d, 2025. Please ensure this due date is explicitly captured in the task metadata.\n"
        "4. General remarks\n"
        "   - Several tasks reference “pending” status without target completion dates. Please populate milestone dates where the EO specifies 30-day, 90-day, or 180-day requirements.\n"
        "   - Ensure every task includes a clear “Responsible Role” aligned with the ROLES catalog (e.g., OMB Director, Certifying Officers).\n"
        "Once these updates are made, please resend the task package for approval.\n"
        "Thanks,\n"
        "PMO Office"
    )

    tasks_dict = {
      "tasks": [
        {
          "id": 1,
          "title": "Update guidance and enhance payment verification systems",
          "description": "Per Sec. 3(a), update guidance and enhance systems to ensure all Treasury-disbursed payments are subject to pre-certification verification, including compliance with Do Not Pay and other validation programs.",
          "category_dept": "Secretary of the Treasury (in consultation with OMB Director)",
          "assignee": "Jordan Kim",
          "status": "Pending",
          "due_date": "TBD",
          "created_at": "2025-08-17T17:23:01.700439+00:00"
        },
        {
          "id": 2,
          "title": "Cooperate with Treasury on pre-certification and pre-award procedures",
          "description": "Cooperate with the Secretary of the Treasury to fulfill obligations for payment or award eligibility determination through pre-certification and pre-award procedures. Per Sec. 3(b).",
          "category_dept": "All Agency Heads",
          "assignee": "James",
          "status": "Pending",
          "due_date": "TBD",
          "created_at": "2025-08-17T17:23:01.700439+00:00"
        },
        {
          "id": 3,
          "title": "Waive Privacy Act requirements for computer matching to prevent fraud",
          "description": "Exercise authority to waive 5 U.S.C. 552a(o) requirements for computer matching activities, in consultation with OMB Director, to minimize barriers to data access for fraud prevention. Per Sec. 3(c).",
          "category_dept": "Secretary of the Treasury (in consultation with OMB Director)",
          "assignee": "Jordan Kim",
          "status": "Pending",
          "due_date": "TBD",
          "created_at": "2025-08-17T17:23:01.700439+00:00"
        }
      ]
    }

    # Add some per-task remarks to demonstrate the functionality
    tasks_dict["tasks"][0]["remarks"] = "Task is too vague, needs more specific deliverables"
    tasks_dict["tasks"][1]["remarks"] = "Should be assigned to Director of Compliance instead of CFO"
    tasks_dict["tasks"][2]["remarks"] = "Missing timeline and success criteria"

    print("\n--- DEMO: rewire_tasks_with_remarks ---")
    # Use database roles instead of hardcoded ones
    from src.db.users import build_roles_with_members_text
    roles_text = build_roles_with_members_text()
    if not roles_text.strip():
        # Fallback for demo if no users in DB
        roles_text = "CFO\n1. Jack Smith\n\nDeputy CFO\n1. Kevin Brown\n\nDirector of Compliance\n1. Dylan Sachetti"
    
    improved_tasks = rewire_tasks_with_remarks(EOstring, remarks, tasks_dict, roles_text)
    print("Improved tasks:", improved_tasks)

    # 2. Demo for generate_task_update_from_update_email
    employee_role = "Secretary of the Treasury (in consultation with OMB Director)"
    raw_update = (
        "Subject: [EO-db58338f][TASK-f243dc77] Daily Update\n\n"
        "Hey,\n\n"
        "Spent most of today reviewing the existing Treasury payment verification scripts. \n"
        "Found some gaps with how Do Not Pay checks are being applied. Fixed about 70% of the issues, but we still need \n"
        "clarification from OMB before we can finalize changes. \n\n"
        "ETA: might need another week.  \n"
        "Progress feels like around 60% done.  \n"
        "- John"
    )
    task = {
      "task_id": "f243dc77-955b-40e7-b15f-0e3610298d9b",
      "eo_id": "db58338f-3848-40d8-99c0-22b0fc17695b",
      "title": "Update guidance and enhance payment verification systems",
      "assignee": "johnsmith",
      "description": "Per Sec. 3(a), update guidance and enhance systems to ensure all Treasury-disbursed payments are subject to pre-certification verification, including compliance with Do Not Pay and other validation programs.",
      "status": "pending",
      "role": "Secretary of the Treasury (in consultation with OMB Director)"
    }
    print("\n--- DEMO: generate_task_update_from_update_email ---")
    print(generate_task_update_from_update_email(employee_role, raw_update, task))

    # 3. Demo for generate_summary_from_list_of_task_updates
    task_update_list = [
        {
            "Task_title": "Update guidance and enhance payment verification systems",
            "assignee": "Jordan Kim",
            "progress_pct": 60,
            "hours_spent": 5,
            "status_note": "Reviewed existing payment verification scripts. Fixed ~70% of gaps. Awaiting OMB clarification before finalizing.",
            "blockers": ["Need clarification from OMB on Do Not Pay checks"],
            "risks": ["Delays if OMB response is late"],
            "next_actions": ["Follow up with OMB", "Finalize script updates"],
            "extraction_confidence": 85,
            "created_at": "2025-08-18T14:32:11Z"
        },
        {
            "Task_title": "Cooperate with Treasury on pre-certification and pre-award procedures",
            "assignee": "James",
            "progress_pct": 30,
            "hours_spent": 3,
            "status_note": "Initial coordination meeting held with Treasury team. Awaiting draft procedures for review.",
            "blockers": ["Treasury draft procedures not yet delivered"],
            "risks": ["May not meet internal deadlines if drafts are delayed"],
            "next_actions": ["Request draft procedures from Treasury", "Review and provide feedback"],
            "extraction_confidence": 80,
            "created_at": "2025-08-18T14:35:42Z"
        },
        {
            "Task_title": "Waive Privacy Act requirements for computer matching to prevent fraud",
            "assignee": "Jordan Kim",
            "progress_pct": 75,
            "hours_spent": 6,
            "status_note": "Drafted waiver framework in consultation with OMB legal team. Identified key sections requiring sign-off.",
            "blockers": ["Pending legal clearance from OMB"],
            "risks": ["Implementation may be delayed without timely OMB approval"],
            "next_actions": ["Finalize draft waiver", "Submit for OMB clearance"],
            "extraction_confidence": 88,
            "created_at": "2025-08-18T14:38:09Z"
        }
    ]
    print("\n--- DEMO: generate_summary_from_list_of_task_updates ---")
    print(generate_summary_from_list_of_task_updates(task_update_list, EOstring))

    # 4. Demo for generate_eo_weekly_summary
    six_day_summary = [
        {
            "day": 1,
            "date": "2025-08-12",
            "tasks": [
                {
                    "assignee": "Alice Johnson",
                    "Task_title": "Review design documents",
                    "progress_pct": 50,
                    "hours_spent": 8.0,
                    "status_note": "Initial review started, identified key sections needing updates.",
                    "blockers": [],
                    "risks": ["Architect feedback turnaround may be slow"],
                    "next_actions": ["Send clarifying questions to architect"],
                    "summary": "Review underway, progress slower than expected due to unclear requirements."
                },
                {
                    "assignee": "Bob Smith",
                    "Task_title": "Test integration with subsystem Y",
                    "progress_pct": 20,
                    "hours_spent": 5.0,
                    "status_note": "Setup environment, waiting on vendor API.",
                    "blockers": ["Vendor API not delivered"],
                    "risks": ["Integration may slip if vendor delay persists"],
                    "next_actions": ["Ping vendor for API status"],
                    "summary": "Task blocked early; risk of major delay due to vendor dependency."
                },
                {
                    "assignee": "Charlie Patel",
                    "Task_title": "Implement feature X",
                    "progress_pct": 60,
                    "hours_spent": 12.0,
                    "status_note": "Core functionality coded, unit tests in progress.",
                    "blockers": [],
                    "risks": ["Potential rework from code review"],
                    "next_actions": ["Finish unit tests"],
                    "summary": "Implementation progressing well; only minor risks expected."
                }
            ]
        },
    ]
    tasks_for_week = [
        {
            "id": 1,
            "title": "Review design documents",
            "assignee": "Alice Johnson",
            "status": "Pending",
            "due_date": "2025-08-20",
            "created_at": "2025-08-12T09:00:00Z"
        },
        {
            "id": 2,
            "title": "Test integration with subsystem Y",
            "assignee": "Bob Smith",
            "status": "Pending",
            "due_date": "2025-08-20",
            "created_at": "2025-08-12T09:00:00Z"
        },
        {
            "id": 3,
            "title": "Implement feature X",
            "assignee": "Charlie Patel",
            "status": "Pending",
            "due_date": "2025-08-20",
            "created_at": "2025-08-12T09:00:00Z"
        }
    ]
    print("\n--- DEMO: generate_eo_weekly_summary ---")
    print(generate_eo_weekly_summary(six_day_summary, EOstring, tasks_for_week))
