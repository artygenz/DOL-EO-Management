--
-- PostgreSQL database dump
--

\restrict IDjWHO99LPzcPgErO8X3KkCx9tc28OsMjlyDfPRTDe6Vbeqd1agT1LseM9MoOkb

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

INSERT INTO public.alembic_version VALUES ('bbe85c9252e4');


--
-- Data for Name: executive_orders; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.executive_orders VALUES ('4079e80f-781b-44ed-a759-527f97ef87f5', 'EO - Digital Transformation', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', 'westley.everette@lumenlighthouse.ai', '2025-08-29 18:08:51.823537+00', NULL, 'error', '2025-08-29 18:08:51.840504+00', '2025-08-29 18:08:51.845023+00', '<aeede9de-89b3-4dce-a511-5bb9270c5725@example.com>');
INSERT INTO public.executive_orders VALUES ('8fd95066-1662-4482-b1f8-3801f037f356', 'EO: Modernize Workforce Data', 'Presidential ActionsProtecting America’s Bank Account Against Fraud, Waste, and AbuseExecutive OrdersMarch 25, 2025 By the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered:Section 1. Purpose.  Promoting financial integrity and operational efficiency are critical responsibilities of the Federal Government.  The Federal Government processes trillions of dollars annually in disbursements to individuals, businesses, and organizations, and in receipts from taxes, fees, and other payments to finance daily and long-term Government operations.  These transactions flow into and out of the United States General Fund (General Fund), which might be thought of as America’s bank account.  In Fiscal Year 2024, $33.9 trillion flowed into the General Fund and $33.6 trillion flowed out of the account, including $5.87 trillion (less net interest) in benefits, grants, loans, vendor payments, and other disbursements. The Department of the Treasury is the largest financial payment manager of the Federal Government and is responsible for safeguarding the General Fund, but lacks sufficient controls to track transactions flowing through the General Fund to determine if they were proper.  To enforce sufficient controls and ensure accountability to American taxpayers, the Department of the Treasury requires financial information from executive departments and agencies (agencies) beyond what they currently provide.Financial fraud threatens the integrity of Federal programs and undermines trust in Government.  Agencies’ past underinvestment in technology and longstanding challenges with access to accurate data has prevented them from more fully safeguarding taxpayer dollars against fraud and improper payments.  The Government Accountability Office estimates that the Federal Government loses between $233 and $521 billion annually to fraud.In addition to being an efficient steward of taxpayer funds, the Federal Government, on behalf of the American public, must seek to ensure that financial information is accurate and that there is transparency with respect to how taxpayer dollars are being used.  Today, Federal funds are disbursed both by the Department of the Treasury and various Federal Government entities that are authorized to issue their own disbursements known as Non-Treasury Disbursing Offices (NTDOs).  In Fiscal Year 2024, NTDOs were estimated to be responsible for 181 million payments totaling over $1.5 trillion (approximately 22 percent of all Federal Government dollars disbursed). This fragmentation of disbursing authority, together with the proliferation of non-standard financial management systems across the Federal Government, leads to expensive, disjointed, and duplicative financial reporting, lack of financial traceability, complicated financial management, opacity, increased operational risks, and decreased ability of the Department of the Treasury to provide centralized oversight.This order promotes financial integrity by enabling the Department of the Treasury to more easily conduct improper payment and fraud prevention screening prior to disbursing funds on behalf of agencies.  This order increases transparency and accountability by requiring agencies to provide the Department of the Treasury with the information needed to track transactions through the General Fund in greater detail.  This order also promotes operational efficiency by returning disbursing functions to the Department of the Treasury when possible and consolidating and standardizing core Federal financial systems.Sec. 2.  Policy.  It is the policy of the United States to defend against financial fraud and improper payments, increase transparency and accountability around the Federal Government’s operations and financial condition, increase efficiency, reduce costs, and enhance the security of Federal payments.Sec. 3.  Treasury Verification of Agency Payments Information.  (a)  The Secretary of the Treasury, in consultation with the Director of the Office of Management and Budget (OMB Director), shall update guidance and enhance systems to ensure that all payments made by the Department of the Treasury on behalf of agencies pursuant to the Secretary of the Treasury’s disbursing authority, including 31 U.S.C. 3321, are subject to pre-certification verification processes established by the Secretary of the Treasury and conducted by agencies and the Department of the Treasury for the purposes of defending against financial fraud and improper payments, to the greatest extent permitted by law.  Such guidance shall set forth guidelines for compliance with the Do Not Pay Working System as described in 31 U.S.C. 3351 et seq., and such other payment, account, and payee validation programs and services that the Secretary of the Treasury and the OMB Director determine to be beneficial for reducing financial fraud and improper payments.(b)  In accordance with 31 U.S.C. 3354, the heads of all agencies shall cooperate with the Secretary of the Treasury to fulfill their obligations to determine payment or award eligibility through pre-certification and pre-award procedures, as determined by the Secretary of the Treasury, including pursuant to subsection (a) of this section and section 4 of this order to prevent fraud and improper payments.(c)  The Secretary of the Treasury is directed to minimize administrative barriers to accessing and using data to prevent fraud and improper payments by exercising the authority in 31 U.S.C. 3351 et seq. to waive the requirements of 5 U.S.C. 552a(o), in consultation with the OMB Director, in any case or class of cases for computer matching activities, to the extent permissible by law.(d)  Within 90 days of the date of this order, agency heads shall review and modify, as applicable, their relevant system of records notices under the Privacy Act of 1974 to include a “routine use” that allows for the disclosure of records to the Department of the Treasury for the purposes of identifying, preventing, or recouping fraud and improper payments, to the extent permissible by law. (e)  The Secretary of the Treasury, in consultation with the OMB Director, shall issue guidance to agency heads on the circumstances in which agency heads, to the extent permissible by law, may provide the Secretary of the Treasury with access to data necessary for the purposes of detecting and preventing fraud and improper payments, as well as data for payment information verification (and not, for example, data such as health records).Sec. 4.  Implementation and Compliance of Payment Verification.  (a)  Agency heads, through designated agency officials (Certifying Officers or COs), who are responsible for verifying that disbursements made by the Federal Government are legal, proper, and correct, and for performing the duties in 31 U.S.C. 3528, shall comply with the disbursement requirements and instructions, including pre-certification requirements, published by the Secretary of the Treasury.(b)  The Secretary of the Treasury shall consider, as appropriate, issuing instructions to agencies to enforce the following pre-certification criteria for disbursement requests submitted by COs (Vouchers) before they are certified for payment by the CO:(i)     Funds are available at the time the obligation is incurred.  If an obligation is incurred when funds are not available, then the CO shall not certify the payment.(ii)    The amount of the payment and the name of the payee on the Voucher are correct, in conformance with the Department of the Treasury’s prescribed standard format.(iii)   A proper Social Security Number, Taxpayer Identification Number, Employer Identification Number, Individual Taxpayer Identification Number, or Payee ID Number is provided for each payee on the Voucher, as applicable.(iv)    The appropriation or fund from which the payment will be made is available for the purpose set forth in the Voucher and indicated with the appropriate Treasury Account Symbol/Business Event Type Code.(v)     Payees are not deceased individuals, to the greatest extent permitted by law.(vi)    The account number provided on the Voucher is held at a financial institution and is open, valid, and belongs to the payee or valid designee of payee.(vii)   Contracts or agreements are referenced on the Voucher by providing the contract number, referred to as the Procurement Instrument Identifier, where applicable.(viii)  Financial assistance awards (non-aggregate) are referenced on the Voucher by providing the award number, referred to as the Federal Award Identification Number, where applicable.(ix)    For summary schedules, the payments on the Voucher are submitted in conformance with the Department of the Treasury prescribed standard formats for such schedules.(c)  Agency heads shall submit payment files other than with respect to same-day payments to the Secretary of the Treasury or the Secretary’s designee with sufficient lead time prior to the date of disbursement as determined by the Department of the Treasury and provided in the requirements and instructions issued pursuant to subsections (a) and (b) of this section, to allow for fraud and improper payment screening, to the extent permissible by law.  With respect to same-day payments, agency heads shall submit payment files to the Secretary of the Treasury or the Secretary’s designee as much in advance as reasonably practicable.(d)  In issuing requirements and instructions pursuant to subsection (a) of this section, the Secretary of the Treasury shall consider whether it would be appropriate to provide that the Department of the Treasury’s Chief Disbursing Officer return to the relevant agency for reconciliation any payments that do not pass the pre-certification verification processes established pursuant to section 3(a) of this order and notify the designated CO.  (e)  The Secretary of the Treasury shall include in the guidance issued pursuant to subsection (a) of this section, or in other regulations or guidance, a transparent process for agencies to request exemptions from some or all of the payment verification requirements for specific payments or categories of payments.Sec. 5.  Core Financial System Consolidation.  (a)  Within 180 days of the date of this order, the OMB Director shall issue guidance that directs agencies described in 31 U.S.C. 901(b) (CFO Act agencies) to consolidate their core financial systems.(b)  As soon as practicable, but not later than 180 days of the date of this order, the OMB Director, in consultation with the Secretary of the Treasury, shall issue guidance directing all non-CFO Act agencies to consolidate transactional financial management services under a single provider approved by the Department of the Treasury.(c)  As soon as practicable, all heads of CFO Act agencies shall use standard financial management solutions available through the Financial Management Marketplace, administered by the Financial Management Quality Service Management Office.(d)  Agency heads shall ensure that core financial systems comply with Federal accounting and financial reporting standards and relevant regulations, orders, guidance documents, policy statements, and other agency actions published by the Department of the Treasury from time to time.Sec. 6.  Reduction of NTDOs.  (a)  Within 30 days of the date of this order, the Secretary of the Treasury shall assess whether to maintain disbursing authority that it has delegated to agencies pursuant to 31 U.S.C. 3321(b) and issue notices to revoke such delegations, as appropriate, in accordance with applicable law.  (b)  The heads of agencies with disbursing authority under 31 U.S.C. 3321(c), including the Secretary of Defense, the Secretary of Homeland Security, and the Attorney General (but excluding, for the avoidance of doubt, the Supreme Court and other entities of the Federal Government outside the Executive Branch) will work with the Secretary of the Treasury to delegate the performance of their disbursing activities, other than with respect to classified payments, to the Department of the Treasury’s Chief Disbursing Officer in accordance with applicable law. (c)  Notwithstanding subsections (a) or (b) of this section, the Secretary of the Treasury may continue to delegate disbursing authority to NTDOs at other agencies when doing so would align with significant Government priorities.  Any remaining NTDOs are required to report daily to the Department of the Treasury’s centralized accounting and reporting system in accordance with then-current Department of the Treasury guidance and applicable law.(d)  The Secretary of the Treasury shall develop a plan to centralize and manage all payments previously disbursed by NTDOs, ensuring seamless continuity of Government payments.(e)  The Secretary of the Treasury, in coordination with agency heads, shall establish a transition plan for agencies currently operating as NTDOs, including staffing adjustments, system integrations, and legal or regulatory modifications necessary for full consolidation.(f)  The heads of agencies with disbursing authority delegated to the agency under 33 U.S.C. 3321(b) shall decommission all internal payment systems and use the Department of the Treasury’s disbursement systems, except and to the extent authorized by the Department of the Treasury or otherwise required by applicable law.Sec. 7.  Reporting and Implementation Requirements.  (a)  The heads of all agencies shall submit a compliance plan to the OMB Director within 90 days of the date of this order detailing their strategy for:(i)    transitioning disbursing authority to the Department of the Treasury, as applicable and as contemplated by this order;(ii)   updating and integrating systems with Department of the Treasury platforms;(iii)  procedures to verify payment information as contemplated by this order; and(iv)   transmitting information associated with improper payments to the Department of the Treasury in accordance with standards and reporting specifications established by the OMB Director in coordination with the Secretary of the Treasury as contemplated by this order.(b)  The Secretary of the Treasury shall submit an implementation report to the President through the Assistant to the President for Economic Policy within 180 days of the date of this order detailing progress on the matters set forth in this order.(c)  The Secretary of the Treasury and agency heads shall take all necessary steps to protect classified information and systems, as well as personally identifiable information and tax return information, through the implementation of this order.Sec. 8.  General Provisions.  (a)  Nothing in this order shall be construed to impair or otherwise affect:(i)   the authority granted by law to an executive department or agency, or the head thereof; or(ii)  the functions of the Director of the Office of Management and Budget relating to budgetary, administrative, or legislative proposals.(b)  This order shall be implemented consistent with applicable law and subject to the availability of appropriations.(c)  This order is not intended to, and does not, create any right or benefit, substantive or procedural, enforceable at law or in equity by any party against the United States, its departments, agencies, or entities, its officers, employees, or agents, or any other person.DONALD J. TRUMPTHE WHITE HOUSE,    March 25, 2025.# Newline-delimited ROLES catalog used by the LLM to set category_dept (verbatim when possible).ROLES_DEMO = Secretary of the Treasury (in consultation with OMB Director)All Agency HeadsSecretary of the TreasuryAgency Heads / Certifying OfficersSecretary of the Treasury & Agency Certifying OfficersOMB DirectorOMB Director (in consultation with Secretary of the Treasury)CFO Act Agency HeadsHeads of agencies with disbursing authority under 31 U.S.C. 3321(c) (e.g., DoD, DHS, DOJ) + Secretary of the TreasurySecretary of the Treasury & NTDOs remaining after consolidation processSecretary of the Treasury (in coordination with agency heads)Agency Heads with authority under 31 U.S.C. 3321(b)', 'sec@agency.gov', '2025-08-13 15:00:00+00', NULL, 'error', '2025-08-28 19:15:30.705092+00', '2025-08-28 19:15:30.711016+00', 'msg-2001@sample');
INSERT INTO public.executive_orders VALUES ('ccae689f-6842-4b82-a745-19d5d7e0c659', 'EO - Digital Transformation', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', 'westley.everette@lumenlighthouse.ai', '2025-08-29 18:03:01.805171+00', NULL, 'error', '2025-08-29 18:03:02.014919+00', '2025-08-29 18:03:02.038947+00', '<11607f1d-30d6-40a1-90a8-2062af44df29@example.com>');
INSERT INTO public.executive_orders VALUES ('b8cd1182-41f6-4c38-a3b3-02e0d7e99c84', 'EO - Digital Transformation Initiative', 'Executive Order for Digital Transformation Initiative

This executive order outlines the digital transformation requirements for the Department of Labor.

Key directives:
1. Implement new reporting systems
2. Update documentation
3. Conduct security reviews

Please process this executive order and create appropriate tasks.', 'westley.everette@lumenlighthouse.ai', '2025-08-29 18:03:01.068537+00', NULL, 'error', '2025-08-29 18:03:02.022971+00', '2025-08-29 18:03:02.036999+00', '<0ed8e961-09d0-4ee4-b216-166571587e2b@example.com>');


--
-- Data for Name: email_logs; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.email_logs VALUES ('a4d4141a-95f0-46c4-858e-f91d9855ebc5', 'incoming', 'Mail delivery failed: returning message to sender', 'Mailer-Daemon@p3plzcpnl492179.prod.phx3.secureserver.net', '{eo.14249@lumenlighthouse.ai}', 'This message was created automatically by mail delivery software.

A message that you sent could not be delivered to one or more of its
recipients. This is a permanent error. The following address(es) failed:

  test@example.com
    host p3nlsmtpcp01-v01.prod.phx3.secureserver.net [132.148.124.48]
    SMTP error from remote mail server after RCPT TO:<test@example.com>:
    550 5.1.1 <test@example.com> recipient rejected. This is a default recipient used as a placeholder in many web applications. Please check your settings and try again.
Direct SMTP test to test@example.com
', true, NULL, '2025-08-28 19:05:46.570185+00');
INSERT INTO public.email_logs VALUES ('c64323b7-0677-4a2a-9d19-9e2b78b16426', 'incoming', 'Mail delivery failed: returning message to sender', 'Mailer-Daemon@p3plzcpnl492179.prod.phx3.secureserver.net', '{eo.14249@lumenlighthouse.ai}', 'This message was created automatically by mail delivery software.

A message that you sent could not be delivered to one or more of its
recipients. This is a permanent error. The following address(es) failed:

  test@example.com
    host p3nlsmtpcp01-v01.prod.phx3.secureserver.net [132.148.124.48]
    SMTP error from remote mail server after RCPT TO:<test@example.com>:
    550 5.1.1 <test@example.com> recipient rejected. This is a default recipient used as a placeholder in many web applications. Please check your settings and try again.
This is the final verification test for email sending.
', true, NULL, '2025-08-28 19:15:04.842531+00');
INSERT INTO public.email_logs VALUES ('4f714c62-8509-4f63-b370-295445ce2d6f', 'incoming', 'EO: Modernize Workforce Data', 'sec@agency.gov', '{ops@dol.gov}', 'Presidential ActionsProtecting America’s Bank Account Against Fraud, Waste, and AbuseExecutive OrdersMarch 25, 2025 By the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered:Section 1. Purpose.  Promoting financial integrity and operational efficiency are critical responsibilities of the Federal Government.  The Federal Government processes trillions of dollars annually in disbursements to individuals, businesses, and organizations, and in receipts from taxes, fees, and other payments to finance daily and long-term Government operations.  These transactions flow into and out of the United States General Fund (General Fund), which might be thought of as America’s bank account.  In Fiscal Year 2024, $33.9 trillion flowed into the General Fund and $33.6 trillion flowed out of the account, including $5.87 trillion (less net interest) in benefits, grants, loans, vendor payments, and other disbursements. The Department of the Treasury is the largest financial payment manager of the Federal Government and is responsible for safeguarding the General Fund, but lacks sufficient controls to track transactions flowing through the General Fund to determine if they were proper.  To enforce sufficient controls and ensure accountability to American taxpayers, the Department of the Treasury requires financial information from executive departments and agencies (agencies) beyond what they currently provide.Financial fraud threatens the integrity of Federal programs and undermines trust in Government.  Agencies’ past underinvestment in technology and longstanding challenges with access to accurate data has prevented them from more fully safeguarding taxpayer dollars against fraud and improper payments.  The Government Accountability Office estimates that the Federal Government loses between $233 and $521 billion annually to fraud.In addition to being an efficient steward of taxpayer funds, the Federal Government, on behalf of the American public, must seek to ensure that financial information is accurate and that there is transparency with respect to how taxpayer dollars are being used.  Today, Federal funds are disbursed both by the Department of the Treasury and various Federal Government entities that are authorized to issue their own disbursements known as Non-Treasury Disbursing Offices (NTDOs).  In Fiscal Year 2024, NTDOs were estimated to be responsible for 181 million payments totaling over $1.5 trillion (approximately 22 percent of all Federal Government dollars disbursed). This fragmentation of disbursing authority, together with the proliferation of non-standard financial management systems across the Federal Government, leads to expensive, disjointed, and duplicative financial reporting, lack of financial traceability, complicated financial management, opacity, increased operational risks, and decreased ability of the Department of the Treasury to provide centralized oversight.This order promotes financial integrity by enabling the Department of the Treasury to more easily conduct improper payment and fraud prevention screening prior to disbursing funds on behalf of agencies.  This order increases transparency and accountability by requiring agencies to provide the Department of the Treasury with the information needed to track transactions through the General Fund in greater detail.  This order also promotes operational efficiency by returning disbursing functions to the Department of the Treasury when possible and consolidating and standardizing core Federal financial systems.Sec. 2.  Policy.  It is the policy of the United States to defend against financial fraud and improper payments, increase transparency and accountability around the Federal Government’s operations and financial condition, increase efficiency, reduce costs, and enhance the security of Federal payments.Sec. 3.  Treasury Verification of Agency Payments Information.  (a)  The Secretary of the Treasury, in consultation with the Director of the Office of Management and Budget (OMB Director), shall update guidance and enhance systems to ensure that all payments made by the Department of the Treasury on behalf of agencies pursuant to the Secretary of the Treasury’s disbursing authority, including 31 U.S.C. 3321, are subject to pre-certification verification processes established by the Secretary of the Treasury and conducted by agencies and the Department of the Treasury for the purposes of defending against financial fraud and improper payments, to the greatest extent permitted by law.  Such guidance shall set forth guidelines for compliance with the Do Not Pay Working System as described in 31 U.S.C. 3351 et seq., and such other payment, account, and payee validation programs and services that the Secretary of the Treasury and the OMB Director determine to be beneficial for reducing financial fraud and improper payments.(b)  In accordance with 31 U.S.C. 3354, the heads of all agencies shall cooperate with the Secretary of the Treasury to fulfill their obligations to determine payment or award eligibility through pre-certification and pre-award procedures, as determined by the Secretary of the Treasury, including pursuant to subsection (a) of this section and section 4 of this order to prevent fraud and improper payments.(c)  The Secretary of the Treasury is directed to minimize administrative barriers to accessing and using data to prevent fraud and improper payments by exercising the authority in 31 U.S.C. 3351 et seq. to waive the requirements of 5 U.S.C. 552a(o), in consultation with the OMB Director, in any case or class of cases for computer matching activities, to the extent permissible by law.(d)  Within 90 days of the date of this order, agency heads shall review and modify, as applicable, their relevant system of records notices under the Privacy Act of 1974 to include a “routine use” that allows for the disclosure of records to the Department of the Treasury for the purposes of identifying, preventing, or recouping fraud and improper payments, to the extent permissible by law. (e)  The Secretary of the Treasury, in consultation with the OMB Director, shall issue guidance to agency heads on the circumstances in which agency heads, to the extent permissible by law, may provide the Secretary of the Treasury with access to data necessary for the purposes of detecting and preventing fraud and improper payments, as well as data for payment information verification (and not, for example, data such as health records).Sec. 4.  Implementation and Compliance of Payment Verification.  (a)  Agency heads, through designated agency officials (Certifying Officers or COs), who are responsible for verifying that disbursements made by the Federal Government are legal, proper, and correct, and for performing the duties in 31 U.S.C. 3528, shall comply with the disbursement requirements and instructions, including pre-certification requirements, published by the Secretary of the Treasury.(b)  The Secretary of the Treasury shall consider, as appropriate, issuing instructions to agencies to enforce the following pre-certification criteria for disbursement requests submitted by COs (Vouchers) before they are certified for payment by the CO:(i)     Funds are available at the time the obligation is incurred.  If an obligation is incurred when funds are not available, then the CO shall not certify the payment.(ii)    The amount of the payment and the name of the payee on the Voucher are correct, in conformance with the Department of the Treasury’s prescribed standard format.(iii)   A proper Social Security Number, Taxpayer Identification Number, Employer Identification Number, Individual Taxpayer Identification Number, or Payee ID Number is provided for each payee on the Voucher, as applicable.(iv)    The appropriation or fund from which the payment will be made is available for the purpose set forth in the Voucher and indicated with the appropriate Treasury Account Symbol/Business Event Type Code.(v)     Payees are not deceased individuals, to the greatest extent permitted by law.(vi)    The account number provided on the Voucher is held at a financial institution and is open, valid, and belongs to the payee or valid designee of payee.(vii)   Contracts or agreements are referenced on the Voucher by providing the contract number, referred to as the Procurement Instrument Identifier, where applicable.(viii)  Financial assistance awards (non-aggregate) are referenced on the Voucher by providing the award number, referred to as the Federal Award Identification Number, where applicable.(ix)    For summary schedules, the payments on the Voucher are submitted in conformance with the Department of the Treasury prescribed standard formats for such schedules.(c)  Agency heads shall submit payment files other than with respect to same-day payments to the Secretary of the Treasury or the Secretary’s designee with sufficient lead time prior to the date of disbursement as determined by the Department of the Treasury and provided in the requirements and instructions issued pursuant to subsections (a) and (b) of this section, to allow for fraud and improper payment screening, to the extent permissible by law.  With respect to same-day payments, agency heads shall submit payment files to the Secretary of the Treasury or the Secretary’s designee as much in advance as reasonably practicable.(d)  In issuing requirements and instructions pursuant to subsection (a) of this section, the Secretary of the Treasury shall consider whether it would be appropriate to provide that the Department of the Treasury’s Chief Disbursing Officer return to the relevant agency for reconciliation any payments that do not pass the pre-certification verification processes established pursuant to section 3(a) of this order and notify the designated CO.  (e)  The Secretary of the Treasury shall include in the guidance issued pursuant to subsection (a) of this section, or in other regulations or guidance, a transparent process for agencies to request exemptions from some or all of the payment verification requirements for specific payments or categories of payments.Sec. 5.  Core Financial System Consolidation.  (a)  Within 180 days of the date of this order, the OMB Director shall issue guidance that directs agencies described in 31 U.S.C. 901(b) (CFO Act agencies) to consolidate their core financial systems.(b)  As soon as practicable, but not later than 180 days of the date of this order, the OMB Director, in consultation with the Secretary of the Treasury, shall issue guidance directing all non-CFO Act agencies to consolidate transactional financial management services under a single provider approved by the Department of the Treasury.(c)  As soon as practicable, all heads of CFO Act agencies shall use standard financial management solutions available through the Financial Management Marketplace, administered by the Financial Management Quality Service Management Office.(d)  Agency heads shall ensure that core financial systems comply with Federal accounting and financial reporting standards and relevant regulations, orders, guidance documents, policy statements, and other agency actions published by the Department of the Treasury from time to time.Sec. 6.  Reduction of NTDOs.  (a)  Within 30 days of the date of this order, the Secretary of the Treasury shall assess whether to maintain disbursing authority that it has delegated to agencies pursuant to 31 U.S.C. 3321(b) and issue notices to revoke such delegations, as appropriate, in accordance with applicable law.  (b)  The heads of agencies with disbursing authority under 31 U.S.C. 3321(c), including the Secretary of Defense, the Secretary of Homeland Security, and the Attorney General (but excluding, for the avoidance of doubt, the Supreme Court and other entities of the Federal Government outside the Executive Branch) will work with the Secretary of the Treasury to delegate the performance of their disbursing activities, other than with respect to classified payments, to the Department of the Treasury’s Chief Disbursing Officer in accordance with applicable law. (c)  Notwithstanding subsections (a) or (b) of this section, the Secretary of the Treasury may continue to delegate disbursing authority to NTDOs at other agencies when doing so would align with significant Government priorities.  Any remaining NTDOs are required to report daily to the Department of the Treasury’s centralized accounting and reporting system in accordance with then-current Department of the Treasury guidance and applicable law.(d)  The Secretary of the Treasury shall develop a plan to centralize and manage all payments previously disbursed by NTDOs, ensuring seamless continuity of Government payments.(e)  The Secretary of the Treasury, in coordination with agency heads, shall establish a transition plan for agencies currently operating as NTDOs, including staffing adjustments, system integrations, and legal or regulatory modifications necessary for full consolidation.(f)  The heads of agencies with disbursing authority delegated to the agency under 33 U.S.C. 3321(b) shall decommission all internal payment systems and use the Department of the Treasury’s disbursement systems, except and to the extent authorized by the Department of the Treasury or otherwise required by applicable law.Sec. 7.  Reporting and Implementation Requirements.  (a)  The heads of all agencies shall submit a compliance plan to the OMB Director within 90 days of the date of this order detailing their strategy for:(i)    transitioning disbursing authority to the Department of the Treasury, as applicable and as contemplated by this order;(ii)   updating and integrating systems with Department of the Treasury platforms;(iii)  procedures to verify payment information as contemplated by this order; and(iv)   transmitting information associated with improper payments to the Department of the Treasury in accordance with standards and reporting specifications established by the OMB Director in coordination with the Secretary of the Treasury as contemplated by this order.(b)  The Secretary of the Treasury shall submit an implementation report to the President through the Assistant to the President for Economic Policy within 180 days of the date of this order detailing progress on the matters set forth in this order.(c)  The Secretary of the Treasury and agency heads shall take all necessary steps to protect classified information and systems, as well as personally identifiable information and tax return information, through the implementation of this order.Sec. 8.  General Provisions.  (a)  Nothing in this order shall be construed to impair or otherwise affect:(i)   the authority granted by law to an executive department or agency, or the head thereof; or(ii)  the functions of the Director of the Office of Management and Budget relating to budgetary, administrative, or legislative proposals.(b)  This order shall be implemented consistent with applicable law and subject to the availability of appropriations.(c)  This order is not intended to, and does not, create any right or benefit, substantive or procedural, enforceable at law or in equity by any party against the United States, its departments, agencies, or entities, its officers, employees, or agents, or any other person.DONALD J. TRUMPTHE WHITE HOUSE,    March 25, 2025.# Newline-delimited ROLES catalog used by the LLM to set category_dept (verbatim when possible).ROLES_DEMO = Secretary of the Treasury (in consultation with OMB Director)All Agency HeadsSecretary of the TreasuryAgency Heads / Certifying OfficersSecretary of the Treasury & Agency Certifying OfficersOMB DirectorOMB Director (in consultation with Secretary of the Treasury)CFO Act Agency HeadsHeads of agencies with disbursing authority under 31 U.S.C. 3321(c) (e.g., DoD, DHS, DOJ) + Secretary of the TreasurySecretary of the Treasury & NTDOs remaining after consolidation processSecretary of the Treasury (in coordination with agency heads)Agency Heads with authority under 31 U.S.C. 3321(b)', false, NULL, '2025-08-28 19:15:30.694206+00');
INSERT INTO public.email_logs VALUES ('a7893eda-aa06-4062-be31-082ea427dfb9', 'outgoing', 'PMO Review Required: EO: Modernize Workforce Data [EO ID: 8fd95066-1662-4482-b1f8-3801f037f356]', NULL, '{kevin.brown@lumenlighthouse.ai}', 'Subject EO: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
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
1 | Update Payment Verification Guidance and Enhance Systems | — | Dylan Sachetti | — | [Fill Here] | [Fill Here]
2 | Review and Modify Privacy Act System of Records Notices | — | Dylan Sachetti | 2025-06-23 | [Fill Here] | [Fill Here]
3 | Issue Guidance on Data Access for Fraud Prevention | — | Dylan Sachetti | — | [Fill Here] | [Fill Here]
4 | Implement Pre-Certification Payment Verification Processes | — | Ayesha Ahsan | — | [Fill Here] | [Fill Here]
5 | Submit Payment Files with Sufficient Lead Time for Screening | — | Ayesha Ahsan | — | [Fill Here] | [Fill Here]
6 | Develop Transparent Exemption Request Process for Payment Verification | — | Dylan Sachetti | — | [Fill Here] | [Fill Here]
7 | Issue Guidance for Core Financial System Consolidation (CFO Act Agencies) | — | Hibbi Iqbal | 2025-09-21 | [Fill Here] | [Fill Here]
8 | Issue Guidance for Non-CFO Act Agency Financial Service Consolidation | — | Hibbi Iqbal | 2025-09-21 | [Fill Here] | [Fill Here]
9 | Ensure Use of Standard Financial Management Solutions | — | Hibbi Iqbal | — | [Fill Here] | [Fill Here]
10 | Ensure Core Financial Systems Comply with Federal Standards | — | Sophia Carty | — | [Fill Here] | [Fill Here]
11 | Assess and Revoke Delegated Disbursing Authority as Appropriate | — | Hibbi Iqbal | 2025-04-24 | [Fill Here] | [Fill Here]
12 | Develop Plan to Centralize and Manage NTDO Payments | — | Ayesha Ahsan | — | [Fill Here] | [Fill Here]
13 | Establish Transition Plan for NTDO Agencies | — | Ayesha Ahsan | — | [Fill Here] | [Fill Here]
14 | Decommission Internal Payment Systems and Transition to Treasury Systems | — | Robert Springfiled | — | [Fill Here] | [Fill Here]
15 | Submit Agency Compliance Plan to OMB Director | — | Dylan Sachetti | 2025-06-23 | [Fill Here] | [Fill Here]
16 | Submit Treasury Implementation Report to President | — | Hibbi Iqbal | 2025-09-21 | [Fill Here] | [Fill Here]
17 | Protect Classified and Sensitive Information During Implementation | — | Robert Springfiled | — | [Fill Here] | [Fill Here]', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:15:50.311882+00');
INSERT INTO public.email_logs VALUES ('aa9eff72-69f6-469a-9237-dd7636900dc4', 'incoming', 'Re: PMO Review Required: EO: Modernize Workforce Data [EO ID:
 8fd95066-1662-4482-b1f8-3801f037f356]', 'kevin.brown@lumenlighthouse.ai', '{eo.14249@lumenlighthouse.ai}', '
Task ID	Title	Owner	Assignee	Due	Status	Remarks
1	Update Payment Verification Guidance and Enhance Systems	—	Dylan Sachetti	—	Reject	Too Vague Instructions
2	Review and Modify Privacy Act System of Records Notices	—	Dylan Sachetti	2025-06-23	Approve	[Fill Here]
3	Issue Guidance on Data Access for Fraud Prevention	—	Dylan Sachetti	—	Approve	[Fill Here]
4	Implement Pre-Certification Payment Verification Processes	—	Ayesha Ahsan	—	Approve	[Fill Here]
5	Submit Payment Files with Sufficient Lead Time for Screening	—	Ayesha Ahsan	—	Approve	[Fill Here]
6	Develop Transparent Exemption Request Process for Payment Verification	—	Dylan Sachetti	—	Approve	[Fill Here]
7	Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
8	Issue Guidance for Non-CFO Act Agency Financial Service Consolidation	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
9	Ensure Use of Standard Financial Management Solutions	—	Hibbi Iqbal	—	Approve	[Fill Here]
10	Ensure Core Financial Systems Comply with Federal Standards	—	Sophia Carty	—	Approve	[Fill Here]
11	Assess and Revoke Delegated Disbursing Authority as Appropriate	—	Hibbi Iqbal	2025-04-24	Approve	[Fill Here]
12	Develop Plan to Centralize and Manage NTDO Payments	—	Ayesha Ahsan	—	Approve	[Fill Here]
13	Establish Transition Plan for NTDO Agencies	—	Ayesha Ahsan	—	Approve	[Fill Here]
14	Decommission Internal Payment Systems and Transition to Treasury Systems	—	Robert Springfiled	—	Approve	[Fill Here]
15	Submit Agency Compliance Plan to OMB Director	—	Dylan Sachetti	2025-06-23	Approve	[Fill Here]
16	Submit Treasury Implementation Report to President	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
17	Protect Classified and Sensitive Information During Implementation	—	Robert Springfiled	—	[Fill Here]	[Fill Here]

> On Aug 28, 2025, at 3:15 PM, eo.14249@lumenlighthouse.ai wrote:
> 
> 📋 PMO Review Required
> Executive Order: EO: Modernize Workforce Data
> EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
> Message ID: msg-2001@sample
> Received: 2025-08-13 15:00:00 UTC
> Below are the PENDING tasks for PMO action.
> 
> 📝 Instructions:
> 
> Copy the table below
> Paste it in your reply email
> Fill in the ''Status'' column with ''Approve'' or ''Reject''
> Fill in the ''Remarks'' column with your feedback
> Send the email back
> Task ID	Title	Owner	Assignee	Due	Status	Remarks
> 1	Update Payment Verification Guidance and Enhance Systems	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
> 2	Review and Modify Privacy Act System of Records Notices	—	Dylan Sachetti	2025-06-23	[Fill Here]	[Fill Here]
> 3	Issue Guidance on Data Access for Fraud Prevention	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
> 4	Implement Pre-Certification Payment Verification Processes	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
> 5	Submit Payment Files with Sufficient Lead Time for Screening	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
> 6	Develop Transparent Exemption Request Process for Payment Verification	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
> 7	Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
> 8	Issue Guidance for Non-CFO Act Agency Financial Service Consolidation	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
> 9	Ensure Use of Standard Financial Management Solutions	—	Hibbi Iqbal	—	[Fill Here]	[Fill Here]
> 10	Ensure Core Financial Systems Comply with Federal Standards	—	Sophia Carty	—	[Fill Here]	[Fill Here]
> 11	Assess and Revoke Delegated Disbursing Authority as Appropriate	—	Hibbi Iqbal	2025-04-24	[Fill Here]	[Fill Here]
> 12	Develop Plan to Centralize and Manage NTDO Payments	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
> 13	Establish Transition Plan for NTDO Agencies	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
> 14	Decommission Internal Payment Systems and Transition to Treasury Systems	—	Robert Springfiled	—	[Fill Here]	[Fill Here]
> 15	Submit Agency Compliance Plan to OMB Director	—	Dylan Sachetti	2025-06-23	[Fill Here]	[Fill Here]
> 16	Submit Treasury Implementation Report to President	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
> 17	Protect Classified and Sensitive Information During Implementation	—	Robert Springfiled	—	[Fill Here]	[Fill Here]
> 📎 Attachments:
> 
> Please refer to the attached files for detailed information:
> 
> CSV file: Complete task details in spreadsheet format
> JSON file: Structured task data
> TXT file: Full Executive Order text
> DOL EO Management System
> 
> <pmo_review_tasks.csv><pmo_review_tasks.json><executive_order.txt>

', true, NULL, '2025-08-28 19:17:12.757849+00');
INSERT INTO public.email_logs VALUES ('7c64ed7f-2f1e-459b-b6c2-bff321ea5498', 'incoming', 'Re: PMO Review Required: EO: Modernize Workforce Data [EO ID:
 8fd95066-1662-4482-b1f8-3801f037f356]', 'kevin.brown@lumenlighthouse.ai', '{eo.14249@lumenlighthouse.ai}', '
Task ID	Title	Owner	Assignee	Due	Status	Remarks
1	Update Payment Verification Guidance and Enhance Systems	—	Dylan Sachetti	—	Reject	Too Vague Instructions
2	Review and Modify Privacy Act System of Records Notices	—	Dylan Sachetti	2025-06-23	Approve	[Fill Here]
3	Issue Guidance on Data Access for Fraud Prevention	—	Dylan Sachetti	—	Approve	[Fill Here]
4	Implement Pre-Certification Payment Verification Processes	—	Ayesha Ahsan	—	Approve	[Fill Here]
5	Submit Payment Files with Sufficient Lead Time for Screening	—	Ayesha Ahsan	—	Approve	[Fill Here]
6	Develop Transparent Exemption Request Process for Payment Verification	—	Dylan Sachetti	—	Approve	[Fill Here]
7	Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
8	Issue Guidance for Non-CFO Act Agency Financial Service Consolidation	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
9	Ensure Use of Standard Financial Management Solutions	—	Hibbi Iqbal	—	Approve	[Fill Here]
10	Ensure Core Financial Systems Comply with Federal Standards	—	Sophia Carty	—	Approve	[Fill Here]
11	Assess and Revoke Delegated Disbursing Authority as Appropriate	—	Hibbi Iqbal	2025-04-24	Approve	[Fill Here]
12	Develop Plan to Centralize and Manage NTDO Payments	—	Ayesha Ahsan	—	Approve	[Fill Here]
13	Establish Transition Plan for NTDO Agencies	—	Ayesha Ahsan	—	Approve	[Fill Here]
14	Decommission Internal Payment Systems and Transition to Treasury Systems	—	Robert Springfiled	—	Approve	[Fill Here]
15	Submit Agency Compliance Plan to OMB Director	—	Dylan Sachetti	2025-06-23	Approve	[Fill Here]
16	Submit Treasury Implementation Report to President	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
17	Protect Classified and Sensitive Information During Implementation	—	Robert Springfiled	—	[Fill Here]	[Fill Here]

> On Aug 28, 2025, at 3:15 PM, eo.14249@lumenlighthouse.ai wrote:
> 
> 📋 PMO Review Required
> Executive Order: EO: Modernize Workforce Data
> EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
> Message ID: msg-2001@sample
> Received: 2025-08-13 15:00:00 UTC
> Below are the PENDING tasks for PMO action.
> 
> 📝 Instructions:
> 
> Copy the table below
> Paste it in your reply email
> Fill in the ''Status'' column with ''Approve'' or ''Reject''
> Fill in the ''Remarks'' column with your feedback
> Send the email back
> Task ID	Title	Owner	Assignee	Due	Status	Remarks
> 1	Update Payment Verification Guidance and Enhance Systems	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
> 2	Review and Modify Privacy Act System of Records Notices	—	Dylan Sachetti	2025-06-23	[Fill Here]	[Fill Here]
> 3	Issue Guidance on Data Access for Fraud Prevention	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
> 4	Implement Pre-Certification Payment Verification Processes	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
> 5	Submit Payment Files with Sufficient Lead Time for Screening	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
> 6	Develop Transparent Exemption Request Process for Payment Verification	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
> 7	Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
> 8	Issue Guidance for Non-CFO Act Agency Financial Service Consolidation	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
> 9	Ensure Use of Standard Financial Management Solutions	—	Hibbi Iqbal	—	[Fill Here]	[Fill Here]
> 10	Ensure Core Financial Systems Comply with Federal Standards	—	Sophia Carty	—	[Fill Here]	[Fill Here]
> 11	Assess and Revoke Delegated Disbursing Authority as Appropriate	—	Hibbi Iqbal	2025-04-24	[Fill Here]	[Fill Here]
> 12	Develop Plan to Centralize and Manage NTDO Payments	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
> 13	Establish Transition Plan for NTDO Agencies	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
> 14	Decommission Internal Payment Systems and Transition to Treasury Systems	—	Robert Springfiled	—	[Fill Here]	[Fill Here]
> 15	Submit Agency Compliance Plan to OMB Director	—	Dylan Sachetti	2025-06-23	[Fill Here]	[Fill Here]
> 16	Submit Treasury Implementation Report to President	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
> 17	Protect Classified and Sensitive Information During Implementation	—	Robert Springfiled	—	[Fill Here]	[Fill Here]
> 📎 Attachments:
> 
> Please refer to the attached files for detailed information:
> 
> CSV file: Complete task details in spreadsheet format
> JSON file: Structured task data
> TXT file: Full Executive Order text
> DOL EO Management System
> 
> <pmo_review_tasks.csv><pmo_review_tasks.json><executive_order.txt>

', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:17:12.771689+00');
INSERT INTO public.email_logs VALUES ('413e3109-7de0-464b-9838-c4dfd7d2d172', 'outgoing', 'Improved Tasks Review: EO: Modernize Workforce Data', NULL, '{kevin.brown@lumenlighthouse.ai}', 'Subject EO: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

=== IMPROVEMENT SUMMARY ===
The revised task should explicitly reference the requirement for consultation with the OMB Director, cite the relevant legal authorities, and focus on the specific elements mandated by the EO (guidelines for Do Not Pay, other validation programs, and actionable instructions for agencies). Remove extraneous details not present in the EO, such as establishing timelines and IT team coordination, unless these are specified elsewhere in the implementation plan.

Below are ALL tasks for this EO with their current status.
Tasks marked as ''Approved'' were previously approved and do not need action.
Tasks marked as ''Pending PMO approval'' are improved versions that need your review.

INSTRUCTIONS:
1. Copy the table below
2. Paste it in your reply email
3. For ''Pending PMO approval'' tasks: Fill in the ''Status'' column with ''Approve'' or ''Reject''
4. For ''Pending PMO approval'' tasks: Fill in the ''Remarks'' column with your feedback
5. Leave ''Approved'' tasks as-is (no action needed)
6. Send the email back

NOTE: Please refer to the attached files for detailed information:
- CSV file: Complete task details in spreadsheet format
- JSON file: Structured task data
- TXT file: Full Executive Order text

Task ID | Title | Owner | Assignee | Due | Status | Remarks
--------|-------|-------|----------|-----|--------|--------
1 | Review and Modify Privacy Act System of Records Notices | — | Dylan Sachetti | 2025-06-23 | Approved | N/A
2 | Issue Guidance on Data Access for Fraud Prevention | — | Dylan Sachetti | TBD | Approved | N/A
3 | Update and Issue Payment Verification Guidance in Consultation with OMB Director | — | Dylan Sachetti | TBD | [Fill Here] | [Fill Here]
4 | Protect Classified and Sensitive Information During Implementation | — | Robert Springfiled | TBD | [Fill Here] | [Fill Here]
5 | Implement Pre-Certification Payment Verification Processes | — | Ayesha Ahsan | TBD | Approved | N/A
6 | Submit Payment Files with Sufficient Lead Time for Screening | — | Ayesha Ahsan | TBD | Approved | N/A
7 | Develop Transparent Exemption Request Process for Payment Verification | — | Dylan Sachetti | TBD | Approved | N/A
8 | Issue Guidance for Core Financial System Consolidation (CFO Act Agencies) | — | Hibbi Iqbal | 2025-09-21 | Approved | N/A
9 | Issue Guidance for Non-CFO Act Agency Financial Service Consolidation | — | Hibbi Iqbal | 2025-09-21 | Approved | N/A
10 | Ensure Use of Standard Financial Management Solutions | — | Hibbi Iqbal | TBD | Approved | N/A
11 | Ensure Core Financial Systems Comply with Federal Standards | — | Sophia Carty | TBD | Approved | N/A
12 | Assess and Revoke Delegated Disbursing Authority as Appropriate | — | Hibbi Iqbal | 2025-04-24 | Approved | N/A
13 | Develop Plan to Centralize and Manage NTDO Payments | — | Ayesha Ahsan | TBD | Approved | N/A
14 | Establish Transition Plan for NTDO Agencies | — | Ayesha Ahsan | TBD | Approved | N/A
15 | Decommission Internal Payment Systems and Transition to Treasury Systems | — | Robert Springfiled | TBD | Approved | N/A
16 | Submit Agency Compliance Plan to OMB Director | — | Dylan Sachetti | 2025-06-23 | Approved | N/A
17 | Submit Treasury Implementation Report to President | — | Hibbi Iqbal | 2025-09-21 | Approved | N/A', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:17:34.360958+00');
INSERT INTO public.email_logs VALUES ('10abc36b-1ba6-448c-b6c8-ad3e9b6f2952', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{dylan.sachetti@lumenlighthouse.ai}', 'Dear Dylan Sachetti,

You have been assigned 4 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Review and Modify Privacy Act System of Records Notices
  Description: Review and modify relevant system of records notices to include a routine use for disclosure to Treasury for fraud and improper payment prevention. Per Sec. 3(d).
  Due Date: 2025-06-23
  Status: approved

Task 2:
  Title: Issue Guidance on Data Access for Fraud Prevention
  Description: Issue guidance to agency heads on circumstances for providing Treasury with access to necessary data for fraud and improper payment detection, excluding sensitive data types. Per Sec. 3(e).
  Due Date: TBD
  Status: approved

Task 3:
  Title: Develop Transparent Exemption Request Process for Payment Verification
  Description: Develop and include a transparent process for agencies to request exemptions from payment verification requirements for specific payments. Per Sec. 4(e).
  Due Date: TBD
  Status: approved

Task 4:
  Title: Submit Agency Compliance Plan to OMB Director
  Description: Submit a compliance plan within 90 days detailing strategy for transitioning disbursing authority, updating systems, verifying payment information, and reporting improper payments. Per Sec. 7(a).
  Due Date: 2025-06-23
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:17:12.905263+00');
INSERT INTO public.email_logs VALUES ('b6b942e5-0fbf-4ec5-93f1-eda9108b5479', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{ayesha.ahsan@lumenlighthouse.ai}', 'Dear Ayesha Ahsan,

You have been assigned 4 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Implement Pre-Certification Payment Verification Processes
  Description: Ensure all disbursements comply with Treasury''s pre-certification requirements, including validation of funds, payee information, and contract references. Per Sec. 4(a)-(b).
  Due Date: TBD
  Status: approved

Task 2:
  Title: Submit Payment Files with Sufficient Lead Time for Screening
  Description: Submit payment files to Treasury with sufficient lead time for fraud and improper payment screening, as determined by Treasury requirements. Per Sec. 4(c).
  Due Date: TBD
  Status: approved

Task 3:
  Title: Develop Plan to Centralize and Manage NTDO Payments
  Description: Develop a plan to centralize and manage all payments previously disbursed by NTDOs, ensuring seamless continuity of government payments. Per Sec. 6(d).
  Due Date: TBD
  Status: approved

Task 4:
  Title: Establish Transition Plan for NTDO Agencies
  Description: Establish a transition plan for agencies currently operating as NTDOs, including staffing, system integrations, and legal/regulatory modifications for consolidation. Per Sec. 6(e).
  Due Date: TBD
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:17:13.115723+00');
INSERT INTO public.email_logs VALUES ('a5e4453f-6c5d-446e-ae12-6065527f084b', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{hibbi.iqbal@lumenlighthouse.ai}', 'Dear Hibbi Iqbal,

You have been assigned 5 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)
  Description: Issue guidance directing CFO Act agencies to consolidate their core financial systems. Per Sec. 5(a).
  Due Date: 2025-09-21
  Status: approved

Task 2:
  Title: Issue Guidance for Non-CFO Act Agency Financial Service Consolidation
  Description: Issue guidance directing non-CFO Act agencies to consolidate transactional financial management services under a single Treasury-approved provider. Per Sec. 5(b).
  Due Date: 2025-09-21
  Status: approved

Task 3:
  Title: Ensure Use of Standard Financial Management Solutions
  Description: Ensure all CFO Act agencies use standard financial management solutions available through the Financial Management Marketplace. Per Sec. 5(c).
  Due Date: TBD
  Status: approved

Task 4:
  Title: Assess and Revoke Delegated Disbursing Authority as Appropriate
  Description: Assess whether to maintain or revoke delegated disbursing authority to agencies and issue revocation notices as appropriate. Per Sec. 6(a).
  Due Date: 2025-04-24
  Status: approved

Task 5:
  Title: Submit Treasury Implementation Report to President
  Description: Submit an implementation report to the President within 180 days detailing progress on EO implementation. Per Sec. 7(b).
  Due Date: 2025-09-21
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:17:13.286342+00');
INSERT INTO public.email_logs VALUES ('a9fada6f-b88c-416e-8f2f-a2486a2ae6c0', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{sophia.carty@lumenlighthouse.ai}', 'Dear Sophia Carty,

You have been assigned 1 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Ensure Core Financial Systems Comply with Federal Standards
  Description: Ensure core financial systems comply with Federal accounting and financial reporting standards and relevant Treasury guidance. Per Sec. 5(d).
  Due Date: TBD
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:17:13.458855+00');
INSERT INTO public.email_logs VALUES ('a874db8f-6cb9-4a9c-b712-e2a3267ac3bd', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{robert.springfiled@lumenlighthouse.ai}', 'Dear Robert Springfiled,

You have been assigned 1 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Decommission Internal Payment Systems and Transition to Treasury Systems
  Description: Decommission all internal payment systems and transition to using Treasury’s disbursement systems, except as otherwise authorized. Per Sec. 6(f).
  Due Date: TBD
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:17:13.644338+00');
INSERT INTO public.email_logs VALUES ('8e510567-ef45-4941-b6df-4d339ab1d34d', 'incoming', 'Daily Task Update - 2025-01-15', 'john.doe@example.com', '{pmo@example.com}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:01:09.295761+00');
INSERT INTO public.email_logs VALUES ('e67db531-c879-4312-9854-4a0874790595', 'incoming', 'Mail delivery failed: returning message to sender', 'Mailer-Daemon@p3plzcpnl492179.prod.phx3.secureserver.net', '{eo.14249@lumenlighthouse.ai}', 'This message was created automatically by mail delivery software.

A message that you sent could not be delivered to one or more of its
recipients. This is a permanent error. The following address(es) failed:

  test1@example.com
    host p3nlsmtpcp01-v01.prod.phx3.secureserver.net [132.148.124.48]
    SMTP error from remote mail server after RCPT TO:<test1@example.com>:
    550 5.1.1 <test1@example.com> recipient rejected. This is a default recipient used as a placeholder in many web applications. Please check your settings and try again.
This is a test email sent to multiple recipients with improved rate limiting handling.
', true, NULL, '2025-08-28 19:22:17.371837+00');
INSERT INTO public.email_logs VALUES ('ede1430f-f57c-4b35-a00b-aa791fd9d1f4', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{dylan.sachetti@lumenlighthouse.ai}', 'Dear Dylan Sachetti,

You have been assigned 4 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Review and Modify Privacy Act System of Records Notices
  Description: Review and modify relevant system of records notices to include a routine use for disclosure to Treasury for fraud and improper payment prevention. Per Sec. 3(d).
  Due Date: 2025-06-23
  Status: approved

Task 2:
  Title: Issue Guidance on Data Access for Fraud Prevention
  Description: Issue guidance to agency heads on circumstances for providing Treasury with access to necessary data for fraud and improper payment detection, excluding sensitive data types. Per Sec. 3(e).
  Due Date: TBD
  Status: approved

Task 3:
  Title: Develop Transparent Exemption Request Process for Payment Verification
  Description: Develop and include a transparent process for agencies to request exemptions from payment verification requirements for specific payments. Per Sec. 4(e).
  Due Date: TBD
  Status: approved

Task 4:
  Title: Submit Agency Compliance Plan to OMB Director
  Description: Submit a compliance plan within 90 days detailing strategy for transitioning disbursing authority, updating systems, verifying payment information, and reporting improper payments. Per Sec. 7(a).
  Due Date: 2025-06-23
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:23:25.318649+00');
INSERT INTO public.email_logs VALUES ('e01eec06-a612-40e8-a575-f755d56ceb7a', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{ayesha.ahsan@lumenlighthouse.ai}', 'Dear Ayesha Ahsan,

You have been assigned 4 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Implement Pre-Certification Payment Verification Processes
  Description: Ensure all disbursements comply with Treasury''s pre-certification requirements, including validation of funds, payee information, and contract references. Per Sec. 4(a)-(b).
  Due Date: TBD
  Status: approved

Task 2:
  Title: Submit Payment Files with Sufficient Lead Time for Screening
  Description: Submit payment files to Treasury with sufficient lead time for fraud and improper payment screening, as determined by Treasury requirements. Per Sec. 4(c).
  Due Date: TBD
  Status: approved

Task 3:
  Title: Develop Plan to Centralize and Manage NTDO Payments
  Description: Develop a plan to centralize and manage all payments previously disbursed by NTDOs, ensuring seamless continuity of government payments. Per Sec. 6(d).
  Due Date: TBD
  Status: approved

Task 4:
  Title: Establish Transition Plan for NTDO Agencies
  Description: Establish a transition plan for agencies currently operating as NTDOs, including staffing, system integrations, and legal/regulatory modifications for consolidation. Per Sec. 6(e).
  Due Date: TBD
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:23:27.681907+00');
INSERT INTO public.email_logs VALUES ('c1fbed02-518d-4cd3-92c2-5bef5e28fffa', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{hibbi.iqbal@lumenlighthouse.ai}', 'Dear Hibbi Iqbal,

You have been assigned 5 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)
  Description: Issue guidance directing CFO Act agencies to consolidate their core financial systems. Per Sec. 5(a).
  Due Date: 2025-09-21
  Status: approved

Task 2:
  Title: Issue Guidance for Non-CFO Act Agency Financial Service Consolidation
  Description: Issue guidance directing non-CFO Act agencies to consolidate transactional financial management services under a single Treasury-approved provider. Per Sec. 5(b).
  Due Date: 2025-09-21
  Status: approved

Task 3:
  Title: Ensure Use of Standard Financial Management Solutions
  Description: Ensure all CFO Act agencies use standard financial management solutions available through the Financial Management Marketplace. Per Sec. 5(c).
  Due Date: TBD
  Status: approved

Task 4:
  Title: Assess and Revoke Delegated Disbursing Authority as Appropriate
  Description: Assess whether to maintain or revoke delegated disbursing authority to agencies and issue revocation notices as appropriate. Per Sec. 6(a).
  Due Date: 2025-04-24
  Status: approved

Task 5:
  Title: Submit Treasury Implementation Report to President
  Description: Submit an implementation report to the President within 180 days detailing progress on EO implementation. Per Sec. 7(b).
  Due Date: 2025-09-21
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:23:30.056436+00');
INSERT INTO public.email_logs VALUES ('f0f970cf-1109-42a5-a2a5-2e964475e4d7', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{sophia.carty@lumenlighthouse.ai}', 'Dear Sophia Carty,

You have been assigned 1 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Ensure Core Financial Systems Comply with Federal Standards
  Description: Ensure core financial systems comply with Federal accounting and financial reporting standards and relevant Treasury guidance. Per Sec. 5(d).
  Due Date: TBD
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:23:31.747114+00');
INSERT INTO public.email_logs VALUES ('ba9c9afd-4db1-401d-b2ec-050b3db3c4a6', 'incoming', 'Task Update - Reporting System', 'jane.smith@example.com', '{pmo@example.com}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:01:09.301502+00');
INSERT INTO public.email_logs VALUES ('3195cf14-1726-47e2-a1a2-85162559f052', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{robert.springfiled@lumenlighthouse.ai}', 'Dear Robert Springfiled,

You have been assigned 1 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Decommission Internal Payment Systems and Transition to Treasury Systems
  Description: Decommission all internal payment systems and transition to using Treasury’s disbursement systems, except as otherwise authorized. Per Sec. 6(f).
  Due Date: TBD
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:23:33.19932+00');
INSERT INTO public.email_logs VALUES ('b21cc45a-ddae-40e6-83cf-eeac645464ca', 'incoming', 'Re: PMO Review Required: EO: Modernize Workforce Data [EO ID:
 8fd95066-1662-4482-b1f8-3801f037f356]', 'kevin.brown@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', '

> 
> 
> Task ID	Title	Owner	Assignee	Due	Status	Remarks
> 1	Update Payment Verification Guidance and Enhance Systems	—	Dylan Sachetti	—	Reject	Too Vague Instructions
> 2	Review and Modify Privacy Act System of Records Notices	—	Dylan Sachetti	2025-06-23	Approve	[Fill Here]
> 3	Issue Guidance on Data Access for Fraud Prevention	—	Dylan Sachetti	—	Approve	[Fill Here]
> 4	Implement Pre-Certification Payment Verification Processes	—	Ayesha Ahsan	—	Approve	[Fill Here]
> 5	Submit Payment Files with Sufficient Lead Time for Screening	—	Ayesha Ahsan	—	Approve	[Fill Here]
> 6	Develop Transparent Exemption Request Process for Payment Verification	—	Dylan Sachetti	—	Approve	[Fill Here]
> 7	Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
> 8	Issue Guidance for Non-CFO Act Agency Financial Service Consolidation	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
> 9	Ensure Use of Standard Financial Management Solutions	—	Hibbi Iqbal	—	Approve	[Fill Here]
> 10	Ensure Core Financial Systems Comply with Federal Standards	—	Sophia Carty	—	Approve	[Fill Here]
> 11	Assess and Revoke Delegated Disbursing Authority as Appropriate	—	Hibbi Iqbal	2025-04-24	Approve	[Fill Here]
> 12	Develop Plan to Centralize and Manage NTDO Payments	—	Ayesha Ahsan	—	Approve	[Fill Here]
> 13	Establish Transition Plan for NTDO Agencies	—	Ayesha Ahsan	—	Approve	[Fill Here]
> 14	Decommission Internal Payment Systems and Transition to Treasury Systems	—	Robert Springfiled	—	Approve	[Fill Here]
> 15	Submit Agency Compliance Plan to OMB Director	—	Dylan Sachetti	2025-06-23	Approve	[Fill Here]
> 16	Submit Treasury Implementation Report to President	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
> 17	Protect Classified and Sensitive Information During Implementation	—	Robert Springfiled	—	[Fill Here]	[Fill Here]
> 
>> On Aug 28, 2025, at 3:15 PM, eo.14249@lumenlighthouse.ai wrote:
>> 
>> 📋 PMO Review Required
>> Executive Order: EO: Modernize Workforce Data
>> EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
>> Message ID: msg-2001@sample
>> Received: 2025-08-13 15:00:00 UTC
>> Below are the PENDING tasks for PMO action.
>> 
>> 📝 Instructions:
>> 
>> Copy the table below
>> Paste it in your reply email
>> Fill in the ''Status'' column with ''Approve'' or ''Reject''
>> Fill in the ''Remarks'' column with your feedback
>> Send the email back
>> Task ID	Title	Owner	Assignee	Due	Status	Remarks
>> 1	Update Payment Verification Guidance and Enhance Systems	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
>> 2	Review and Modify Privacy Act System of Records Notices	—	Dylan Sachetti	2025-06-23	[Fill Here]	[Fill Here]
>> 3	Issue Guidance on Data Access for Fraud Prevention	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
>> 4	Implement Pre-Certification Payment Verification Processes	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
>> 5	Submit Payment Files with Sufficient Lead Time for Screening	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
>> 6	Develop Transparent Exemption Request Process for Payment Verification	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
>> 7	Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
>> 8	Issue Guidance for Non-CFO Act Agency Financial Service Consolidation	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
>> 9	Ensure Use of Standard Financial Management Solutions	—	Hibbi Iqbal	—	[Fill Here]	[Fill Here]
>> 10	Ensure Core Financial Systems Comply with Federal Standards	—	Sophia Carty	—	[Fill Here]	[Fill Here]
>> 11	Assess and Revoke Delegated Disbursing Authority as Appropriate	—	Hibbi Iqbal	2025-04-24	[Fill Here]	[Fill Here]
>> 12	Develop Plan to Centralize and Manage NTDO Payments	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
>> 13	Establish Transition Plan for NTDO Agencies	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
>> 14	Decommission Internal Payment Systems and Transition to Treasury Systems	—	Robert Springfiled	—	[Fill Here]	[Fill Here]
>> 15	Submit Agency Compliance Plan to OMB Director	—	Dylan Sachetti	2025-06-23	[Fill Here]	[Fill Here]
>> 16	Submit Treasury Implementation Report to President	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
>> 17	Protect Classified and Sensitive Information During Implementation	—	Robert Springfiled	—	[Fill Here]	[Fill Here]
>> 📎 Attachments:
>> 
>> Please refer to the attached files for detailed information:
>> 
>> CSV file: Complete task details in spreadsheet format
>> JSON file: Structured task data
>> TXT file: Full Executive Order text
>> DOL EO Management System
>> 
>> <pmo_review_tasks.csv><pmo_review_tasks.json><executive_order.txt>
> 

', true, NULL, '2025-08-28 19:26:33.839876+00');
INSERT INTO public.email_logs VALUES ('57d976e2-f3c2-444c-bdaa-48fee0e54d92', 'incoming', 'Re: PMO Review Required: EO: Modernize Workforce Data [EO ID:
 8fd95066-1662-4482-b1f8-3801f037f356]', 'kevin.brown@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', '

> 
> 
> Task ID	Title	Owner	Assignee	Due	Status	Remarks
> 1	Update Payment Verification Guidance and Enhance Systems	—	Dylan Sachetti	—	Reject	Too Vague Instructions
> 2	Review and Modify Privacy Act System of Records Notices	—	Dylan Sachetti	2025-06-23	Approve	[Fill Here]
> 3	Issue Guidance on Data Access for Fraud Prevention	—	Dylan Sachetti	—	Approve	[Fill Here]
> 4	Implement Pre-Certification Payment Verification Processes	—	Ayesha Ahsan	—	Approve	[Fill Here]
> 5	Submit Payment Files with Sufficient Lead Time for Screening	—	Ayesha Ahsan	—	Approve	[Fill Here]
> 6	Develop Transparent Exemption Request Process for Payment Verification	—	Dylan Sachetti	—	Approve	[Fill Here]
> 7	Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
> 8	Issue Guidance for Non-CFO Act Agency Financial Service Consolidation	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
> 9	Ensure Use of Standard Financial Management Solutions	—	Hibbi Iqbal	—	Approve	[Fill Here]
> 10	Ensure Core Financial Systems Comply with Federal Standards	—	Sophia Carty	—	Approve	[Fill Here]
> 11	Assess and Revoke Delegated Disbursing Authority as Appropriate	—	Hibbi Iqbal	2025-04-24	Approve	[Fill Here]
> 12	Develop Plan to Centralize and Manage NTDO Payments	—	Ayesha Ahsan	—	Approve	[Fill Here]
> 13	Establish Transition Plan for NTDO Agencies	—	Ayesha Ahsan	—	Approve	[Fill Here]
> 14	Decommission Internal Payment Systems and Transition to Treasury Systems	—	Robert Springfiled	—	Approve	[Fill Here]
> 15	Submit Agency Compliance Plan to OMB Director	—	Dylan Sachetti	2025-06-23	Approve	[Fill Here]
> 16	Submit Treasury Implementation Report to President	—	Hibbi Iqbal	2025-09-21	Approve	[Fill Here]
> 17	Protect Classified and Sensitive Information During Implementation	—	Robert Springfiled	—	[Fill Here]	[Fill Here]
> 
>> On Aug 28, 2025, at 3:15 PM, eo.14249@lumenlighthouse.ai wrote:
>> 
>> 📋 PMO Review Required
>> Executive Order: EO: Modernize Workforce Data
>> EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
>> Message ID: msg-2001@sample
>> Received: 2025-08-13 15:00:00 UTC
>> Below are the PENDING tasks for PMO action.
>> 
>> 📝 Instructions:
>> 
>> Copy the table below
>> Paste it in your reply email
>> Fill in the ''Status'' column with ''Approve'' or ''Reject''
>> Fill in the ''Remarks'' column with your feedback
>> Send the email back
>> Task ID	Title	Owner	Assignee	Due	Status	Remarks
>> 1	Update Payment Verification Guidance and Enhance Systems	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
>> 2	Review and Modify Privacy Act System of Records Notices	—	Dylan Sachetti	2025-06-23	[Fill Here]	[Fill Here]
>> 3	Issue Guidance on Data Access for Fraud Prevention	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
>> 4	Implement Pre-Certification Payment Verification Processes	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
>> 5	Submit Payment Files with Sufficient Lead Time for Screening	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
>> 6	Develop Transparent Exemption Request Process for Payment Verification	—	Dylan Sachetti	—	[Fill Here]	[Fill Here]
>> 7	Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
>> 8	Issue Guidance for Non-CFO Act Agency Financial Service Consolidation	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
>> 9	Ensure Use of Standard Financial Management Solutions	—	Hibbi Iqbal	—	[Fill Here]	[Fill Here]
>> 10	Ensure Core Financial Systems Comply with Federal Standards	—	Sophia Carty	—	[Fill Here]	[Fill Here]
>> 11	Assess and Revoke Delegated Disbursing Authority as Appropriate	—	Hibbi Iqbal	2025-04-24	[Fill Here]	[Fill Here]
>> 12	Develop Plan to Centralize and Manage NTDO Payments	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
>> 13	Establish Transition Plan for NTDO Agencies	—	Ayesha Ahsan	—	[Fill Here]	[Fill Here]
>> 14	Decommission Internal Payment Systems and Transition to Treasury Systems	—	Robert Springfiled	—	[Fill Here]	[Fill Here]
>> 15	Submit Agency Compliance Plan to OMB Director	—	Dylan Sachetti	2025-06-23	[Fill Here]	[Fill Here]
>> 16	Submit Treasury Implementation Report to President	—	Hibbi Iqbal	2025-09-21	[Fill Here]	[Fill Here]
>> 17	Protect Classified and Sensitive Information During Implementation	—	Robert Springfiled	—	[Fill Here]	[Fill Here]
>> 📎 Attachments:
>> 
>> Please refer to the attached files for detailed information:
>> 
>> CSV file: Complete task details in spreadsheet format
>> JSON file: Structured task data
>> TXT file: Full Executive Order text
>> DOL EO Management System
>> 
>> <pmo_review_tasks.csv><pmo_review_tasks.json><executive_order.txt>
> 

', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:26:33.850633+00');
INSERT INTO public.email_logs VALUES ('3f45ae5b-7ba9-4535-b739-c4ba8e84f7f7', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{dylan.sachetti@lumenlighthouse.ai}', 'Dear Dylan Sachetti,

You have been assigned 4 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Issue Guidance on Data Access for Fraud Prevention
  Description: Issue guidance to agency heads on circumstances for providing Treasury with access to necessary data for fraud and improper payment detection, excluding sensitive data types. Per Sec. 3(e).
  Due Date: TBD
  Status: approved

Task 2:
  Title: Update and Issue Payment Verification Guidance in Consultation with OMB Director
  Description: In consultation with the OMB Director, update and issue guidance to ensure all payments made by the Department of the Treasury on behalf of agencies are subject to pre-certification verification processes. The guidance must: (1) set forth guidelines for compliance with the Do Not Pay Working System as described in 31 U.S.C. 3351 et seq.; (2) include requirements for other payment, account, and payee validation programs and services as determined beneficial for reducing financial fraud and improper payments; (3) specify the data elements and formats agencies must provide for payment submissions; and (4) outline procedures for agencies and Treasury to conduct verification prior to disbursement, as required by law. Reference the legal authorities (31 U.S.C. 3321, 31 U.S.C. 3351 et seq.) and ensure the guidance is actionable for agency implementation.
  Due Date: TBD
  Status: approved

Task 3:
  Title: Develop Transparent Exemption Request Process for Payment Verification
  Description: Develop and include a transparent process for agencies to request exemptions from payment verification requirements for specific payments. Per Sec. 4(e).
  Due Date: TBD
  Status: approved

Task 4:
  Title: Submit Agency Compliance Plan to OMB Director
  Description: Submit a compliance plan within 90 days detailing strategy for transitioning disbursing authority, updating systems, verifying payment information, and reporting improper payments. Per Sec. 7(a).
  Due Date: 2025-06-23
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:26:36.672464+00');
INSERT INTO public.email_logs VALUES ('1da4f4b5-5d58-414f-b527-01d02f0d10b8', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{robert.springfiled@lumenlighthouse.ai}', 'Dear Robert Springfiled,

You have been assigned 2 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Protect Classified and Sensitive Information During Implementation
  Description: Take all necessary steps to protect classified information, personally identifiable information, and tax return information during EO implementation. Per Sec. 7(c).
  Due Date: TBD
  Status: approved

Task 2:
  Title: Decommission Internal Payment Systems and Transition to Treasury Systems
  Description: Decommission all internal payment systems and transition to using Treasury’s disbursement systems, except as otherwise authorized. Per Sec. 6(f).
  Due Date: TBD
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:26:39.061876+00');
INSERT INTO public.email_logs VALUES ('ea53c162-518d-4053-9c49-8bd4d569c3c8', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{ayesha.ahsan@lumenlighthouse.ai}', 'Dear Ayesha Ahsan,

You have been assigned 4 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Implement Pre-Certification Payment Verification Processes
  Description: Ensure all disbursements comply with Treasury''s pre-certification requirements, including validation of funds, payee information, and contract references. Per Sec. 4(a)-(b).
  Due Date: TBD
  Status: approved

Task 2:
  Title: Submit Payment Files with Sufficient Lead Time for Screening
  Description: Submit payment files to Treasury with sufficient lead time for fraud and improper payment screening, as determined by Treasury requirements. Per Sec. 4(c).
  Due Date: TBD
  Status: approved

Task 3:
  Title: Develop Plan to Centralize and Manage NTDO Payments
  Description: Develop a plan to centralize and manage all payments previously disbursed by NTDOs, ensuring seamless continuity of government payments. Per Sec. 6(d).
  Due Date: TBD
  Status: approved

Task 4:
  Title: Establish Transition Plan for NTDO Agencies
  Description: Establish a transition plan for agencies currently operating as NTDOs, including staffing, system integrations, and legal/regulatory modifications for consolidation. Per Sec. 6(e).
  Due Date: TBD
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:26:41.461713+00');
INSERT INTO public.email_logs VALUES ('fa003149-95f9-45a1-8360-ae19c8712e68', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{hibbi.iqbal@lumenlighthouse.ai}', 'Dear Hibbi Iqbal,

You have been assigned 5 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)
  Description: Issue guidance directing CFO Act agencies to consolidate their core financial systems. Per Sec. 5(a).
  Due Date: 2025-09-21
  Status: approved

Task 2:
  Title: Issue Guidance for Non-CFO Act Agency Financial Service Consolidation
  Description: Issue guidance directing non-CFO Act agencies to consolidate transactional financial management services under a single Treasury-approved provider. Per Sec. 5(b).
  Due Date: 2025-09-21
  Status: approved

Task 3:
  Title: Ensure Use of Standard Financial Management Solutions
  Description: Ensure all CFO Act agencies use standard financial management solutions available through the Financial Management Marketplace. Per Sec. 5(c).
  Due Date: TBD
  Status: approved

Task 4:
  Title: Submit Treasury Implementation Report to President
  Description: Submit an implementation report to the President within 180 days detailing progress on EO implementation. Per Sec. 7(b).
  Due Date: 2025-09-21
  Status: approved

Task 5:
  Title: Assess and Revoke Delegated Disbursing Authority as Appropriate
  Description: Assess whether to maintain or revoke delegated disbursing authority to agencies and issue revocation notices as appropriate. Per Sec. 6(a).
  Due Date: 2025-04-24
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:26:43.03161+00');
INSERT INTO public.email_logs VALUES ('22117f7f-090d-40c2-8faa-810ddf5846b4', 'outgoing', 'Task Assignment: EO: Modernize Workforce Data', NULL, '{sophia.carty@lumenlighthouse.ai}', 'Dear Sophia Carty,

You have been assigned 1 task(s) from Executive Order: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

Your assigned tasks are:

Task 1:
  Title: Ensure Core Financial Systems Comply with Federal Standards
  Description: Ensure core financial systems comply with Federal accounting and financial reporting standards and relevant Treasury guidance. Per Sec. 5(d).
  Due Date: TBD
  Status: approved

Please review these tasks and begin work as soon as possible.
If you have any questions or need clarification, please contact your supervisor.

Best regards,
DOL EO Management System', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:26:44.383984+00');
INSERT INTO public.email_logs VALUES ('3f791f90-d891-4c6b-8968-1d337cc8eea3', 'outgoing', 'Improved Tasks Review: EO: Modernize Workforce Data', NULL, '{kevin.brown@lumenlighthouse.ai}', 'Subject EO: EO: Modernize Workforce Data
EO ID: 8fd95066-1662-4482-b1f8-3801f037f356
EO Message-ID: msg-2001@sample
Received: 2025-08-13 15:00:00 UTC

=== IMPROVEMENT SUMMARY ===
The task was rewritten to provide clear, actionable instructions, addressing the PMO''s feedback that the original was too vague. The revised task now specifies the need for a comprehensive review, explicit inclusion of a ''routine use'' provision, details on the types of data and circumstances for disclosure, and documentation of the process, ensuring clarity and completeness.

Below are ALL tasks for this EO with their current status.
Tasks marked as ''Approved'' were previously approved and do not need action.
Tasks marked as ''Pending PMO approval'' are improved versions that need your review.

INSTRUCTIONS:
1. Copy the table below
2. Paste it in your reply email
3. For ''Pending PMO approval'' tasks: Fill in the ''Status'' column with ''Approve'' or ''Reject''
4. For ''Pending PMO approval'' tasks: Fill in the ''Remarks'' column with your feedback
5. Leave ''Approved'' tasks as-is (no action needed)
6. Send the email back

NOTE: Please refer to the attached files for detailed information:
- CSV file: Complete task details in spreadsheet format
- JSON file: Structured task data
- TXT file: Full Executive Order text

Task ID | Title | Owner | Assignee | Due | Status | Remarks
--------|-------|-------|----------|-----|--------|--------
1 | Issue Guidance on Data Access for Fraud Prevention | — | Dylan Sachetti | TBD | Approved | N/A
2 | Update and Issue Payment Verification Guidance in Consultation with OMB Director | — | Dylan Sachetti | TBD | Approved | N/A
3 | Update Privacy Act System of Records Notices for Treasury Data Sharing | — | Dylan Sachetti | 2025-06-23 | [Fill Here] | [Fill Here]
4 | Protect Classified and Sensitive Information During Implementation | — | Robert Springfiled | TBD | Approved | N/A
5 | Implement Pre-Certification Payment Verification Processes | — | Ayesha Ahsan | TBD | Approved | N/A
6 | Submit Payment Files with Sufficient Lead Time for Screening | — | Ayesha Ahsan | TBD | Approved | N/A
7 | Develop Transparent Exemption Request Process for Payment Verification | — | Dylan Sachetti | TBD | Approved | N/A
8 | Issue Guidance for Core Financial System Consolidation (CFO Act Agencies) | — | Hibbi Iqbal | 2025-09-21 | Approved | N/A
9 | Issue Guidance for Non-CFO Act Agency Financial Service Consolidation | — | Hibbi Iqbal | 2025-09-21 | Approved | N/A
10 | Ensure Use of Standard Financial Management Solutions | — | Hibbi Iqbal | TBD | Approved | N/A
11 | Ensure Core Financial Systems Comply with Federal Standards | — | Sophia Carty | TBD | Approved | N/A
12 | Submit Treasury Implementation Report to President | — | Hibbi Iqbal | 2025-09-21 | Approved | N/A
13 | Assess and Revoke Delegated Disbursing Authority as Appropriate | — | Hibbi Iqbal | 2025-04-24 | Approved | N/A
14 | Develop Plan to Centralize and Manage NTDO Payments | — | Ayesha Ahsan | TBD | Approved | N/A
15 | Establish Transition Plan for NTDO Agencies | — | Ayesha Ahsan | TBD | Approved | N/A
16 | Decommission Internal Payment Systems and Transition to Treasury Systems | — | Robert Springfiled | TBD | Approved | N/A
17 | Submit Agency Compliance Plan to OMB Director | — | Dylan Sachetti | 2025-06-23 | Approved | N/A', false, '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-28 19:26:45.917904+00');
INSERT INTO public.email_logs VALUES ('a3dfef6d-0965-4ebe-be66-eeffa6a6a5b1', 'incoming', 'Daily Task Update - 2025-01-15', 'john.doe@example.com', '{pmo@example.com}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:01:09.237875+00');
INSERT INTO public.email_logs VALUES ('d555acc1-d625-4024-aaa9-b4bf5f64fced', 'incoming', 'EO - Digital Transformation Initiative', 'admin@example.com', '{pmo@example.com}', 'Executive Order for Digital Transformation Initiative

This executive order outlines the digital transformation requirements for the Department of Labor.

Key directives:
1. Implement new reporting systems
2. Update documentation
3. Conduct security reviews

Please process this executive order and create appropriate tasks.', true, NULL, '2025-08-29 18:01:09.248296+00');
INSERT INTO public.email_logs VALUES ('cbe3c92e-07d8-4ff5-97d6-ba484f8a3950', 'incoming', 'Re: PMO Review - EO-12345 - Task Approval', 'pmo@example.com', '{admin@example.com}', 'PMO Review Response

I have reviewed the tasks for EO-12345 and approve the following tasks:
- Task 1: Implement new reporting system (APPROVED)
- Task 2: Update documentation (APPROVED)
- Task 3: Security review (APPROVED)

All tasks are approved for execution.', true, NULL, '2025-08-29 18:01:09.255824+00');
INSERT INTO public.email_logs VALUES ('979044fc-89df-4519-9778-8d2186017940', 'incoming', 'General Information', 'info@example.com', '{admin@example.com}', 'General Information

This is just a general information email that should not be processed as any specific type.

Thank you.', true, NULL, '2025-08-29 18:01:09.264027+00');
INSERT INTO public.email_logs VALUES ('2ac53479-db32-4488-b3c8-f094aff36cb5', 'incoming', 'Daily Task Update - 2025-01-15', 'john.doe@example.com', '{pmo@example.com}', '', true, NULL, '2025-08-29 18:01:09.271185+00');
INSERT INTO public.email_logs VALUES ('7c5692b0-804e-461c-9a04-ce5e8df7e5a2', 'incoming', '', 'john.doe@example.com', '{pmo@example.com}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:01:09.278956+00');
INSERT INTO public.email_logs VALUES ('ee7fa2cf-8699-4bb7-86ba-f206f9bd6277', 'incoming', 'Daily Task Update - 2025-01-15', '', '{pmo@example.com}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:01:09.284547+00');
INSERT INTO public.email_logs VALUES ('2f21b750-a3b9-44d2-8394-425ba38b75cc', 'incoming', 'EO - Digital Transformation', 'admin@example.com', '{pmo@example.com}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:01:09.306704+00');
INSERT INTO public.email_logs VALUES ('b10bff49-ab7b-4bd1-a152-a1984c8a1cff', 'incoming', 'Re: PMO Review - EO-12345', 'pmo@example.com', '{pmo@example.com}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:01:09.311577+00');
INSERT INTO public.email_logs VALUES ('c83439cb-e95d-4604-9768-8187531d0487', 'incoming', 'General Information', 'unknown@example.com', '{pmo@example.com}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:01:09.317634+00');
INSERT INTO public.email_logs VALUES ('9648c3e1-4791-454a-aac8-17ef9eb2b260', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:03:01.096279+00');
INSERT INTO public.email_logs VALUES ('a83b0e15-d377-4800-b63e-9437220225f7', 'incoming', 'EO - Digital Transformation Initiative', 'westley.everette@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Executive Order for Digital Transformation Initiative

This executive order outlines the digital transformation requirements for the Department of Labor.

Key directives:
1. Implement new reporting systems
2. Update documentation
3. Conduct security reviews

Please process this executive order and create appropriate tasks.', true, NULL, '2025-08-29 18:03:01.756436+00');
INSERT INTO public.email_logs VALUES ('2a4625d6-17b8-4a69-96f8-983f6a7d6edd', 'incoming', 'Re: PMO Review - EO-12345 - Task Approval', 'kevin.brown@lumenlighthouse.ai', '{westley.everette@lumenlighthouse.ai}', 'PMO Review Response

I have reviewed the tasks for EO-12345 and approve the following tasks:
- Task 1: Implement new reporting system (APPROVED)
- Task 2: Update documentation (APPROVED)
- Task 3: Security review (APPROVED)

All tasks are approved for execution.', true, NULL, '2025-08-29 18:03:01.764261+00');
INSERT INTO public.email_logs VALUES ('c34c4431-8be0-452b-a344-fc92a0991c5f', 'incoming', 'General Information', 'info@example.com', '{admin@example.com}', 'General Information

This is just a general information email that should not be processed as any specific type.

Thank you.', true, NULL, '2025-08-29 18:03:01.77183+00');
INSERT INTO public.email_logs VALUES ('cc0ca599-4985-4947-8125-aba1c97e59ca', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', '', true, NULL, '2025-08-29 18:03:01.778965+00');
INSERT INTO public.email_logs VALUES ('da7956ca-3479-4a17-9c19-b0082467589f', 'incoming', '', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:03:01.786985+00');
INSERT INTO public.email_logs VALUES ('92b6a807-3098-4251-9aaf-dd57edb79f73', 'incoming', 'Daily Task Update - 2025-01-15', '', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:03:01.792432+00');
INSERT INTO public.email_logs VALUES ('b050a2e7-3b2d-44ca-8b81-67d2d9558da7', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:03:01.800084+00');
INSERT INTO public.email_logs VALUES ('7b02b698-b66f-414c-8c34-0083df625712', 'incoming', 'Task Update - Reporting System', 'ayesha.ahsan@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:03:01.805368+00');
INSERT INTO public.email_logs VALUES ('73276ad9-87d2-4067-a618-6816e2499a14', 'incoming', 'EO - Digital Transformation', 'westley.everette@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:03:01.810005+00');
INSERT INTO public.email_logs VALUES ('57b51716-c105-4ba4-8f8f-f0066badcf11', 'incoming', 'Re: PMO Review - EO-12345', 'kevin.brown@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:03:01.816034+00');
INSERT INTO public.email_logs VALUES ('f43f6189-2276-473b-82c9-217e4fe595e2', 'incoming', 'General Information', 'unknown@example.com', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:03:01.821074+00');
INSERT INTO public.email_logs VALUES ('9ff0ee26-f563-4e28-99a5-d7f5917015a1', 'incoming', 'EO - Digital Transformation', 'westley.everette@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', false, NULL, '2025-08-29 18:03:01.980683+00');
INSERT INTO public.email_logs VALUES ('57be74f8-5c94-49b9-98d5-21bfa347868c', 'outgoing', 'PMO Review Required: EO - Digital Transformation Initiative [EO ID: b8cd1182-41f6-4c38-a3b3-02e0d7e99c84]', NULL, '{kevin.brown@lumenlighthouse.ai}', 'Subject EO: EO - Digital Transformation Initiative
EO ID: b8cd1182-41f6-4c38-a3b3-02e0d7e99c84
EO Message-ID: <0ed8e961-09d0-4ee4-b216-166571587e2b@example.com>
Received: 2025-08-29 18:03:01 UTC

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
1 | Implement New Digital Reporting Systems | — | Hibbi Iqbal | — | [Fill Here] | [Fill Here]
2 | Update Departmental Documentation for Digital Transformation | — | Ayesha Ahsan | — | [Fill Here] | [Fill Here]
3 | Conduct Security Reviews of New Digital Systems | — | Robert Springfiled | — | [Fill Here] | [Fill Here]', false, 'b8cd1182-41f6-4c38-a3b3-02e0d7e99c84', '2025-08-29 18:03:05.301781+00');
INSERT INTO public.email_logs VALUES ('0f043571-59cb-4eda-a37f-b67dc96e89f8', 'incoming', 'EO - Digital Transformation Initiative', 'westley.everette@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Executive Order for Digital Transformation Initiative

This executive order outlines the digital transformation requirements for the Department of Labor.

Key directives:
1. Implement new reporting systems
2. Update documentation
3. Conduct security reviews

Please process this executive order and create appropriate tasks.', false, NULL, '2025-08-29 18:03:01.996783+00');
INSERT INTO public.email_logs VALUES ('b57cb309-2ff0-4ec3-bd05-c8b331e29768', 'outgoing', 'PMO Review Required: EO - Digital Transformation [EO ID: ccae689f-6842-4b82-a745-19d5d7e0c659]', NULL, '{kevin.brown@lumenlighthouse.ai}', 'Subject EO: EO - Digital Transformation
EO ID: ccae689f-6842-4b82-a745-19d5d7e0c659
EO Message-ID: <11607f1d-30d6-40a1-90a8-2062af44df29@example.com>
Received: 2025-08-29 18:03:01 UTC

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
1 | Implement New Reporting System | — | Hibbi Iqbal | — | [Fill Here] | [Fill Here]
2 | Update Documentation for Reporting System | — | Hibbi Iqbal | — | [Fill Here] | [Fill Here]
3 | Conduct Security Review of Reporting System | — | Robert Springfiled | — | [Fill Here] | [Fill Here]', false, 'ccae689f-6842-4b82-a745-19d5d7e0c659', '2025-08-29 18:03:05.523423+00');
INSERT INTO public.email_logs VALUES ('248cb0f6-acd2-454d-aa6e-7934f96e19f3', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:08:51.078916+00');
INSERT INTO public.email_logs VALUES ('5accc0c4-af28-47f9-b9bd-d0e9200a6292', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:08:51.812719+00');
INSERT INTO public.email_logs VALUES ('83a0effc-2ddd-4e7f-892c-36749ce9e60c', 'incoming', 'Task Update - Reporting System', 'ayesha.ahsan@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:08:51.823696+00');
INSERT INTO public.email_logs VALUES ('4562bccc-a166-4f25-a30a-7a2687940e86', 'incoming', 'EO - Digital Transformation', 'westley.everette@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:08:51.829766+00');
INSERT INTO public.email_logs VALUES ('eca2eaa1-79fe-4571-b0ca-ae83804f0f27', 'incoming', 'Re: PMO Review - EO-12345', 'kevin.brown@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:08:51.836606+00');
INSERT INTO public.email_logs VALUES ('5a396830-8a7c-479e-9793-b9191d67e148', 'incoming', 'EO - Digital Transformation', 'westley.everette@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', false, NULL, '2025-08-29 18:08:51.836923+00');
INSERT INTO public.email_logs VALUES ('96b22ada-48bc-4de8-8c6d-466a25ab0d27', 'outgoing', 'PMO Review Required: EO - Digital Transformation [EO ID: 4079e80f-781b-44ed-a759-527f97ef87f5]', NULL, '{kevin.brown@lumenlighthouse.ai}', 'Subject EO: EO - Digital Transformation
EO ID: 4079e80f-781b-44ed-a759-527f97ef87f5
EO Message-ID: <aeede9de-89b3-4dce-a511-5bb9270c5725@example.com>
Received: 2025-08-29 18:08:51 UTC

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
1 | Implement New Reporting System | — | Hibbi Iqbal | — | [Fill Here] | [Fill Here]
2 | Update System Documentation | — | Hibbi Iqbal | — | [Fill Here] | [Fill Here]
3 | Conduct Security Review of Reporting System | — | Robert Springfiled | — | [Fill Here] | [Fill Here]', false, '4079e80f-781b-44ed-a759-527f97ef87f5', '2025-08-29 18:08:55.3141+00');
INSERT INTO public.email_logs VALUES ('90646a6e-a24c-4bff-bad7-673a32577cdd', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.

Working on the Implement new reporting system - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. Update documentation will start next week once the system is ready.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:11:28.305211+00');
INSERT INTO public.email_logs VALUES ('b62ecf15-88e3-497d-8c2f-4dd3ae1fce9c', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.', true, NULL, '2025-08-29 18:12:28.224669+00');
INSERT INTO public.email_logs VALUES ('e6dcef4e-9be8-40b8-8019-9bd8fb8ead4f', 'incoming', 'Task Update - Reporting System', 'ayesha.ahsan@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Task Update: Made progress on reporting system.', true, NULL, '2025-08-29 18:12:28.708791+00');
INSERT INTO public.email_logs VALUES ('03e94396-b25b-410b-a9a4-d6f7aa17cbb7', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - All tasks progressing well.', true, NULL, '2025-08-29 18:14:26.540949+00');
INSERT INTO public.email_logs VALUES ('881bb10c-2971-4508-b970-66cfa6fe0289', 'incoming', 'Task Update - Reporting System', 'ayesha.ahsan@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Task Update: Made progress on reporting system.', true, NULL, '2025-08-29 18:14:27.097757+00');
INSERT INTO public.email_logs VALUES ('ae3adfc6-e59b-4bd1-94fc-d0b9c890c834', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - 2025-01-15

Working on the Update Privacy Act System of Records Notices for Treasury Data Sharing - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. 

Also made progress on the Issue Guidance on Data Access for Fraud Prevention - about 40% done, spent 2 hours today.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:18:31.087728+00');
INSERT INTO public.email_logs VALUES ('b6a0b0c2-6a7f-48d9-b3c6-93b68030b800', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - 2025-01-15

Working on the Update Privacy Act System of Records Notices for Treasury Data Sharing - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. 

Also made progress on the Issue Guidance on Data Access for Fraud Prevention - about 40% done, spent 2 hours today.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:21:30.208547+00');
INSERT INTO public.email_logs VALUES ('85b9ed34-5921-466d-bc5e-91ae165239e1', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - 2025-01-15

Working on the Update Privacy Act System of Records Notices for Treasury Data Sharing - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. 

Also made progress on the Issue Guidance on Data Access for Fraud Prevention - about 40% done, spent 2 hours today.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:25:33.270719+00');
INSERT INTO public.email_logs VALUES ('8a8375cd-3499-41ab-be30-26d8409e0ce9', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - 2025-01-15

Working on the Update Privacy Act System of Records Notices for Treasury Data Sharing - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. 

Also made progress on the Issue Guidance on Data Access for Fraud Prevention - about 40% done, spent 2 hours today.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:29:00.75739+00');
INSERT INTO public.email_logs VALUES ('777e618b-ee6f-4cf0-a7bf-59977a2263ee', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - 2025-01-15

Working on the Update Privacy Act System of Records Notices for Treasury Data Sharing - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. 

Also made progress on the Issue Guidance on Data Access for Fraud Prevention - about 40% done, spent 2 hours today.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:29:31.579227+00');
INSERT INTO public.email_logs VALUES ('21a7765d-2e6b-45ad-b589-e95e1da345e4', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - 2025-01-15

Working on the Update Privacy Act System of Records Notices for Treasury Data Sharing - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. 

Also made progress on the Issue Guidance on Data Access for Fraud Prevention - about 40% done, spent 2 hours today.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:30:21.997375+00');
INSERT INTO public.email_logs VALUES ('bcbeee40-e94f-4e3b-9452-828b863c3a7c', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - 2025-01-15

Working on the Update Privacy Act System of Records Notices for Treasury Data Sharing - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. 

Also made progress on the Issue Guidance on Data Access for Fraud Prevention - about 40% done, spent 2 hours today.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:31:05.038335+00');
INSERT INTO public.email_logs VALUES ('fc88300c-80dd-472a-a844-2e144ade3f0c', 'incoming', 'Daily Task Update - 2025-01-15', 'dylan.sachetti@lumenlighthouse.ai', '{kevin.brown@lumenlighthouse.ai}', 'Daily Update - 2025-01-15

Working on the Update Privacy Act System of Records Notices for Treasury Data Sharing - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. 

Also made progress on the Issue Guidance on Data Access for Fraud Prevention - about 40% done, spent 2 hours today.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.', true, NULL, '2025-08-29 18:32:13.874976+00');
INSERT INTO public.email_logs VALUES ('83cdf283-b20a-4664-bfe3-0eb372ce8a90', 'incoming', 'Task Update', 'kevin.brown@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', 'Working on the Issue Guidance for Core Financial System Consolidation (CFO Act Agencies) - about 75% complete, spent 4 hours today. Drafting the final guidance document and coordinating with Treasury stakeholders for review. Need to finalize the implementation timeline section.
Made good progress on the Submit Treasury Implementation Report to President - about 60% done, spent 3 hours today. Completed the executive summary and started working on the progress tracking framework. Need to gather data from various agencies for the 180-day implementation timeline.
Also worked on the Assess and Revoke Delegated Disbursing Authority as Appropriate - about 45% complete, spent 2.5 hours today. Conducted initial assessment of current delegated authorities and identified agencies that may need revocation notices. Need to schedule stakeholder meetings to discuss findings.
The Ensure Use of Standard Financial Management Solutions task is about 30% done, spent 2 hours today. Started mapping current financial management solutions across CFO Act agencies and identifying gaps. Need to coordinate with the Financial Management Marketplace team.
Finally, made some progress on the Issue Guidance for Non-CFO Act Agency Financial Service Consolidation - about 25% complete, spent 1.5 hours today. Began drafting the guidance framework and identifying key stakeholders from non-CFO Act agencies.
Overall Status: Good progress across all tasks. Main blockers are stakeholder coordination and data gathering from agencies. Need to schedule follow-up meetings with Treasury and agency representatives next week.
Hours Spent Today: 13 hours total
Key Achievements: Completed executive summary for implementation report, drafted core guidance document, and initiated agency assessments.', true, NULL, '2025-08-29 19:14:34.004386+00');
INSERT INTO public.email_logs VALUES ('1b6b474e-e41f-4772-b760-7ccc221196ba', 'incoming', 'Daily Task Update', 'hibbi.iqbal@lumenlighthouse.ai', '{admin@example.com}', 'Here are my daily updates:

Task: Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)
Status: In Progress
Progress: 75%
Notes: Completed authentication module, working on authorization
Hours Spent: 6
Blockers: Need clarification on role permissions
Risks: Timeline might slip if requirements change', true, NULL, '2025-08-29 23:10:23.860476+00');
INSERT INTO public.email_logs VALUES ('475079ff-4d0e-4203-997b-95653e091390', 'incoming', 'Daily Task Update', 'hibbi.iqbal@lumenlighthouse.ai', '{admin@example.com}', 'Here are my daily updates:

Task: Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)
Status: Completed
Progress: 100%
Notes: Finished all work on this task
Hours Spent: 8
Blockers: None
Risks: None', true, NULL, '2025-08-29 23:12:30.43604+00');
INSERT INTO public.email_logs VALUES ('88c750da-44d5-4d47-9cc2-00bd298fc7c2', 'incoming', 'Task Update', 'Hibbi.Iqbal@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', 'Working on the Issue Guidance for Core Financial System Consolidation (CFO Act Agencies) - about 75% complete, spent 4 hours today. Drafting the final guidance document and coordinating with Treasury stakeholders for review. Need to finalize the implementation timeline section.
Made good progress on the Submit Treasury Implementation Report to President - about 60% done, spent 3 hours today. Completed the executive summary and started working on the progress tracking framework. Need to gather data from various agencies for the 180-day implementation timeline.
Also worked on the Assess and Revoke Delegated Disbursing Authority as Appropriate - about 45% complete, spent 2.5 hours today. Conducted initial assessment of current delegated authorities and identified agencies that may need revocation notices. Need to schedule stakeholder meetings to discuss findings.
The Ensure Use of Standard Financial Management Solutions task is about 30% done, spent 2 hours today. Started mapping current financial management solutions across CFO Act agencies and identifying gaps. Need to coordinate with the Financial Management Marketplace team.
Finally, made some progress on the Issue Guidance for Non-CFO Act Agency Financial Service Consolidation - about 25% complete, spent 1.5 hours today. Began drafting the guidance framework and identifying key stakeholders from non-CFO Act agencies.
Overall Status: Good progress across all tasks. Main blockers are stakeholder coordination and data gathering from agencies. Need to schedule follow-up meetings with Treasury and agency representatives next week.
Hours Spent Today: 13 hours total
Key Achievements: Completed executive summary for implementation report, drafted core guidance document, and initiated agency assessments.', true, NULL, '2025-08-29 19:15:50.522256+00');
INSERT INTO public.email_logs VALUES ('612fcb03-a4a0-4bbe-958e-270ee63974c6', 'incoming', 'Task Update', 'Hibbi.Iqbal@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', 'Working on the Issue Guidance for Core Financial System Consolidation (CFO Act Agencies) - about 75% complete, spent 4 hours today. Drafting the final guidance document and coordinating with Treasury stakeholders for review. Need to finalize the implementation timeline section.
Made good progress on the Submit Treasury Implementation Report to President - about 60% done, spent 3 hours today. Completed the executive summary and started working on the progress tracking framework. Need to gather data from various agencies for the 180-day implementation timeline.
Also worked on the Assess and Revoke Delegated Disbursing Authority as Appropriate - about 45% complete, spent 2.5 hours today. Conducted initial assessment of current delegated authorities and identified agencies that may need revocation notices. Need to schedule stakeholder meetings to discuss findings.
The Ensure Use of Standard Financial Management Solutions task is about 30% done, spent 2 hours today. Started mapping current financial management solutions across CFO Act agencies and identifying gaps. Need to coordinate with the Financial Management Marketplace team.
Finally, made some progress on the Issue Guidance for Non-CFO Act Agency Financial Service Consolidation - about 25% complete, spent 1.5 hours today. Began drafting the guidance framework and identifying key stakeholders from non-CFO Act agencies.
Overall Status: Good progress across all tasks. Main blockers are stakeholder coordination and data gathering from agencies. Need to schedule follow-up meetings with Treasury and agency representatives next week.
Hours Spent Today: 13 hours total
Key Achievements: Completed executive summary for implementation report, drafted core guidance document, and initiated agency assessments.', true, NULL, '2025-08-29 19:19:51.297536+00');
INSERT INTO public.email_logs VALUES ('c8efd20f-4d77-4179-a084-89f7a7febbfb', 'incoming', 'Task Update', 'Hibbi.Iqbal@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', 'Working on the Issue Guidance for Core Financial System Consolidation (CFO Act Agencies) - about 75% complete, spent 4 hours today. Drafting the final guidance document and coordinating with Treasury stakeholders for review. Need to finalize the implementation timeline section.
Made good progress on the Submit Treasury Implementation Report to President - about 60% done, spent 3 hours today. Completed the executive summary and started working on the progress tracking framework. Need to gather data from various agencies for the 180-day implementation timeline.
Also worked on the Assess and Revoke Delegated Disbursing Authority as Appropriate - about 45% complete, spent 2.5 hours today. Conducted initial assessment of current delegated authorities and identified agencies that may need revocation notices. Need to schedule stakeholder meetings to discuss findings.
The Ensure Use of Standard Financial Management Solutions task is about 30% done, spent 2 hours today. Started mapping current financial management solutions across CFO Act agencies and identifying gaps. Need to coordinate with the Financial Management Marketplace team.
Finally, made some progress on the Issue Guidance for Non-CFO Act Agency Financial Service Consolidation - about 25% complete, spent 1.5 hours today. Began drafting the guidance framework and identifying key stakeholders from non-CFO Act agencies.
Overall Status: Good progress across all tasks. Main blockers are stakeholder coordination and data gathering from agencies. Need to schedule follow-up meetings with Treasury and agency representatives next week.
Hours Spent Today: 13 hours total
Key Achievements: Completed executive summary for implementation report, drafted core guidance document, and initiated agency assessments.', true, NULL, '2025-08-29 20:12:32.981208+00');
INSERT INTO public.email_logs VALUES ('6018f778-55ea-4210-b7af-c0e5ddf24541', 'incoming', 'Task update', 'Hibbi.Iqbal@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', '	Working on the Issue Guidance for Core Financial System Consolidation (CFO Act Agencies) - about 75% complete, spent 4 hours today. Drafting the final guidance document and coordinating with Treasury stakeholders for review. Need to finalize the implementation timeline section.
Made good progress on the Submit Treasury Implementation Report to President - about 60% done, spent 3 hours today. Completed the executive summary and started working on the progress tracking framework. Need to gather data from various agencies for the 180-day implementation timeline.
Also worked on the Assess and Revoke Delegated Disbursing Authority as Appropriate - about 45% complete, spent 2.5 hours today. Conducted initial assessment of current delegated authorities and identified agencies that may need revocation notices. Need to schedule stakeholder meetings to discuss findings.
The Ensure Use of Standard Financial Management Solutions task is about 30% done, spent 2 hours today. Started mapping current financial management solutions across CFO Act agencies and identifying gaps. Need to coordinate with the Financial Management Marketplace team.
Finally, made some progress on the Issue Guidance for Non-CFO Act Agency Financial Service Consolidation - about 25% complete, spent 1.5 hours today. Began drafting the guidance framework and identifying key stakeholders from non-CFO Act agencies.
Overall Status: Good progress across all tasks. Main blockers are stakeholder coordination and data gathering from agencies. Need to schedule follow-up meetings with Treasury and agency representatives next week.
Hours Spent Today: 13 hours total
Key Achievements: Completed executive summary for implementation report, drafted core guidance document, and initiated agency assessments.', true, NULL, '2025-08-29 20:13:39.789998+00');
INSERT INTO public.email_logs VALUES ('f703665d-b172-44ca-852b-27d767b66690', 'incoming', 'Daily Task Update - 2025-01-16', 'dylan.sachetti@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', 'Daily Update - 2025-01-16

Made significant progress on the Issue Guidance on Data Access for Fraud Prevention - now 85% complete, spent 6 hours today. Finalized the technical specifications and submitted for legal review. Expecting feedback by end of week.

The Update Privacy Act System of Records Notices for Treasury Data Sharing is 90% done, spent 4 hours today. Completed the draft notices and sent to Treasury for final approval. Should be ready for publication next week.

Also worked on the Develop Transparent Exemption Request Process for Payment Verification - about 70% complete, spent 3 hours today. Created the process flow and started drafting the exemption criteria. Need stakeholder input on approval thresholds.

The Submit Agency Compliance Plan to OMB Director task is 50% done, spent 2 hours today. Compiled initial compliance data and started drafting the plan structure. Need to coordinate with other agencies for comprehensive data.

Finally, made some progress on the Update and Issue Payment Verification Guidance in Consultation with OMB Director - about 35% complete, spent 1.5 hours today. Began drafting the guidance framework and identified key consultation points.

Overall Status: Excellent progress across all tasks. Main focus is on completing the fraud prevention guidance and privacy notices. Need to schedule stakeholder meetings for exemption process.

Hours Spent Today: 16.5 hours total
Key Achievements: Completed technical specs for fraud prevention, finalized privacy notices, and established exemption process framework.', true, NULL, '2025-08-29 20:21:47.731441+00');
INSERT INTO public.email_logs VALUES ('a78d5b0b-f83c-4163-8946-76bc22cc2f21', 'incoming', 'Task Update - 2025-01-16', 'hibbi.iqbal@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', 'Progress Update - 2025-01-16

The Issue Guidance for Core Financial System Consolidation (CFO Act Agencies) is now 90% complete, spent 5 hours today. Finalized the guidance document and submitted for Treasury review. Awaiting final approval before publication.

Completed the Submit Treasury Implementation Report to President - 100% done, spent 2 hours today for final review and submission. Report has been delivered to the President office as required.

Made good progress on the Assess and Revoke Delegated Disbursing Authority as Appropriate - now 75% complete, spent 4 hours today. Completed stakeholder meetings and prepared revocation notices for identified agencies. Ready to issue notices next week.

The Ensure Use of Standard Financial Management Solutions task is 60% done, spent 3 hours today. Successfully coordinated with the Financial Management Marketplace team and identified all gaps. Started implementation planning.

The Issue Guidance for Non-CFO Act Agency Financial Service Consolidation is 45% complete, spent 2.5 hours today. Drafted the guidance framework and identified all non-CFO Act agencies. Need to schedule consultation meetings.

Overall Status: Strong progress with one task completed. Focus on finalizing CFO Act guidance and issuing revocation notices. Need to accelerate non-CFO Act agency coordination.

Hours Spent Today: 16.5 hours total
Key Achievements: Completed implementation report, finalized CFO Act guidance, and prepared revocation notices.', true, NULL, '2025-08-29 20:23:41.860264+00');
INSERT INTO public.email_logs VALUES ('ae76d937-eee7-4671-b84a-236146309a51', 'incoming', 'Update on Issue Guidance on Data Access for Fraud Prevention', 'dylan.sachetti@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', 'Task Update: Issue Guidance on Data Access for Fraud Prevention

Current Status: 95% Complete

Progress Made Today:
- Finalized all technical specifications
- Completed legal review and incorporated feedback
- Submitted for final Treasury approval
- Prepared implementation timeline
- Created training materials for agencies

Hours Spent: 8 hours

Blockers: None - awaiting final approval

Next Steps:
- Receive Treasury approval (expected by Friday)
- Publish guidance document
- Schedule agency training sessions
- Monitor implementation progress

Risks: Minimal - approval process is standard

Summary: Task is essentially complete pending final approval. All deliverables are ready and implementation planning is in place.', true, NULL, '2025-08-29 20:24:01.748705+00');
INSERT INTO public.email_logs VALUES ('3d3a0682-2c8a-4d1e-8145-1b38f5898020', 'incoming', 'Detailed Task Updates - 2025-01-16', 'hibbi.iqbal@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', 'Detailed Task Updates - 2025-01-16

Task: Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)
Status: 90% Complete
Hours: 5 hours today
Progress: Finalized guidance document, submitted for Treasury review
Blockers: Awaiting Treasury approval
Next Actions: Publish upon approval, schedule agency briefings

Task: Submit Treasury Implementation Report to President
Status: 100% Complete
Hours: 2 hours today
Progress: Final review and submission completed
Blockers: None
Next Actions: Monitor for any follow-up requests

Task: Assess and Revoke Delegated Disbursing Authority as Appropriate
Status: 75% Complete
Hours: 4 hours today
Progress: Completed stakeholder meetings, prepared revocation notices
Blockers: None
Next Actions: Issue notices to identified agencies

Task: Ensure Use of Standard Financial Management Solutions
Status: 60% Complete
Hours: 3 hours today
Progress: Coordinated with Marketplace team, identified gaps
Next Actions: Begin implementation planning

Task: Issue Guidance for Non-CFO Act Agency Financial Service Consolidation
Status: 45% Complete
Hours: 2.5 hours today
Progress: Drafted framework, identified agencies
Blockers: Need stakeholder coordination
Next Actions: Schedule consultation meetings

Total Hours Today: 16.5 hours', true, NULL, '2025-08-29 20:24:43.259974+00');
INSERT INTO public.email_logs VALUES ('7db240f8-204c-48a8-b190-5b06e0d06331', 'incoming', 'Late Task Update - 2025-01-16', 'dylan.sachetti@lumenlighthouse.ai', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', 'Late Update - 2025-01-16

Working late to catch up on the Update Privacy Act System of Records Notices for Treasury Data Sharing - now 95% complete, spent 3 hours this evening. Completed final revisions based on Treasury feedback. Ready for publication tomorrow.

Also made progress on the Issue Guidance on Data Access for Fraud Prevention - about 90% done, spent 2 hours this evening. Finalized technical specifications and submitted for legal review. Expecting approval by end of week.

The Develop Transparent Exemption Request Process for Payment Verification is 80% complete, spent 1.5 hours this evening. Completed the process flow and exemption criteria. Ready for stakeholder review.

Overall Status: Good progress despite late start. Main blockers were earlier meetings and coordination calls. All tasks on track for completion.

Hours Spent Today: 6.5 hours total
Note: This is a late update due to earlier commitments.', true, NULL, '2025-08-29 20:25:04.061221+00');
INSERT INTO public.email_logs VALUES ('f58a0d9b-0cba-4f51-ad49-9a69ca68c8a2', 'incoming', 'General Inquiry', 'unknown.user@example.com', '{"EO 14249 Email <eo.14249@lumenlighthouse.ai>"}', 'Hello,

I have a general question about the Executive Order implementation process.

Best regards,
Unknown User', true, NULL, '2025-08-29 20:26:39.960097+00');
INSERT INTO public.email_logs VALUES ('70815a26-cb38-47d9-b4cf-a1559a01e80c', 'incoming', 'Daily Task Update', 'hibbi.iqbal@lumenlighthouse.ai', '{admin@example.com}', 'Here are my daily updates:

Task: Develop API endpoints for user management
Status: In Progress
Progress: 75%
Notes: Completed authentication module, working on authorization
Hours Spent: 6
Blockers: Need clarification on role permissions
Risks: Timeline might slip if requirements change', true, NULL, '2025-08-29 23:08:34.268941+00');


--
-- Data for Name: attachments; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.users VALUES ('1e882225-d379-40a0-a3af-2ba90f6ab76a', 'Kevin Brown', 'kevin.brown@lumenlighthouse.ai', 'reviewer', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Deputy CFO', '$2b$12$5.KYuZOoFBHC0ApmmQj1He8u0fIaU/bw3aV1d60R2yioPMiY5zgBK');
INSERT INTO public.users VALUES ('e9df20f5-8a10-4261-be4f-584c10c60d74', 'Westley Everette', 'westley.everette@lumenlighthouse.ai', 'admin', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Associate Deputy CFO', '$2b$12$o7p66.NF8VB7GjlxHqB0iu2lAO45E0X79jI78kR2zFq096nslTmJe');
INSERT INTO public.users VALUES ('6a445645-3029-4b62-aac7-10cd7e6558d0', 'Dylan Sachetti', 'dylan.sachetti@lumenlighthouse.ai', 'executor', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Director of Compliance', '$2b$12$JM5JngFTW8vA8Mhh1L6BkuFVsk0j9.AbHLKdNvree45F0Ln8sp7BG');
INSERT INTO public.users VALUES ('783a8139-367f-486c-9c19-05b9291cdf9a', 'Ayesha Ahsan', 'ayesha.ahsan@lumenlighthouse.ai', 'executor', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Director of Division of Business Process Improvement', '$2b$12$ffcIGEdUyCMHSXm0jyFzYe.Zuz6zSTpJ9ANMpHOhrWR/okg2vFsDm');
INSERT INTO public.users VALUES ('a7fa1461-11e3-4f91-ae42-8e4b85ed5a8e', 'Jack Smith', 'jack.smith@lumenlighthouse.ai', 'admin', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'CFO', '$2b$12$sNiRxauwjeeSWLPX6TTvtOtuX4qixatsd4AIFifKoN8StX3CDeK5.');
INSERT INTO public.users VALUES ('5814f396-9360-41ad-adda-cd15afcbc88f', 'Hibbi Iqbal', 'hibbi.iqbal@lumenlighthouse.ai', 'executor', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Director of Financial Reporting', '$2b$12$r9HjknKVSWbMoCdgtbSxX.UcA85Ge.L0O90xFeIuMPCOkK.INLC8m');
INSERT INTO public.users VALUES ('e24c7d45-75b2-4f90-9b14-dcde4fd281d7', 'Sophia Carty', 'sophia.carty@lumenlighthouse.ai', 'executor', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Director of Accounting', '$2b$12$n8znnH0tIo14KEBT0OBmBORcY3EYXZ2G5vN.L/qOpBHIxFLRVD/na');
INSERT INTO public.users VALUES ('9e195007-1ca2-453e-b3d7-b6bbf32d0185', 'Robert Springfiled', 'robert.springfiled@lumenlighthouse.ai', 'executor', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Director of Security and Technology', '$2b$12$e5YQ0Z57t3.5QRM.k7Y7geYdsoozsuCvk8tvYQkRsYcKERI57lRNi');
INSERT INTO public.users VALUES ('0a50508d-2861-46b1-ba89-c77126606c42', 'Micheal Kim', 'micheal.kim@lumenlighthouse.ai', 'executor', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Director of Travel Management', '$2b$12$yCbhRtywqP0qijz44p6xCufL7.IMUmJAZrRmin5MViaVA79Ms2RqW');
INSERT INTO public.users VALUES ('da7d66bd-e296-47fb-92f0-cd5b93b15ba4', 'Zacira Copper', 'zacira.copper@lumenlighthouse.ai', 'executor', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Supervisor (reports to Ayesha)', '$2b$12$Uo2i/En.K1lglebIK3VNRufCaCJSg/AW35eCX/49x5gedsDqvaDim');
INSERT INTO public.users VALUES ('25038ac4-5da6-4634-b210-cff180d5bd9d', 'Jada Mccray', 'jada.mccray@lumenlighthouse.ai', 'executor', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Lead Accountant (Reports to Zacira)', '$2b$12$DgScEPp7FW2ov1wvRJ14h.DPtlc.XaJH74qbvHTru7PNcvMRpfaQa');
INSERT INTO public.users VALUES ('0c9067b4-72f7-4285-84a1-488352d4d956', 'Jose Flores', 'jose.flores@lumenlighthouse.ai', 'executor', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Lead Accountant (Reports to Zacira)', '$2b$12$8qMJPtR17BDeKlcDNYAqbuSk8o.1cq2263809t0LvYcSmz/n9UOdC');
INSERT INTO public.users VALUES ('f52c4d2e-a1c6-4f3f-9a13-ad948e96d76e', 'EO 14249 Email', 'eo.14249@lumenlighthouse.ai', 'reviewer', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'EO 14249 Email', '$2b$12$6Cl5Ldl9.mZpVRDKs5G1juF/Q7.LilhdFQhiCCO1TeUJ1jxkJy84.');
INSERT INTO public.users VALUES ('bc8eb760-3ffb-4e93-b197-773851b69c33', 'EO 14247 Email', 'eo.14247@lumenlighthouse.ai', 'reviewer', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'EO 14247 Email', '$2b$12$Zs7HEYHsZC3lhciM1c5PaufQ4TOKACKxqXZby8.RXtxcOKkCuxk46');
INSERT INTO public.users VALUES ('9ac8c65f-d0fe-42d0-aaff-29e5531ca2f5', 'Sarah Johnson', 'sarah.johnson@lumenlighthouse.ai', 'reviewer', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Senior Project Manager', '$2b$12$97LEysJmeZYPHcWf1f5Gyu57J.VXMUyNQepb..8EPpG7K.R1JawLK');
INSERT INTO public.users VALUES ('2c2ca07e-b379-46f1-99c3-b677f5fdbe79', 'David Chen', 'david.chen@lumenlighthouse.ai', 'reviewer', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Compliance Manager', '$2b$12$8TWXh4OeXb1a07sOHxOGMetHzlBHMxYK8hl0QQnFPAGCeuHuRADny');
INSERT INTO public.users VALUES ('bf42c44e-3a96-42d4-8c82-d87115bfa2d8', 'Maria Rodriguez', 'maria.rodriguez@lumenlighthouse.ai', 'reviewer', true, '2025-08-28 17:21:23.407379+00', '2025-08-28 17:21:23.407379+00', 'Financial Operations Manager', '$2b$12$RVFqOmsO6kkm1x.IanEIr.N5IKP/sOHqodc310R5NNtOZ3/PPg5da');


--
-- Data for Name: auth_tokens; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: daily_eo_summaries; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.daily_eo_summaries VALUES ('b7d06bba-5396-436a-9e97-8839924838dc', '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-29', 'Daily Progress Summary for EO: Modernize Workforce Data

Tasks Updated: 22
- Completed: 6
- In Progress: 16
- Blocked: 0

Overall Progress: 6/22 tasks completed', '["Need to coordinate with the Financial Management Marketplace team", "Need stakeholder coordination", "Earlier meetings and coordination calls delayed progress earlier in the day", "Need to coordinate with other agencies for comprehensive data", "Security review pending until system implementation progresses", "Finalizing implementation timeline section", "Awaiting final approval from Treasury before publication", "Pending PMO approval", "Need stakeholder input on approval thresholds", "Earlier meetings and coordination calls caused delays earlier in the day.", "Stakeholder coordination", "Consultation meetings with non-CFO Act agencies have not yet been scheduled.", "Awaiting Treasury approval", "Need to gather data from various agencies", "Need to schedule stakeholder meetings to discuss findings"]', '["Potential delay if Treasury approval is not received promptly", "Potential delays if stakeholder meetings are not scheduled promptly", "Potential delays if coordination with the Financial Management Marketplace team is not timely", "Potential delay if legal review takes longer than expected.", "Delays due to pending approvals", "Implementation timeline may be delayed if not finalized soon", "Potential delays if coordination with other agencies is not timely", "Delays in scheduling or conducting agency consultations may slow overall progress.", "Potential delays due to difficulty in coordinating with non-CFO Act agency stakeholders", "Potential delays if security review is not completed in time", "Potential delays if stakeholder input is not received promptly", "Potential delays if Treasury stakeholder feedback is not received promptly", "Potential delays in data collection from agencies could impact the 180-day timeline"]', 'null', '[]', 22, 22, false, NULL, '2025-08-29 20:35:43.792431+00', '2025-08-29 20:35:43.792431+00');
INSERT INTO public.daily_eo_summaries VALUES ('6bef094f-010d-4e94-9e95-87a55e218196', '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-29', 'Daily Progress Summary for EO: Modernize Workforce Data

Tasks Updated: 22
- Completed: 6
- In Progress: 16
- Blocked: 0

Overall Progress: 6/22 tasks completed', '["Need to coordinate with the Financial Management Marketplace team", "Need stakeholder coordination", "Earlier meetings and coordination calls delayed progress earlier in the day", "Need to coordinate with other agencies for comprehensive data", "Security review pending until system implementation progresses", "Finalizing implementation timeline section", "Awaiting final approval from Treasury before publication", "Pending PMO approval", "Need stakeholder input on approval thresholds", "Earlier meetings and coordination calls caused delays earlier in the day.", "Stakeholder coordination", "Consultation meetings with non-CFO Act agencies have not yet been scheduled.", "Awaiting Treasury approval", "Need to gather data from various agencies", "Need to schedule stakeholder meetings to discuss findings"]', '["Potential delay if Treasury approval is not received promptly", "Potential delays if stakeholder meetings are not scheduled promptly", "Potential delays if coordination with the Financial Management Marketplace team is not timely", "Potential delay if legal review takes longer than expected.", "Delays due to pending approvals", "Implementation timeline may be delayed if not finalized soon", "Potential delays if coordination with other agencies is not timely", "Delays in scheduling or conducting agency consultations may slow overall progress.", "Potential delays due to difficulty in coordinating with non-CFO Act agency stakeholders", "Potential delays if security review is not completed in time", "Potential delays if stakeholder input is not received promptly", "Potential delays if Treasury stakeholder feedback is not received promptly", "Potential delays in data collection from agencies could impact the 180-day timeline"]', 'null', '[]', 22, 22, false, NULL, '2025-08-29 20:44:09.774746+00', '2025-08-29 20:44:09.774746+00');
INSERT INTO public.daily_eo_summaries VALUES ('dfdf37ab-502e-430a-b48a-4be28805eda2', '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-29', 'Daily Progress Summary for EO: Modernize Workforce Data

Tasks Updated: 22
- Completed: 6
- In Progress: 16
- Blocked: 0

Overall Progress: 6/22 tasks completed', '["Awaiting final approval from Treasury before publication", "Stakeholder coordination", "Need to gather data from various agencies", "Need to schedule stakeholder meetings to discuss findings", "Earlier meetings and coordination calls delayed progress earlier in the day", "Security review pending until system implementation progresses", "Finalizing implementation timeline section", "Need stakeholder coordination", "Awaiting Treasury approval", "Consultation meetings with non-CFO Act agencies have not yet been scheduled.", "Pending PMO approval", "Need to coordinate with the Financial Management Marketplace team", "Need stakeholder input on approval thresholds", "Need to coordinate with other agencies for comprehensive data", "Earlier meetings and coordination calls caused delays earlier in the day."]', '["Potential delay if legal review takes longer than expected.", "Potential delays if coordination with other agencies is not timely", "Potential delays if stakeholder meetings are not scheduled promptly", "Potential delays if stakeholder input is not received promptly", "Potential delays due to difficulty in coordinating with non-CFO Act agency stakeholders", "Potential delays in data collection from agencies could impact the 180-day timeline", "Potential delays if security review is not completed in time", "Delays due to pending approvals", "Potential delays if coordination with the Financial Management Marketplace team is not timely", "Potential delays if Treasury stakeholder feedback is not received promptly", "Delays in scheduling or conducting agency consultations may slow overall progress.", "Implementation timeline may be delayed if not finalized soon", "Potential delay if Treasury approval is not received promptly"]', 'null', '[]', 22, 22, false, NULL, '2025-08-29 20:46:27.818575+00', '2025-08-29 20:46:27.818575+00');
INSERT INTO public.daily_eo_summaries VALUES ('d7e1ea1b-0e73-44f5-9b9f-7da2094ae54e', '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-29', 'Daily Progress Summary for EO: Modernize Workforce Data

Tasks Updated: 22
- Completed: 6
- In Progress: 16
- Blocked: 0

Overall Progress: 6/22 tasks completed', '["Awaiting final approval from Treasury before publication", "Stakeholder coordination", "Need to gather data from various agencies", "Need to schedule stakeholder meetings to discuss findings", "Earlier meetings and coordination calls delayed progress earlier in the day", "Security review pending until system implementation progresses", "Finalizing implementation timeline section", "Need stakeholder coordination", "Awaiting Treasury approval", "Consultation meetings with non-CFO Act agencies have not yet been scheduled.", "Pending PMO approval", "Need to coordinate with the Financial Management Marketplace team", "Need stakeholder input on approval thresholds", "Need to coordinate with other agencies for comprehensive data", "Earlier meetings and coordination calls caused delays earlier in the day."]', '["Potential delay if legal review takes longer than expected.", "Potential delays if coordination with other agencies is not timely", "Potential delays if stakeholder meetings are not scheduled promptly", "Potential delays if stakeholder input is not received promptly", "Potential delays due to difficulty in coordinating with non-CFO Act agency stakeholders", "Potential delays in data collection from agencies could impact the 180-day timeline", "Potential delays if security review is not completed in time", "Delays due to pending approvals", "Potential delays if coordination with the Financial Management Marketplace team is not timely", "Potential delays if Treasury stakeholder feedback is not received promptly", "Delays in scheduling or conducting agency consultations may slow overall progress.", "Implementation timeline may be delayed if not finalized soon", "Potential delay if Treasury approval is not received promptly"]', 'null', '[]', 22, 22, false, NULL, '2025-08-29 20:48:45.560524+00', '2025-08-29 20:48:45.560524+00');
INSERT INTO public.daily_eo_summaries VALUES ('7c449f7b-d139-4247-bb7d-7f5439e125ab', '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-29', 'Daily Progress Summary for EO: Modernize Workforce Data

Tasks Updated: 22
- Completed: 6
- In Progress: 16
- Blocked: 0

Overall Progress: 6/22 tasks completed', '["Need stakeholder coordination", "Need stakeholder input on approval thresholds", "Consultation meetings with non-CFO Act agencies have not yet been scheduled.", "Awaiting final approval from Treasury before publication", "Awaiting Treasury approval", "Need to schedule stakeholder meetings to discuss findings", "Need to coordinate with other agencies for comprehensive data", "Pending PMO approval", "Need to coordinate with the Financial Management Marketplace team", "Need to gather data from various agencies", "Stakeholder coordination", "Finalizing implementation timeline section", "Earlier meetings and coordination calls caused delays earlier in the day.", "Earlier meetings and coordination calls delayed progress earlier in the day", "Security review pending until system implementation progresses"]', '["Potential delays if Treasury stakeholder feedback is not received promptly", "Potential delays if stakeholder input is not received promptly", "Implementation timeline may be delayed if not finalized soon", "Potential delay if Treasury approval is not received promptly", "Delays in scheduling or conducting agency consultations may slow overall progress.", "Potential delays if coordination with the Financial Management Marketplace team is not timely", "Potential delays in data collection from agencies could impact the 180-day timeline", "Delays due to pending approvals", "Potential delays due to difficulty in coordinating with non-CFO Act agency stakeholders", "Potential delays if security review is not completed in time", "Potential delay if legal review takes longer than expected.", "Potential delays if stakeholder meetings are not scheduled promptly", "Potential delays if coordination with other agencies is not timely"]', 'null', '[]', 22, 22, true, '2025-08-29 20:49:26.539258+00', '2025-08-29 20:49:24.085524+00', '2025-08-29 20:49:26.538739+00');
INSERT INTO public.daily_eo_summaries VALUES ('e69b5294-fd28-4cd6-a8b9-cf673c7316fc', '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-29', 'Daily Progress Summary for EO: Modernize Workforce Data

Tasks Updated: 22
- Completed: 6
- In Progress: 16
- Blocked: 0

Overall Progress: 6/22 tasks completed', '["Consultation meetings with non-CFO Act agencies have not yet been scheduled.", "Earlier meetings and coordination calls caused delays earlier in the day.", "Need to coordinate with other agencies for comprehensive data", "Need to coordinate with the Financial Management Marketplace team", "Awaiting final approval from Treasury before publication", "Stakeholder coordination", "Finalizing implementation timeline section", "Awaiting Treasury approval", "Need to gather data from various agencies", "Need stakeholder input on approval thresholds", "Earlier meetings and coordination calls delayed progress earlier in the day", "Pending PMO approval", "Need stakeholder coordination", "Need to schedule stakeholder meetings to discuss findings", "Security review pending until system implementation progresses"]', '["Potential delay if legal review takes longer than expected.", "Delays in scheduling or conducting agency consultations may slow overall progress.", "Potential delays if coordination with other agencies is not timely", "Potential delays if coordination with the Financial Management Marketplace team is not timely", "Potential delay if Treasury approval is not received promptly", "Potential delays if stakeholder meetings are not scheduled promptly", "Potential delays due to difficulty in coordinating with non-CFO Act agency stakeholders", "Implementation timeline may be delayed if not finalized soon", "Potential delays if stakeholder input is not received promptly", "Potential delays if security review is not completed in time", "Delays due to pending approvals", "Potential delays if Treasury stakeholder feedback is not received promptly", "Potential delays in data collection from agencies could impact the 180-day timeline"]', 'null', '[]', 22, 22, true, '2025-08-29 22:52:01.760358+00', '2025-08-29 22:51:59.363492+00', '2025-08-29 22:52:01.75899+00');
INSERT INTO public.daily_eo_summaries VALUES ('e71007ac-04d8-456d-968c-a63e539e7115', '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-29', 'Daily Progress Summary for EO: Modernize Workforce Data

Tasks Updated: 22
- Completed: 6
- In Progress: 16
- Blocked: 0

Overall Progress: 6/22 tasks completed', '["Need to schedule stakeholder meetings to discuss findings", "Need to coordinate with the Financial Management Marketplace team", "Earlier meetings and coordination calls delayed progress earlier in the day", "Need to gather data from various agencies", "Need stakeholder coordination", "Finalizing implementation timeline section", "Pending PMO approval", "Awaiting Treasury approval", "Need to coordinate with other agencies for comprehensive data", "Stakeholder coordination", "Security review pending until system implementation progresses", "Need stakeholder input on approval thresholds", "Awaiting final approval from Treasury before publication", "Earlier meetings and coordination calls caused delays earlier in the day.", "Consultation meetings with non-CFO Act agencies have not yet been scheduled."]', '["Delays due to pending approvals", "Potential delays if coordination with other agencies is not timely", "Potential delay if Treasury approval is not received promptly", "Potential delays if security review is not completed in time", "Potential delays if stakeholder meetings are not scheduled promptly", "Potential delays if stakeholder input is not received promptly", "Potential delays if coordination with the Financial Management Marketplace team is not timely", "Potential delays if Treasury stakeholder feedback is not received promptly", "Potential delays due to difficulty in coordinating with non-CFO Act agency stakeholders", "Potential delays in data collection from agencies could impact the 180-day timeline", "Implementation timeline may be delayed if not finalized soon", "Delays in scheduling or conducting agency consultations may slow overall progress.", "Potential delay if legal review takes longer than expected."]', 'null', '[]', 22, 22, true, '2025-08-29 23:00:21.23092+00', '2025-08-29 23:00:19.722029+00', '2025-08-29 23:00:21.230561+00');
INSERT INTO public.daily_eo_summaries VALUES ('3c323266-72e2-40ce-96a1-05fac533eef4', '8fd95066-1662-4482-b1f8-3801f037f356', '2025-08-29', 'Daily Progress Summary for EO: Modernize Workforce Data

Tasks Updated: 20
- Completed: 6
- In Progress: 14
- Blocked: 0

Overall Progress: 6/20 tasks completed', '["Need to coordinate with the Financial Management Marketplace team", "Need stakeholder input on approval thresholds", "Security review pending until system implementation progresses", "Need to coordinate with other agencies for comprehensive data", "Earlier meetings and coordination calls delayed progress earlier in the day", "Pending PMO approval", "Stakeholder coordination", "Need stakeholder coordination", "Consultation meetings with non-CFO Act agencies have not yet been scheduled.", "Need to schedule stakeholder meetings to discuss findings", "Need to gather data from various agencies", "Earlier meetings and coordination calls caused delays earlier in the day."]', '["Potential delays if stakeholder input is not received promptly", "Potential delays if coordination with other agencies is not timely", "Potential delays in data collection from agencies could impact the 180-day timeline", "Potential delays if stakeholder meetings are not scheduled promptly", "Potential delay if legal review takes longer than expected.", "Delays due to pending approvals", "Potential delays if security review is not completed in time", "Potential delays due to difficulty in coordinating with non-CFO Act agency stakeholders", "Potential delays if coordination with the Financial Management Marketplace team is not timely", "Delays in scheduling or conducting agency consultations may slow overall progress."]', 'null', '[]', 20, 20, true, '2025-08-29 23:13:53.101937+00', '2025-08-29 23:13:50.688579+00', '2025-08-29 23:13:53.101375+00');


--
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.tasks VALUES ('d6b4ef70-cd60-4612-a027-3a353234d0e1', '8fd95066-1662-4482-b1f8-3801f037f356', 'Issue Guidance on Data Access for Fraud Prevention', 'Issue guidance to agency heads on circumstances for providing Treasury with access to necessary data for fraud and improper payment detection, excluding sensitive data types. Per Sec. 3(e).', '6a445645-3029-4b62-aac7-10cd7e6558d0', 'approved', NULL, '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Compliance', 'N/A');
INSERT INTO public.tasks VALUES ('f9ae9927-17eb-436c-a1f6-9e2c25958926', '8fd95066-1662-4482-b1f8-3801f037f356', 'Update and Issue Payment Verification Guidance in Consultation with OMB Director', 'In consultation with the OMB Director, update and issue guidance to ensure all payments made by the Department of the Treasury on behalf of agencies are subject to pre-certification verification processes. The guidance must: (1) set forth guidelines for compliance with the Do Not Pay Working System as described in 31 U.S.C. 3351 et seq.; (2) include requirements for other payment, account, and payee validation programs and services as determined beneficial for reducing financial fraud and improper payments; (3) specify the data elements and formats agencies must provide for payment submissions; and (4) outline procedures for agencies and Treasury to conduct verification prior to disbursement, as required by law. Reference the legal authorities (31 U.S.C. 3321, 31 U.S.C. 3351 et seq.) and ensure the guidance is actionable for agency implementation.', '6a445645-3029-4b62-aac7-10cd7e6558d0', 'approved', NULL, '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Secretary of the Treasury (in consultation with OMB Director)', 'N/A');
INSERT INTO public.tasks VALUES ('18138d50-e87b-4226-9a8b-2e6145ea1a79', '8fd95066-1662-4482-b1f8-3801f037f356', 'Protect Classified and Sensitive Information During Implementation', 'Take all necessary steps to protect classified information, personally identifiable information, and tax return information during EO implementation. Per Sec. 7(c).', '9e195007-1ca2-453e-b3d7-b6bbf32d0185', 'approved', NULL, '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Security and Technology', 'N/A');
INSERT INTO public.tasks VALUES ('0c8147be-d07e-40b6-9031-c39aaf280ad4', '8fd95066-1662-4482-b1f8-3801f037f356', 'Implement Pre-Certification Payment Verification Processes', 'Ensure all disbursements comply with Treasury''s pre-certification requirements, including validation of funds, payee information, and contract references. Per Sec. 4(a)-(b).', '783a8139-367f-486c-9c19-05b9291cdf9a', 'approved', NULL, '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Division of Business Process Improvement', 'N/A');
INSERT INTO public.tasks VALUES ('5c1900be-8058-4faf-aa10-5f4a8c5bf85b', '8fd95066-1662-4482-b1f8-3801f037f356', 'Submit Payment Files with Sufficient Lead Time for Screening', 'Submit payment files to Treasury with sufficient lead time for fraud and improper payment screening, as determined by Treasury requirements. Per Sec. 4(c).', '783a8139-367f-486c-9c19-05b9291cdf9a', 'approved', NULL, '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Division of Business Process Improvement', 'N/A');
INSERT INTO public.tasks VALUES ('0924dcbc-9246-4e0b-b0cd-30bc48d0ae20', '8fd95066-1662-4482-b1f8-3801f037f356', 'Develop Transparent Exemption Request Process for Payment Verification', 'Develop and include a transparent process for agencies to request exemptions from payment verification requirements for specific payments. Per Sec. 4(e).', '6a445645-3029-4b62-aac7-10cd7e6558d0', 'approved', NULL, '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Compliance', 'N/A');
INSERT INTO public.tasks VALUES ('4ad4258e-029a-4531-90cb-29bb88a94a53', '8fd95066-1662-4482-b1f8-3801f037f356', 'Issue Guidance for Core Financial System Consolidation (CFO Act Agencies)', 'Issue guidance directing CFO Act agencies to consolidate their core financial systems. Per Sec. 5(a).', '5814f396-9360-41ad-adda-cd15afcbc88f', 'approved', '2025-09-21', '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Financial Reporting', 'N/A');
INSERT INTO public.tasks VALUES ('fb03d023-7293-4a37-8d5b-f6cc6939e83a', '8fd95066-1662-4482-b1f8-3801f037f356', 'Issue Guidance for Non-CFO Act Agency Financial Service Consolidation', 'Issue guidance directing non-CFO Act agencies to consolidate transactional financial management services under a single Treasury-approved provider. Per Sec. 5(b).', '5814f396-9360-41ad-adda-cd15afcbc88f', 'approved', '2025-09-21', '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Financial Reporting', 'N/A');
INSERT INTO public.tasks VALUES ('ec87e386-0e30-4c2b-b050-39a2889f76fc', '8fd95066-1662-4482-b1f8-3801f037f356', 'Ensure Use of Standard Financial Management Solutions', 'Ensure all CFO Act agencies use standard financial management solutions available through the Financial Management Marketplace. Per Sec. 5(c).', '5814f396-9360-41ad-adda-cd15afcbc88f', 'approved', NULL, '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Financial Reporting', 'N/A');
INSERT INTO public.tasks VALUES ('e6abe8fa-22c8-4c45-9c93-46810b4f9f45', '8fd95066-1662-4482-b1f8-3801f037f356', 'Ensure Core Financial Systems Comply with Federal Standards', 'Ensure core financial systems comply with Federal accounting and financial reporting standards and relevant Treasury guidance. Per Sec. 5(d).', 'e24c7d45-75b2-4f90-9b14-dcde4fd281d7', 'approved', NULL, '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Accounting', 'N/A');
INSERT INTO public.tasks VALUES ('577e3c17-9ef8-446b-b124-36bb6e7b46ea', '8fd95066-1662-4482-b1f8-3801f037f356', 'Submit Treasury Implementation Report to President', 'Submit an implementation report to the President within 180 days detailing progress on EO implementation. Per Sec. 7(b).', '5814f396-9360-41ad-adda-cd15afcbc88f', 'approved', '2025-09-21', '2025-08-28 19:15:50.277558+00', '2025-08-28 19:17:12.831931+00', 'Director of Financial Reporting', 'N/A');
INSERT INTO public.tasks VALUES ('6419fdfa-59d4-4854-abee-f94622e2916c', '8fd95066-1662-4482-b1f8-3801f037f356', 'Assess and Revoke Delegated Disbursing Authority as Appropriate', 'Assess whether to maintain or revoke delegated disbursing authority to agencies and issue revocation notices as appropriate. Per Sec. 6(a).', '5814f396-9360-41ad-adda-cd15afcbc88f', 'approved', '2025-04-24', '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Financial Reporting', 'N/A');
INSERT INTO public.tasks VALUES ('eb50a7b5-636c-4e49-a1ec-772b76e63110', '8fd95066-1662-4482-b1f8-3801f037f356', 'Develop Plan to Centralize and Manage NTDO Payments', 'Develop a plan to centralize and manage all payments previously disbursed by NTDOs, ensuring seamless continuity of government payments. Per Sec. 6(d).', '783a8139-367f-486c-9c19-05b9291cdf9a', 'approved', NULL, '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Division of Business Process Improvement', 'N/A');
INSERT INTO public.tasks VALUES ('1e02623a-cc8c-4c0d-b4a7-5b8a040640b1', '8fd95066-1662-4482-b1f8-3801f037f356', 'Establish Transition Plan for NTDO Agencies', 'Establish a transition plan for agencies currently operating as NTDOs, including staffing, system integrations, and legal/regulatory modifications for consolidation. Per Sec. 6(e).', '783a8139-367f-486c-9c19-05b9291cdf9a', 'approved', NULL, '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Division of Business Process Improvement', 'N/A');
INSERT INTO public.tasks VALUES ('ed539622-bbd4-4e44-881e-a5c50326f332', '8fd95066-1662-4482-b1f8-3801f037f356', 'Decommission Internal Payment Systems and Transition to Treasury Systems', 'Decommission all internal payment systems and transition to using Treasury’s disbursement systems, except as otherwise authorized. Per Sec. 6(f).', '9e195007-1ca2-453e-b3d7-b6bbf32d0185', 'approved', NULL, '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Security and Technology', 'N/A');
INSERT INTO public.tasks VALUES ('48426c30-e66a-4e5b-9bc9-1c07fb088368', '8fd95066-1662-4482-b1f8-3801f037f356', 'Submit Agency Compliance Plan to OMB Director', 'Submit a compliance plan within 90 days detailing strategy for transitioning disbursing authority, updating systems, verifying payment information, and reporting improper payments. Per Sec. 7(a).', '6a445645-3029-4b62-aac7-10cd7e6558d0', 'approved', '2025-06-23', '2025-08-28 19:15:50.277558+00', '2025-08-28 19:26:36.615798+00', 'Director of Compliance', 'N/A');


--
-- Data for Name: daily_updates; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: eo_pmo_assignments; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.eo_pmo_assignments VALUES ('a37fdd81-813d-4322-8f34-f76aff0f8593', '8fd95066-1662-4482-b1f8-3801f037f356', '1e882225-d379-40a0-a3af-2ba90f6ab76a', '2025-08-29 20:43:25.53752+00', 'e9df20f5-8a10-4261-be4f-584c10c60d74', true);


--
-- Data for Name: task_confirmations; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: task_logs; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: task_updates; Type: TABLE DATA; Schema: public; Owner: dol_user
--



--
-- Data for Name: token_blacklist; Type: TABLE DATA; Schema: public; Owner: dol_user
--

INSERT INTO public.token_blacklist VALUES ('677b9cc6-52af-444c-95ee-f1b8935984bd', 'db4345184a8a409d44911deadb6c17578ae8da3d282ae3b9720fc16f8fe554ef', 'dcd920f0-6e8c-4f01-a67c-bc0ce415a7ac', '2025-08-25 16:41:36+00', '2025-08-25 16:11:43.597326+00');
INSERT INTO public.token_blacklist VALUES ('73381922-6729-405b-876a-0b91594ca3e0', '0a65bdbda82a7c33412370ca6dfcce89430978ed00eed7cf8154f5718a611480', 'a7fa1461-11e3-4f91-ae42-8e4b85ed5a8e', '2025-08-29 00:20:33+00', '2025-08-28 23:58:59.746689+00');
INSERT INTO public.token_blacklist VALUES ('35b264cf-fce7-4ae5-a696-65f8c4c0d178', '15cab62d8c5675a2f825df61d5e60381eaab450b99f009e6d0e484b085897728', '6a445645-3029-4b62-aac7-10cd7e6558d0', '2025-08-29 00:29:49+00', '2025-08-29 00:03:52.750785+00');
INSERT INTO public.token_blacklist VALUES ('a13e827a-d25d-4c21-8d08-3fbf7782bc33', 'c305455579a250007e0f4291a7a554d9b437b06d7e6542b346f3139249faad29', '1e882225-d379-40a0-a3af-2ba90f6ab76a', '2025-08-29 00:34:23+00', '2025-08-29 00:06:17.498977+00');
INSERT INTO public.token_blacklist VALUES ('83248d31-0564-4b93-88d0-364013e067f8', 'eb837bcd460e30f746ea6690b482c5fe87c9b1a3a397af96889fb69239e9dbeb', 'a7fa1461-11e3-4f91-ae42-8e4b85ed5a8e', '2025-08-29 03:05:13+00', '2025-08-29 02:38:48.698574+00');
INSERT INTO public.token_blacklist VALUES ('b5e622c5-bc7c-48ed-9dd4-e724892d10e4', 'fb14f516a296054b764064b361a8da6c9f748f5ac00912e2be781f721ac2eb2a', '6a445645-3029-4b62-aac7-10cd7e6558d0', '2025-08-29 03:10:37+00', '2025-08-29 02:43:06.018675+00');
INSERT INTO public.token_blacklist VALUES ('54ea80b3-71b8-48c6-9ee4-4eba6676ba41', '77448839371b5659c92858afbb33e8646b6d803a403be5c56956a897396ff7a7', '1e882225-d379-40a0-a3af-2ba90f6ab76a', '2025-08-29 03:13:37+00', '2025-08-29 02:56:12.839294+00');
INSERT INTO public.token_blacklist VALUES ('12fb8c7e-20a8-43eb-8f4a-7c396c2d40bd', '13e4cea83a81d44fd48e0f437755c77e6437a766ebe244f429c86d89561ae0f4', 'a7fa1461-11e3-4f91-ae42-8e4b85ed5a8e', '2025-08-29 03:26:25+00', '2025-08-29 03:11:43.371091+00');


--
-- PostgreSQL database dump complete
--

\unrestrict IDjWHO99LPzcPgErO8X3KkCx9tc28OsMjlyDfPRTDe6Vbeqd1agT1LseM9MoOkb

