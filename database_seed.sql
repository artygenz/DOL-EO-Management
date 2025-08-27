--
-- PostgreSQL database dump
--

\restrict tAplqhac0BrrBtZHd63lYXYLvVLYqmJVmBmXPTuvXlj1jdoNXrpbRMnMUdGyTFh

-- Dumped from database version 13.22 (Debian 13.22-1.pgdg13+1)
-- Dumped by pg_dump version 13.22 (Debian 13.22-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.alembic_version VALUES ('fcc836971b2d');


--
-- Data for Name: executive_orders; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.executive_orders VALUES ('e8514019-182d-4197-a902-a054d4ab1da4', 'EO: Modernize Workforce Data', 'Presidential ActionsProtecting America’s Bank Account Against Fraud, Waste, and AbuseExecutive OrdersMarch 25, 2025 By the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered:Section 1. Purpose.  Promoting financial integrity and operational efficiency are critical responsibilities of the Federal Government.  The Federal Government processes trillions of dollars annually in disbursements to individuals, businesses, and organizations, and in receipts from taxes, fees, and other payments to finance daily and long-term Government operations.  These transactions flow into and out of the United States General Fund (General Fund), which might be thought of as America’s bank account.  In Fiscal Year 2024, $33.9 trillion flowed into the General Fund and $33.6 trillion flowed out of the account, including $5.87 trillion (less net interest) in benefits, grants, loans, vendor payments, and other disbursements. The Department of the Treasury is the largest financial payment manager of the Federal Government and is responsible for safeguarding the General Fund, but lacks sufficient controls to track transactions flowing through the General Fund to determine if they were proper.  To enforce sufficient controls and ensure accountability to American taxpayers, the Department of the Treasury requires financial information from executive departments and agencies (agencies) beyond what they currently provide.Financial fraud threatens the integrity of Federal programs and undermines trust in Government.  Agencies’ past underinvestment in technology and longstanding challenges with access to accurate data has prevented them from more fully safeguarding taxpayer dollars against fraud and improper payments.  The Government Accountability Office estimates that the Federal Government loses between $233 and $521 billion annually to fraud.In addition to being an efficient steward of taxpayer funds, the Federal Government, on behalf of the American public, must seek to ensure that financial information is accurate and that there is transparency with respect to how taxpayer dollars are being used.  Today, Federal funds are disbursed both by the Department of the Treasury and various Federal Government entities that are authorized to issue their own disbursements known as Non-Treasury Disbursing Offices (NTDOs).  In Fiscal Year 2024, NTDOs were estimated to be responsible for 181 million payments totaling over $1.5 trillion (approximately 22 percent of all Federal Government dollars disbursed). This fragmentation of disbursing authority, together with the proliferation of non-standard financial management systems across the Federal Government, leads to expensive, disjointed, and duplicative financial reporting, lack of financial traceability, complicated financial management, opacity, increased operational risks, and decreased ability of the Department of the Treasury to provide centralized oversight.This order promotes financial integrity by enabling the Department of the Treasury to more easily conduct improper payment and fraud prevention screening prior to disbursing funds on behalf of agencies.  This order increases transparency and accountability by requiring agencies to provide the Department of the Treasury with the information needed to track transactions through the General Fund in greater detail.  This order also promotes operational efficiency by returning disbursing functions to the Department of the Treasury when possible and consolidating and standardizing core Federal financial systems.Sec. 2.  Policy.  It is the policy of the United States to defend against financial fraud and improper payments, increase transparency and accountability around the Federal Government’s operations and financial condition, increase efficiency, reduce costs, and enhance the security of Federal payments.Sec. 3.  Treasury Verification of Agency Payments Information.  (a)  The Secretary of the Treasury, in consultation with the Director of the Office of Management and Budget (OMB Director), shall update guidance and enhance systems to ensure that all payments made by the Department of the Treasury on behalf of agencies pursuant to the Secretary of the Treasury’s disbursing authority, including 31 U.S.C. 3321, are subject to pre-certification verification processes established by the Secretary of the Treasury and conducted by agencies and the Department of the Treasury for the purposes of defending against financial fraud and improper payments, to the greatest extent permitted by law.  Such guidance shall set forth guidelines for compliance with the Do Not Pay Working System as described in 31 U.S.C. 3351 et seq., and such other payment, account, and payee validation programs and services that the Secretary of the Treasury and the OMB Director determine to be beneficial for reducing financial fraud and improper payments.(b)  In accordance with 31 U.S.C. 3354, the heads of all agencies shall cooperate with the Secretary of the Treasury to fulfill their obligations to determine payment or award eligibility through pre-certification and pre-award procedures, as determined by the Secretary of the Treasury, including pursuant to subsection (a) of this section and section 4 of this order to prevent fraud and improper payments.(c)  The Secretary of the Treasury is directed to minimize administrative barriers to accessing and using data to prevent fraud and improper payments by exercising the authority in 31 U.S.C. 3351 et seq. to waive the requirements of 5 U.S.C. 552a(o), in consultation with the OMB Director, in any case or class of cases for computer matching activities, to the extent permissible by law.(d)  Within 90 days of the date of this order, agency heads shall review and modify, as applicable, their relevant system of records notices under the Privacy Act of 1974 to include a “routine use” that allows for the disclosure of records to the Department of the Treasury for the purposes of identifying, preventing, or recouping fraud and improper payments, to the extent permissible by law. (e)  The Secretary of the Treasury, in consultation with the OMB Director, shall issue guidance to agency heads on the circumstances in which agency heads, to the extent permissible by law, may provide the Secretary of the Treasury with access to data necessary for the purposes of detecting and preventing fraud and improper payments, as well as data for payment information verification (and not, for example, data such as health records).Sec. 4.  Implementation and Compliance of Payment Verification.  (a)  Agency heads, through designated agency officials (Certifying Officers or COs), who are responsible for verifying that disbursements made by the Federal Government are legal, proper, and correct, and for performing the duties in 31 U.S.C. 3528, shall comply with the disbursement requirements and instructions, including pre-certification requirements, published by the Secretary of the Treasury.(b)  The Secretary of the Treasury shall consider, as appropriate, issuing instructions to agencies to enforce the following pre-certification criteria for disbursement requests submitted by COs (Vouchers) before they are certified for payment by the CO:(i)     Funds are available at the time the obligation is incurred.  If an obligation is incurred when funds are not available, then the CO shall not certify the payment.(ii)    The amount of the payment and the name of the payee on the Voucher are correct, in conformance with the Department of the Treasury’s prescribed standard format.(iii)   A proper Social Security Number, Taxpayer Identification Number, Employer Identification Number, Individual Taxpayer Identification Number, or Payee ID Number is provided for each payee on the Voucher, as applicable.(iv)    The appropriation or fund from which the payment will be made is available for the purpose set forth in the Voucher and indicated with the appropriate Treasury Account Symbol/Business Event Type Code.(v)     Payees are not deceased individuals, to the greatest extent permitted by law.(vi)    The account number provided on the Voucher is held at a financial institution and is open, valid, and belongs to the payee or valid designee of payee.(vii)   Contracts or agreements are referenced on the Voucher by providing the contract number, referred to as the Procurement Instrument Identifier, where applicable.(viii)  Financial assistance awards (non-aggregate) are referenced on the Voucher by providing the award number, referred to as the Federal Award Identification Number, where applicable.(ix)    For summary schedules, the payments on the Voucher are submitted in conformance with the Department of the Treasury prescribed standard formats for such schedules.(c)  Agency heads shall submit payment files other than with respect to same-day payments to the Secretary of the Treasury or the Secretary’s designee with sufficient lead time prior to the date of disbursement as determined by the Department of the Treasury and provided in the requirements and instructions issued pursuant to subsections (a) and (b) of this section, to allow for fraud and improper payment screening, to the extent permissible by law.  With respect to same-day payments, agency heads shall submit payment files to the Secretary of the Treasury or the Secretary’s designee as much in advance as reasonably practicable.(d)  In issuing requirements and instructions pursuant to subsection (a) of this section, the Secretary of the Treasury shall consider whether it would be appropriate to provide that the Department of the Treasury’s Chief Disbursing Officer return to the relevant agency for reconciliation any payments that do not pass the pre-certification verification processes established pursuant to section 3(a) of this order and notify the designated CO.  (e)  The Secretary of the Treasury shall include in the guidance issued pursuant to subsection (a) of this section, or in other regulations or guidance, a transparent process for agencies to request exemptions from some or all of the payment verification requirements for specific payments or categories of payments.Sec. 5.  Core Financial System Consolidation.  (a)  Within 180 days of the date of this order, the OMB Director shall issue guidance that directs agencies described in 31 U.S.C. 901(b) (CFO Act agencies) to consolidate their core financial systems.(b)  As soon as practicable, but not later than 180 days of the date of this order, the OMB Director, in consultation with the Secretary of the Treasury, shall issue guidance directing all non-CFO Act agencies to consolidate transactional financial management services under a single provider approved by the Department of the Treasury.(c)  As soon as practicable, all heads of CFO Act agencies shall use standard financial management solutions available through the Financial Management Marketplace, administered by the Financial Management Quality Service Management Office.(d)  Agency heads shall ensure that core financial systems comply with Federal accounting and financial reporting standards and relevant regulations, orders, guidance documents, policy statements, and other agency actions published by the Department of the Treasury from time to time.Sec. 6.  Reduction of NTDOs.  (a)  Within 30 days of the date of this order, the Secretary of the Treasury shall assess whether to maintain disbursing authority that it has delegated to agencies pursuant to 31 U.S.C. 3321(b) and issue notices to revoke such delegations, as appropriate, in accordance with applicable law.  (b)  The heads of agencies with disbursing authority under 31 U.S.C. 3321(c), including the Secretary of Defense, the Secretary of Homeland Security, and the Attorney General (but excluding, for the avoidance of doubt, the Supreme Court and other entities of the Federal Government outside the Executive Branch) will work with the Secretary of the Treasury to delegate the performance of their disbursing activities, other than with respect to classified payments, to the Department of the Treasury’s Chief Disbursing Officer in accordance with applicable law. (c)  Notwithstanding subsections (a) or (b) of this section, the Secretary of the Treasury may continue to delegate disbursing authority to NTDOs at other agencies when doing so would align with significant Government priorities.  Any remaining NTDOs are required to report daily to the Department of the Treasury’s centralized accounting and reporting system in accordance with then-current Department of the Treasury guidance and applicable law.(d)  The Secretary of the Treasury shall develop a plan to centralize and manage all payments previously disbursed by NTDOs, ensuring seamless continuity of Government payments.(e)  The Secretary of the Treasury, in coordination with agency heads, shall establish a transition plan for agencies currently operating as NTDOs, including staffing adjustments, system integrations, and legal or regulatory modifications necessary for full consolidation.(f)  The heads of agencies with disbursing authority delegated to the agency under 33 U.S.C. 3321(b) shall decommission all internal payment systems and use the Department of the Treasury’s disbursement systems, except and to the extent authorized by the Department of the Treasury or otherwise required by applicable law.Sec. 7.  Reporting and Implementation Requirements.  (a)  The heads of all agencies shall submit a compliance plan to the OMB Director within 90 days of the date of this order detailing their strategy for:(i)    transitioning disbursing authority to the Department of the Treasury, as applicable and as contemplated by this order;(ii)   updating and integrating systems with Department of the Treasury platforms;(iii)  procedures to verify payment information as contemplated by this order; and(iv)   transmitting information associated with improper payments to the Department of the Treasury in accordance with standards and reporting specifications established by the OMB Director in coordination with the Secretary of the Treasury as contemplated by this order.(b)  The Secretary of the Treasury shall submit an implementation report to the President through the Assistant to the President for Economic Policy within 180 days of the date of this order detailing progress on the matters set forth in this order.(c)  The Secretary of the Treasury and agency heads shall take all necessary steps to protect classified information and systems, as well as personally identifiable information and tax return information, through the implementation of this order.Sec. 8.  General Provisions.  (a)  Nothing in this order shall be construed to impair or otherwise affect:(i)   the authority granted by law to an executive department or agency, or the head thereof; or(ii)  the functions of the Director of the Office of Management and Budget relating to budgetary, administrative, or legislative proposals.(b)  This order shall be implemented consistent with applicable law and subject to the availability of appropriations.(c)  This order is not intended to, and does not, create any right or benefit, substantive or procedural, enforceable at law or in equity by any party against the United States, its departments, agencies, or entities, its officers, employees, or agents, or any other person.DONALD J. TRUMPTHE WHITE HOUSE,    March 25, 2025.# Newline-delimited ROLES catalog used by the LLM to set category_dept (verbatim when possible).ROLES_DEMO = Secretary of the Treasury (in consultation with OMB Director)All Agency HeadsSecretary of the TreasuryAgency Heads / Certifying OfficersSecretary of the Treasury & Agency Certifying OfficersOMB DirectorOMB Director (in consultation with Secretary of the Treasury)CFO Act Agency HeadsHeads of agencies with disbursing authority under 31 U.S.C. 3321(c) (e.g., DoD, DHS, DOJ) + Secretary of the TreasurySecretary of the Treasury & NTDOs remaining after consolidation processSecretary of the Treasury (in coordination with agency heads)Agency Heads with authority under 31 U.S.C. 3321(b)', 'sec@agency.gov', '2025-08-13 15:00:00+00', NULL, 'error', '2025-08-26 18:18:02.054741+00', '2025-08-26 18:18:02.063385+00', 'msg-2001@sample');


--
-- Data for Name: email_logs; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.email_logs VALUES ('08e0278d-2a66-4604-8e89-c962c5b81c35', 'incoming', 'EO: Modernize Workforce Data', 'sec@agency.gov', '{ops@dol.gov}', 'Presidential ActionsProtecting America’s Bank Account Against Fraud, Waste, and AbuseExecutive OrdersMarch 25, 2025 By the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered:Section 1. Purpose.  Promoting financial integrity and operational efficiency are critical responsibilities of the Federal Government.  The Federal Government processes trillions of dollars annually in disbursements to individuals, businesses, and organizations, and in receipts from taxes, fees, and other payments to finance daily and long-term Government operations.  These transactions flow into and out of the United States General Fund (General Fund), which might be thought of as America’s bank account.  In Fiscal Year 2024, $33.9 trillion flowed into the General Fund and $33.6 trillion flowed out of the account, including $5.87 trillion (less net interest) in benefits, grants, loans, vendor payments, and other disbursements. The Department of the Treasury is the largest financial payment manager of the Federal Government and is responsible for safeguarding the General Fund, but lacks sufficient controls to track transactions flowing through the General Fund to determine if they were proper.  To enforce sufficient controls and ensure accountability to American taxpayers, the Department of the Treasury requires financial information from executive departments and agencies (agencies) beyond what they currently provide.Financial fraud threatens the integrity of Federal programs and undermines trust in Government.  Agencies’ past underinvestment in technology and longstanding challenges with access to accurate data has prevented them from more fully safeguarding taxpayer dollars against fraud and improper payments.  The Government Accountability Office estimates that the Federal Government loses between $233 and $521 billion annually to fraud.In addition to being an efficient steward of taxpayer funds, the Federal Government, on behalf of the American public, must seek to ensure that financial information is accurate and that there is transparency with respect to how taxpayer dollars are being used.  Today, Federal funds are disbursed both by the Department of the Treasury and various Federal Government entities that are authorized to issue their own disbursements known as Non-Treasury Disbursing Offices (NTDOs).  In Fiscal Year 2024, NTDOs were estimated to be responsible for 181 million payments totaling over $1.5 trillion (approximately 22 percent of all Federal Government dollars disbursed). This fragmentation of disbursing authority, together with the proliferation of non-standard financial management systems across the Federal Government, leads to expensive, disjointed, and duplicative financial reporting, lack of financial traceability, complicated financial management, opacity, increased operational risks, and decreased ability of the Department of the Treasury to provide centralized oversight.This order promotes financial integrity by enabling the Department of the Treasury to more easily conduct improper payment and fraud prevention screening prior to disbursing funds on behalf of agencies.  This order increases transparency and accountability by requiring agencies to provide the Department of the Treasury with the information needed to track transactions through the General Fund in greater detail.  This order also promotes operational efficiency by returning disbursing functions to the Department of the Treasury when possible and consolidating and standardizing core Federal financial systems.Sec. 2.  Policy.  It is the policy of the United States to defend against financial fraud and improper payments, increase transparency and accountability around the Federal Government’s operations and financial condition, increase efficiency, reduce costs, and enhance the security of Federal payments.Sec. 3.  Treasury Verification of Agency Payments Information.  (a)  The Secretary of the Treasury, in consultation with the Director of the Office of Management and Budget (OMB Director), shall update guidance and enhance systems to ensure that all payments made by the Department of the Treasury on behalf of agencies pursuant to the Secretary of the Treasury’s disbursing authority, including 31 U.S.C. 3321, are subject to pre-certification verification processes established by the Secretary of the Treasury and conducted by agencies and the Department of the Treasury for the purposes of defending against financial fraud and improper payments, to the greatest extent permitted by law.  Such guidance shall set forth guidelines for compliance with the Do Not Pay Working System as described in 31 U.S.C. 3351 et seq., and such other payment, account, and payee validation programs and services that the Secretary of the Treasury and the OMB Director determine to be beneficial for reducing financial fraud and improper payments.(b)  In accordance with 31 U.S.C. 3354, the heads of all agencies shall cooperate with the Secretary of the Treasury to fulfill their obligations to determine payment or award eligibility through pre-certification and pre-award procedures, as determined by the Secretary of the Treasury, including pursuant to subsection (a) of this section and section 4 of this order to prevent fraud and improper payments.(c)  The Secretary of the Treasury is directed to minimize administrative barriers to accessing and using data to prevent fraud and improper payments by exercising the authority in 31 U.S.C. 3351 et seq. to waive the requirements of 5 U.S.C. 552a(o), in consultation with the OMB Director, in any case or class of cases for computer matching activities, to the extent permissible by law.(d)  Within 90 days of the date of this order, agency heads shall review and modify, as applicable, their relevant system of records notices under the Privacy Act of 1974 to include a “routine use” that allows for the disclosure of records to the Department of the Treasury for the purposes of identifying, preventing, or recouping fraud and improper payments, to the extent permissible by law. (e)  The Secretary of the Treasury, in consultation with the OMB Director, shall issue guidance to agency heads on the circumstances in which agency heads, to the extent permissible by law, may provide the Secretary of the Treasury with access to data necessary for the purposes of detecting and preventing fraud and improper payments, as well as data for payment information verification (and not, for example, data such as health records).Sec. 4.  Implementation and Compliance of Payment Verification.  (a)  Agency heads, through designated agency officials (Certifying Officers or COs), who are responsible for verifying that disbursements made by the Federal Government are legal, proper, and correct, and for performing the duties in 31 U.S.C. 3528, shall comply with the disbursement requirements and instructions, including pre-certification requirements, published by the Secretary of the Treasury.(b)  The Secretary of the Treasury shall consider, as appropriate, issuing instructions to agencies to enforce the following pre-certification criteria for disbursement requests submitted by COs (Vouchers) before they are certified for payment by the CO:(i)     Funds are available at the time the obligation is incurred.  If an obligation is incurred when funds are not available, then the CO shall not certify the payment.(ii)    The amount of the payment and the name of the payee on the Voucher are correct, in conformance with the Department of the Treasury’s prescribed standard format.(iii)   A proper Social Security Number, Taxpayer Identification Number, Employer Identification Number, Individual Taxpayer Identification Number, or Payee ID Number is provided for each payee on the Voucher, as applicable.(iv)    The appropriation or fund from which the payment will be made is available for the purpose set forth in the Voucher and indicated with the appropriate Treasury Account Symbol/Business Event Type Code.(v)     Payees are not deceased individuals, to the greatest extent permitted by law.(vi)    The account number provided on the Voucher is held at a financial institution and is open, valid, and belongs to the payee or valid designee of payee.(vii)   Contracts or agreements are referenced on the Voucher by providing the contract number, referred to as the Procurement Instrument Identifier, where applicable.(viii)  Financial assistance awards (non-aggregate) are referenced on the Voucher by providing the award number, referred to as the Federal Award Identification Number, where applicable.(ix)    For summary schedules, the payments on the Voucher are submitted in conformance with the Department of the Treasury prescribed standard formats for such schedules.(c)  Agency heads shall submit payment files other than with respect to same-day payments to the Secretary of the Treasury or the Secretary’s designee with sufficient lead time prior to the date of disbursement as determined by the Department of the Treasury and provided in the requirements and instructions issued pursuant to subsections (a) and (b) of this section, to allow for fraud and improper payment screening, to the extent permissible by law.  With respect to same-day payments, agency heads shall submit payment files to the Secretary of the Treasury or the Secretary’s designee as much in advance as reasonably practicable.(d)  In issuing requirements and instructions pursuant to subsection (a) of this section, the Secretary of the Treasury shall consider whether it would be appropriate to provide that the Department of the Treasury’s Chief Disbursing Officer return to the relevant agency for reconciliation any payments that do not pass the pre-certification verification processes established pursuant to section 3(a) of this order and notify the designated CO.  (e)  The Secretary of the Treasury shall include in the guidance issued pursuant to subsection (a) of this section, or in other regulations or guidance, a transparent process for agencies to request exemptions from some or all of the payment verification requirements for specific payments or categories of payments.Sec. 5.  Core Financial System Consolidation.  (a)  Within 180 days of the date of this order, the OMB Director shall issue guidance that directs agencies described in 31 U.S.C. 901(b) (CFO Act agencies) to consolidate their core financial systems.(b)  As soon as practicable, but not later than 180 days of the date of this order, the OMB Director, in consultation with the Secretary of the Treasury, shall issue guidance directing all non-CFO Act agencies to consolidate transactional financial management services under a single provider approved by the Department of the Treasury.(c)  As soon as practicable, all heads of CFO Act agencies shall use standard financial management solutions available through the Financial Management Marketplace, administered by the Financial Management Quality Service Management Office.(d)  Agency heads shall ensure that core financial systems comply with Federal accounting and financial reporting standards and relevant regulations, orders, guidance documents, policy statements, and other agency actions published by the Department of the Treasury from time to time.Sec. 6.  Reduction of NTDOs.  (a)  Within 30 days of the date of this order, the Secretary of the Treasury shall assess whether to maintain disbursing authority that it has delegated to agencies pursuant to 31 U.S.C. 3321(b) and issue notices to revoke such delegations, as appropriate, in accordance with applicable law.  (b)  The heads of agencies with disbursing authority under 31 U.S.C. 3321(c), including the Secretary of Defense, the Secretary of Homeland Security, and the Attorney General (but excluding, for the avoidance of doubt, the Supreme Court and other entities of the Federal Government outside the Executive Branch) will work with the Secretary of the Treasury to delegate the performance of their disbursing activities, other than with respect to classified payments, to the Department of the Treasury’s Chief Disbursing Officer in accordance with applicable law. (c)  Notwithstanding subsections (a) or (b) of this section, the Secretary of the Treasury may continue to delegate disbursing authority to NTDOs at other agencies when doing so would align with significant Government priorities.  Any remaining NTDOs are required to report daily to the Department of the Treasury’s centralized accounting and reporting system in accordance with then-current Department of the Treasury guidance and applicable law.(d)  The Secretary of the Treasury shall develop a plan to centralize and manage all payments previously disbursed by NTDOs, ensuring seamless continuity of Government payments.(e)  The Secretary of the Treasury, in coordination with agency heads, shall establish a transition plan for agencies currently operating as NTDOs, including staffing adjustments, system integrations, and legal or regulatory modifications necessary for full consolidation.(f)  The heads of agencies with disbursing authority delegated to the agency under 33 U.S.C. 3321(b) shall decommission all internal payment systems and use the Department of the Treasury’s disbursement systems, except and to the extent authorized by the Department of the Treasury or otherwise required by applicable law.Sec. 7.  Reporting and Implementation Requirements.  (a)  The heads of all agencies shall submit a compliance plan to the OMB Director within 90 days of the date of this order detailing their strategy for:(i)    transitioning disbursing authority to the Department of the Treasury, as applicable and as contemplated by this order;(ii)   updating and integrating systems with Department of the Treasury platforms;(iii)  procedures to verify payment information as contemplated by this order; and(iv)   transmitting information associated with improper payments to the Department of the Treasury in accordance with standards and reporting specifications established by the OMB Director in coordination with the Secretary of the Treasury as contemplated by this order.(b)  The Secretary of the Treasury shall submit an implementation report to the President through the Assistant to the President for Economic Policy within 180 days of the date of this order detailing progress on the matters set forth in this order.(c)  The Secretary of the Treasury and agency heads shall take all necessary steps to protect classified information and systems, as well as personally identifiable information and tax return information, through the implementation of this order.Sec. 8.  General Provisions.  (a)  Nothing in this order shall be construed to impair or otherwise affect:(i)   the authority granted by law to an executive department or agency, or the head thereof; or(ii)  the functions of the Director of the Office of Management and Budget relating to budgetary, administrative, or legislative proposals.(b)  This order shall be implemented consistent with applicable law and subject to the availability of appropriations.(c)  This order is not intended to, and does not, create any right or benefit, substantive or procedural, enforceable at law or in equity by any party against the United States, its departments, agencies, or entities, its officers, employees, or agents, or any other person.DONALD J. TRUMPTHE WHITE HOUSE,    March 25, 2025.# Newline-delimited ROLES catalog used by the LLM to set category_dept (verbatim when possible).ROLES_DEMO = Secretary of the Treasury (in consultation with OMB Director)All Agency HeadsSecretary of the TreasuryAgency Heads / Certifying OfficersSecretary of the Treasury & Agency Certifying OfficersOMB DirectorOMB Director (in consultation with Secretary of the Treasury)CFO Act Agency HeadsHeads of agencies with disbursing authority under 31 U.S.C. 3321(c) (e.g., DoD, DHS, DOJ) + Secretary of the TreasurySecretary of the Treasury & NTDOs remaining after consolidation processSecretary of the Treasury (in coordination with agency heads)Agency Heads with authority under 31 U.S.C. 3321(b)', false, NULL, '2025-08-26 18:18:02.030673+00');
INSERT INTO public.email_logs VALUES ('a6e7f803-a935-4617-b35b-d9f8995b5058', 'outgoing', 'PMO Review Required: EO: Modernize Workforce Data', NULL, '{abbuabhinav.1502@gmail.com}', 'Subject EO: EO: Modernize Workforce Data
EO ID: e8514019-182d-4197-a902-a054d4ab1da4
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Below are the PENDING tasks for PMO action.

INSTRUCTIONS:
1. Copy the table below
2. Paste it in your reply email
3. Fill in the ''Status'' column with ''Approve'' or ''Reject''
4. Fill in the ''Remarks'' column with your feedback
5. Send the email back

NOTE: Please refer to the attached files for detailed information:
- CSV file: Complete task details in spreadsheet format
- JSON file: Structured task data
- TXT file: Full Executive Order text

Task ID | Title | Owner | Assignee | Due | Status | Remarks
--------|-------|-------|----------|-----|--------|--------
1 | Update Guidance and Enhance Payment Verification Systems | — | Dylan Sachetti | — | [Fill Here] | [Fill Here]
2 | Review and Modify System of Records Notices for Routine Use | — | Dylan Sachetti | 2025-06-23 | [Fill Here] | [Fill Here]
3 | Issue Guidance on Data Access for Fraud Prevention | — | Dylan Sachetti | — | [Fill Here] | [Fill Here]
4 | Implement Pre-Certification Payment Verification Requirements | — | Hibbi Iqbal | — | [Fill Here] | [Fill Here]
5 | Submit Payment Files with Sufficient Lead Time for Screening | — | Hibbi Iqbal | — | [Fill Here] | [Fill Here]
6 | Develop Transparent Exemption Request Process for Payment Verification | — | Dylan Sachetti | — | [Fill Here] | [Fill Here]
7 | Consolidate Core Financial Systems for CFO Act Agencies | — | Ayesha Ahsan | 2025-09-21 | [Fill Here] | [Fill Here]
8 | Consolidate Transactional Financial Management for Non-CFO Agencies | — | Ayesha Ahsan | 2025-09-21 | [Fill Here] | [Fill Here]
9 | Ensure Use of Standard Financial Management Solutions | — | Ayesha Ahsan | — | [Fill Here] | [Fill Here]
10 | Assess and Revoke Delegated Disbursing Authority as Appropriate | — | Hibbi Iqbal | 2025-04-24 | [Fill Here] | [Fill Here]
11 | Develop Plan to Centralize and Manage NTDO Payments | — | Ayesha Ahsan | — | [Fill Here] | [Fill Here]
12 | Establish Transition Plan for NTDO Agencies | — | Ayesha Ahsan | — | [Fill Here] | [Fill Here]
13 | Decommission Internal Payment Systems and Use Treasury Systems | — | Robert Springfiled | — | [Fill Here] | [Fill Here]
14 | Submit Agency Compliance Plan to OMB Director | — | Dylan Sachetti | 2025-06-23 | [Fill Here] | [Fill Here]
15 | Submit Implementation Report on EO Progress | — | Dylan Sachetti | 2025-09-21 | [Fill Here] | [Fill Here]
16 | Protect Classified and Sensitive Information During Implementation | — | Robert Springfiled | — | [Fill Here] | [Fill Here]', false, 'e8514019-182d-4197-a902-a054d4ab1da4', '2025-08-26 18:18:58.225858+00');
INSERT INTO public.email_logs VALUES ('280655ec-32a2-4edc-8073-d30b76669c81', 'incoming', 'Re: [PMO ACTION][EO:e8514019-182d-4197-a902-a054d4ab1da4] EO: Modernize Workforce Data — 12 pending tasks', 'pmo@example.gov', '{workflow@example.gov}', 'Task ID	Title	Owner	Assignee	Due	Status	Remarks
1	Update Guidance and Enhance Payment Verification Systems	—	Dylan Sachetti	—	Approve	[Fill Here]
2	Review and Modify System of Records Notices for Routine Use	—	Dylan Sachetti	2025-06-23	Approve	[Fill Here]
3	Issue Guidance on Data Access for Fraud Prevention	—	Dylan Sachetti	—	Approve	[Fill Here]
4	Implement Pre-Certification Payment Verification Requirements	—	Hibbi Iqbal	—	Approve	[Fill Here]
5	Submit Payment Files with Sufficient Lead Time for Screening	—	Hibbi Iqbal	—	Approve	[Fill Here]
6	Develop Transparent Exemption Request Process for Payment Verification	—	Dylan Sachetti	—	Approve	[Fill Here]
7	Consolidate Core Financial Systems for CFO Act Agencies	—	Ayesha Ahsan	2025-09-21	Approve	[Fill Here]
8	Consolidate Transactional Financial Management for Non-CFO Agencies	—	Ayesha Ahsan	2025-09-21	Approve	[Fill Here]
9	Ensure Use of Standard Financial Management Solutions	—	Ayesha Ahsan	—	Approve	[Fill Here]
10	Assess and Revoke Delegated Disbursing Authority as Appropriate	—	Hibbi Iqbal	2025-04-24	Approve	[Fill Here]
11	Develop Plan to Centralize and Manage NTDO Payments	—	Ayesha Ahsan	—	Approve	[Fill Here]
12	Establish Transition Plan for NTDO Agencies	—	Ayesha Ahsan	—	Approve	[Fill Here]
13	Decommission Internal Payment Systems and Use Treasury Systems	—	Robert Springfiled	—	Approve	[Fill Here]
14	Submit Agency Compliance Plan to OMB Director	—	Dylan Sachetti	2025-06-23	Approve	[Fill Here]
15	Submit Implementation Report on EO Progress	—	Dylan Sachetti	2025-09-21	Approve	[Fill Here]
16	Protect Classified and Sensitive Information During Implementation	—	Robert Springfiled	—	Approve	[Fill Here]
', false, 'e8514019-182d-4197-a902-a054d4ab1da4', '2025-08-26 18:27:17.098177+00');
INSERT INTO public.email_logs VALUES ('a489df58-f85d-4800-b829-175e3db10e0e', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{Dylan.Sachetti@lumenlighthouse.ai}', 'Dear Dylan Sachetti,

You have been assigned 6 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: e8514019-182d-4197-a902-a054d4ab1da4
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Update Guidance and Enhance Payment Verification Systems
  Description: Update guidance and enhance systems to ensure all Treasury payments are subject to pre-certification verification, including compliance with Do Not Pay and other validation programs. Per Sec. 3(a).
  Due Date: TBD
  Status: approved

Task 2:
  Title: Review and Modify System of Records Notices for Routine Use
  Description: Review and modify relevant system of records notices under the Privacy Act to include a routine use for disclosure to Treasury for fraud prevention. Per Sec. 3(d).
  Due Date: 2025-06-23
  Status: approved

Task 3:
  Title: Issue Guidance on Data Access for Fraud Prevention
  Description: Issue guidance to agency heads on circumstances for providing Treasury with access to necessary data for fraud and improper payment detection. Per Sec. 3(e).
  Due Date: TBD
  Status: approved

Task 4:
  Title: Develop Transparent Exemption Request Process for Payment Verification
  Description: Develop and include a transparent process for agencies to request exemptions from payment verification requirements for specific payments. Per Sec. 4(e).
  Due Date: TBD
  Status: approved

Task 5:
  Title: Submit Agency Compliance Plan to OMB Director
  Description: Submit a compliance plan to the OMB Director within 90 days detailing strategy for transitioning disbursing authority, updating systems, verifying payment information, and reporting improper payments. Per Sec. 7(a).
  Due Date: 2025-06-23
  Status: approved

Task 6:
  Title: Submit Implementation Report on EO Progress
  Description: Submit an implementation report to the President within 180 days detailing progress on the EO’s directives. Per Sec. 7(b).
  Due Date: 2025-09-21
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, 'e8514019-182d-4197-a902-a054d4ab1da4', '2025-08-26 18:27:17.197552+00');
INSERT INTO public.email_logs VALUES ('e1cc21dd-2294-4c22-a15e-28d1bf767412', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{Hibbi.Iqbal@lumenlighthouse.ai}', 'Dear Hibbi Iqbal,

You have been assigned 3 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: e8514019-182d-4197-a902-a054d4ab1da4
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Implement Pre-Certification Payment Verification Requirements
  Description: Ensure compliance with Treasury-issued disbursement and pre-certification requirements, including verification of payment information and supporting documentation. Per Sec. 4(a)-(b).
  Due Date: TBD
  Status: approved

Task 2:
  Title: Submit Payment Files with Sufficient Lead Time for Screening
  Description: Submit payment files to Treasury with sufficient lead time for fraud and improper payment screening, except for same-day payments which should be submitted as early as practicable. Per Sec. 4(c).
  Due Date: TBD
  Status: approved

Task 3:
  Title: Assess and Revoke Delegated Disbursing Authority as Appropriate
  Description: Assess whether to maintain or revoke delegated disbursing authority to agencies and issue revocation notices as appropriate. Per Sec. 6(a).
  Due Date: 2025-04-24
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, 'e8514019-182d-4197-a902-a054d4ab1da4', '2025-08-26 18:27:17.21522+00');
INSERT INTO public.email_logs VALUES ('4509bac4-e347-4a9f-a2b8-7985ad44c410', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{Ayesha.Ahsan@lumenlighthouse.ai}', 'Dear Ayesha Ahsan,

You have been assigned 5 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: e8514019-182d-4197-a902-a054d4ab1da4
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Consolidate Core Financial Systems for CFO Act Agencies
  Description: Issue and implement guidance for CFO Act agencies to consolidate their core financial systems. Per Sec. 5(a).
  Due Date: 2025-09-21
  Status: approved

Task 2:
  Title: Consolidate Transactional Financial Management for Non-CFO Agencies
  Description: Issue and implement guidance for non-CFO Act agencies to consolidate transactional financial management services under a single Treasury-approved provider. Per Sec. 5(b).
  Due Date: 2025-09-21
  Status: approved

Task 3:
  Title: Ensure Use of Standard Financial Management Solutions
  Description: Ensure all CFO Act agencies use standard financial management solutions available through the Financial Management Marketplace. Per Sec. 5(c).
  Due Date: TBD
  Status: approved

Task 4:
  Title: Develop Plan to Centralize and Manage NTDO Payments
  Description: Develop a plan to centralize and manage all payments previously disbursed by NTDOs, ensuring seamless continuity of government payments. Per Sec. 6(d).
  Due Date: TBD
  Status: approved

Task 5:
  Title: Establish Transition Plan for NTDO Agencies
  Description: Establish a transition plan for agencies currently operating as NTDOs, including staffing, system integrations, and legal/regulatory modifications for consolidation. Per Sec. 6(e).
  Due Date: TBD
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, 'e8514019-182d-4197-a902-a054d4ab1da4', '2025-08-26 18:27:17.236401+00');
INSERT INTO public.email_logs VALUES ('45ec1027-da78-4a1b-8fc7-d6f04d63c8d1', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{Robert.Springfiled@lumenlighthouse.ai}', 'Dear Robert Springfiled,

You have been assigned 2 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: e8514019-182d-4197-a902-a054d4ab1da4
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Decommission Internal Payment Systems and Use Treasury Systems
  Description: Decommission all internal payment systems and transition to using Treasury’s disbursement systems, except as otherwise authorized. Per Sec. 6(f).
  Due Date: TBD
  Status: approved

Task 2:
  Title: Protect Classified and Sensitive Information During Implementation
  Description: Take all necessary steps to protect classified information, personally identifiable information, and tax return information during EO implementation. Per Sec. 7(c).
  Due Date: TBD
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, 'e8514019-182d-4197-a902-a054d4ab1da4', '2025-08-26 18:27:17.251345+00');


--
-- Data for Name: attachments; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.users VALUES ('893b3c9a-1bf3-41b1-892c-3f0e01a49c1c', 'Micheal Kim', 'Micheal.Kim@lumenlighthouse.ai', 'executor', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Director of Travel Management', '$2b$12$fRIm.x.bg/ER1HAWklxXLOssfaBM2n.QX7ydsPbByU8yLefFlPPci');
INSERT INTO public.users VALUES ('19989f97-e3e9-437c-a5a8-8cc8b36fa387', 'Zacira Copper', 'Zacira.Copper@lumenlighthouse.ai', 'executor', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Supervisor (reports to Ayesha)', '$2b$12$8m3dCMWHjD8XNOBmBfxb4.PSCetyYUHIVD9tW6xszwQVD4zbLj6EG');
INSERT INTO public.users VALUES ('0e9dcef9-695c-4441-aa25-2f32f31b476f', 'Jada Mccray', 'Jada.Mccray@lumenlighthouse.ai', 'executor', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Lead Accountant (Reports to Zacira)', '$2b$12$amGYHh8q3olfLYzsSAqAWOMcA2Ysiin7ayT49MudMNvMutWGn7tFi');
INSERT INTO public.users VALUES ('abbc0c86-6da1-480e-9cc4-c368a3ce0f08', 'Jose Flores', 'Jose.Flores@lumenlighthouse.ai', 'executor', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Lead Accountant (Reports to Zacira)', '$2b$12$PAO1ncB/vUetJpvOHhTjI.mGncU8TVBwRG8uDxL8XOCkTsVWNhAR6');
INSERT INTO public.users VALUES ('71002888-89e3-46af-a9bb-a1a41d41e761', 'EO 14249 Email', 'EO.14249@lumenlighthouse.ai', 'reviewer', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'EO 14249 Email', '$2b$12$U73ON2P4ghYYIRJ53JqqCeBPEhtBLr3SKlQg6Pd3fI5ubp.EI7Pge');
INSERT INTO public.users VALUES ('464fdb46-dacb-43f3-8cde-f0b5acfde376', 'EO 14247 Email', 'EO.14247@lumenlighthouse.ai', 'reviewer', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'EO 14247 Email', '$2b$12$2GER8IZ1pP/75eROTDFbj.YPJvGg78spwgimEWkthUtGlBapuFN/u');
INSERT INTO public.users VALUES ('fab9cb31-f6ed-4a65-bedc-34da95783dd1', 'Sarah Johnson', 'sarah.johnson@lumenlighthouse.ai', 'reviewer', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Senior Project Manager', '$2b$12$QsdrHfwrVgCQAr5dT22oO.iwT4exEybjyi1cUCc3/32MzuV5NhDue');
INSERT INTO public.users VALUES ('02a5a667-2ca8-4f30-97ef-8daadd8322f1', 'David Chen', 'david.chen@lumenlighthouse.ai', 'reviewer', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Compliance Manager', '$2b$12$ELLvyp14AXbYv88spWm1HeGnscNvoANpU22VzU6uVhxCfdQHA6mOW');
INSERT INTO public.users VALUES ('c962e3d8-f3af-4d98-91e5-793826891329', 'Maria Rodriguez', 'maria.rodriguez@lumenlighthouse.ai', 'reviewer', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Financial Operations Manager', '$2b$12$fb8Inms/Wg3ThPnTMO.iEe64MlGieSO.VsRYKzQbIj5/5DjaaGeVS');
INSERT INTO public.users VALUES ('2aedc3eb-db84-4419-a07c-0072ec1f16eb', 'Jack Smith', 'jack.smith@lumenlighthouse.ai', 'admin', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'CFO', '$2b$12$B4Z26hnRBW30aXlIcvnL9u3RuOMb0QHVkGe8vGvTevV1qz8OQBlzm');
INSERT INTO public.users VALUES ('a66ae39c-2ff7-407d-a51a-c36cb161a53d', 'Kevin Brown', 'Kevin.Brown@lumenlighthouse.ai', 'admin', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Deputy CFO', '$2b$12$2EmByE/sElmjD5hhC99QuuRPhr6iMOXOv/iMcS4JLcFjgf4wVSP7i');
INSERT INTO public.users VALUES ('405cdfc8-b68d-4ea9-a0ff-76862e077005', 'Westley Everette', 'Westley.Everette@lumenlighthouse.ai', 'admin', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Associate Deputy CFO', '$2b$12$6VKyazOHVcMcU5vwnP1OO.33h.J0nkpe7Y9tKhh/y0X8eaDR.aoka');
INSERT INTO public.users VALUES ('e743d07a-9cbc-4073-837e-721880ad6ecc', 'Dylan Sachetti', 'Dylan.Sachetti@lumenlighthouse.ai', 'executor', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Director of Compliance', '$2b$12$enxg5uAs9g5Jcp.EhLbuJujXMFvLSn2jYPOSWxCoVqTGfaVupUkRe');
INSERT INTO public.users VALUES ('fb935a51-8356-440a-9afa-6218df6c14a2', 'Ayesha Ahsan', 'Ayesha.Ahsan@lumenlighthouse.ai', 'executor', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Director of Division of Business Process Improvement', '$2b$12$Ve8JbqzwPRnKU7hPfwBLIurtehLA2qlRj/ZuyOttO1e73EQ/tSMVm');
INSERT INTO public.users VALUES ('d0630e23-53c1-4be3-96f9-f55e08b94f52', 'Hibbi Iqbal', 'Hibbi.Iqbal@lumenlighthouse.ai', 'executor', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Director of Financial Reporting', '$2b$12$dd29riAI5vn2aN6mkz5aMuLyW9EwNhbBIem2ltLJfVVcphPbu1lXS');
INSERT INTO public.users VALUES ('45416f04-2c1c-40d0-b248-4305ea8704a8', 'Sophia Carty', 'Sophia.Carty@lumenlighthouse.ai', 'executor', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Director of Accounting', '$2b$12$cJSLSufoFlgoPlFNn5ckoeP818a3eIEqbc8pZ.ve2sKZNxjPpMeku');
INSERT INTO public.users VALUES ('2f4d19c0-1ce5-49fe-ba0c-2ce452f76c8a', 'Robert Springfiled', 'Robert.Springfiled@lumenlighthouse.ai', 'executor', true, '2025-08-26 18:17:41.782838+00', '2025-08-26 18:17:41.782838+00', 'Director of Security and Technology', '$2b$12$6xKnNQfj0.memyKcvd2fw.tQx07aHOQj8PGLsnpTUNuOnLyq0V3qK');


--
-- Data for Name: auth_tokens; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.tasks VALUES ('35427c2b-a353-4a1d-94b2-954f9925e88a', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Update Guidance and Enhance Payment Verification Systems', 'Update guidance and enhance systems to ensure all Treasury payments are subject to pre-certification verification, including compliance with Do Not Pay and other validation programs. Per Sec. 3(a).', 'e743d07a-9cbc-4073-837e-721880ad6ecc', 'approved', NULL, '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Compliance', 'N/A');
INSERT INTO public.tasks VALUES ('2db11230-a22b-4d9c-8954-cd9b1059d20a', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Review and Modify System of Records Notices for Routine Use', 'Review and modify relevant system of records notices under the Privacy Act to include a routine use for disclosure to Treasury for fraud prevention. Per Sec. 3(d).', 'e743d07a-9cbc-4073-837e-721880ad6ecc', 'approved', '2025-06-23', '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Compliance', 'N/A');
INSERT INTO public.tasks VALUES ('8750a86e-b9e9-4abc-ba9a-3717fbd5fa83', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Issue Guidance on Data Access for Fraud Prevention', 'Issue guidance to agency heads on circumstances for providing Treasury with access to necessary data for fraud and improper payment detection. Per Sec. 3(e).', 'e743d07a-9cbc-4073-837e-721880ad6ecc', 'approved', NULL, '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Compliance', 'N/A');
INSERT INTO public.tasks VALUES ('ca0999a8-41c6-4f8a-9008-7b925e8c9b4d', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Implement Pre-Certification Payment Verification Requirements', 'Ensure compliance with Treasury-issued disbursement and pre-certification requirements, including verification of payment information and supporting documentation. Per Sec. 4(a)-(b).', 'd0630e23-53c1-4be3-96f9-f55e08b94f52', 'approved', NULL, '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Financial Reporting', 'N/A');
INSERT INTO public.tasks VALUES ('81bab07f-bc6a-41da-bb55-5fc0a34b284a', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Submit Payment Files with Sufficient Lead Time for Screening', 'Submit payment files to Treasury with sufficient lead time for fraud and improper payment screening, except for same-day payments which should be submitted as early as practicable. Per Sec. 4(c).', 'd0630e23-53c1-4be3-96f9-f55e08b94f52', 'approved', NULL, '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Financial Reporting', 'N/A');
INSERT INTO public.tasks VALUES ('12238978-2dd2-48a7-b4a1-cee1efbc7d3d', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Develop Transparent Exemption Request Process for Payment Verification', 'Develop and include a transparent process for agencies to request exemptions from payment verification requirements for specific payments. Per Sec. 4(e).', 'e743d07a-9cbc-4073-837e-721880ad6ecc', 'approved', NULL, '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Compliance', 'N/A');
INSERT INTO public.tasks VALUES ('bf14fe00-7414-4e58-adce-319860fabe4d', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Consolidate Core Financial Systems for CFO Act Agencies', 'Issue and implement guidance for CFO Act agencies to consolidate their core financial systems. Per Sec. 5(a).', 'fb935a51-8356-440a-9afa-6218df6c14a2', 'approved', '2025-09-21', '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Division of Business Process Improvement', 'N/A');
INSERT INTO public.tasks VALUES ('045c36ae-595d-4775-94be-ae08ab515fd2', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Consolidate Transactional Financial Management for Non-CFO Agencies', 'Issue and implement guidance for non-CFO Act agencies to consolidate transactional financial management services under a single Treasury-approved provider. Per Sec. 5(b).', 'fb935a51-8356-440a-9afa-6218df6c14a2', 'approved', '2025-09-21', '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Division of Business Process Improvement', 'N/A');
INSERT INTO public.tasks VALUES ('fe65d0f7-ff10-40dd-a675-4e260f1dfa1c', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Ensure Use of Standard Financial Management Solutions', 'Ensure all CFO Act agencies use standard financial management solutions available through the Financial Management Marketplace. Per Sec. 5(c).', 'fb935a51-8356-440a-9afa-6218df6c14a2', 'approved', NULL, '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Division of Business Process Improvement', 'N/A');
INSERT INTO public.tasks VALUES ('cea6e66b-9343-4537-aedd-de77ccdb8628', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Assess and Revoke Delegated Disbursing Authority as Appropriate', 'Assess whether to maintain or revoke delegated disbursing authority to agencies and issue revocation notices as appropriate. Per Sec. 6(a).', 'd0630e23-53c1-4be3-96f9-f55e08b94f52', 'approved', '2025-04-24', '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Financial Reporting', 'N/A');
INSERT INTO public.tasks VALUES ('f9795788-34c5-4e18-9f91-9ee18165a16d', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Develop Plan to Centralize and Manage NTDO Payments', 'Develop a plan to centralize and manage all payments previously disbursed by NTDOs, ensuring seamless continuity of government payments. Per Sec. 6(d).', 'fb935a51-8356-440a-9afa-6218df6c14a2', 'approved', NULL, '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Division of Business Process Improvement', 'N/A');
INSERT INTO public.tasks VALUES ('571cee99-7d46-4844-ac39-093da1f2ab93', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Establish Transition Plan for NTDO Agencies', 'Establish a transition plan for agencies currently operating as NTDOs, including staffing, system integrations, and legal/regulatory modifications for consolidation. Per Sec. 6(e).', 'fb935a51-8356-440a-9afa-6218df6c14a2', 'approved', NULL, '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Division of Business Process Improvement', 'N/A');
INSERT INTO public.tasks VALUES ('ed1ac6bb-959f-4e24-a59d-10a444a3cb26', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Decommission Internal Payment Systems and Use Treasury Systems', 'Decommission all internal payment systems and transition to using Treasury’s disbursement systems, except as otherwise authorized. Per Sec. 6(f).', '2f4d19c0-1ce5-49fe-ba0c-2ce452f76c8a', 'approved', NULL, '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Security and Technology', 'N/A');
INSERT INTO public.tasks VALUES ('7e0b82dd-53e1-4efa-b549-58ccc6550114', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Submit Agency Compliance Plan to OMB Director', 'Submit a compliance plan to the OMB Director within 90 days detailing strategy for transitioning disbursing authority, updating systems, verifying payment information, and reporting improper payments. Per Sec. 7(a).', 'e743d07a-9cbc-4073-837e-721880ad6ecc', 'approved', '2025-06-23', '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Compliance', 'N/A');
INSERT INTO public.tasks VALUES ('65ae22ba-8df3-4a5f-8b6c-4385dc5280ca', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Submit Implementation Report on EO Progress', 'Submit an implementation report to the President within 180 days detailing progress on the EO’s directives. Per Sec. 7(b).', 'e743d07a-9cbc-4073-837e-721880ad6ecc', 'approved', '2025-09-21', '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Compliance', 'N/A');
INSERT INTO public.tasks VALUES ('5782577b-7239-4158-aa60-ecf6433495d3', 'e8514019-182d-4197-a902-a054d4ab1da4', 'Protect Classified and Sensitive Information During Implementation', 'Take all necessary steps to protect classified information, personally identifiable information, and tax return information during EO implementation. Per Sec. 7(c).', '2f4d19c0-1ce5-49fe-ba0c-2ce452f76c8a', 'approved', NULL, '2025-08-26 18:18:58.176533+00', '2025-08-26 18:27:17.157503+00', 'Director of Security and Technology', 'N/A');


--
-- Data for Name: daily_updates; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: eo_pmo_assignments; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: task_confirmations; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: task_logs; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: token_blacklist; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.token_blacklist VALUES ('677b9cc6-52af-444c-95ee-f1b8935984bd', 'db4345184a8a409d44911deadb6c17578ae8da3d282ae3b9720fc16f8fe554ef', 'dcd920f0-6e8c-4f01-a67c-bc0ce415a7ac', '2025-08-25 16:41:36+00', '2025-08-25 16:11:43.597326+00');


--
-- PostgreSQL database dump complete
--

\unrestrict tAplqhac0BrrBtZHd63lYXYLvVLYqmJVmBmXPTuvXlj1jdoNXrpbRMnMUdGyTFh

