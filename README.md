# DOL-EO-Management: Email-Driven Task Automation

## 🚀 Project Overview

This project is building a modular, scalable, **email-driven automation system** for the U.S. Department of Labor’s Executive Orders (EOs) management workflow.
**Goal:** Seamlessly ingest, process, assign, and track tasks via email—starting with GoDaddy (IMAP/SMTP), but architected to support any provider.

---

## ✅ Phase 1: Environment & Abstract Email Client Setup (Completed)

**Goal:** Lay the foundation for a provider-agnostic email integration system.

**Accomplishments:**

* **Dockerized Dev Environment:** FastAPI, Celery, Redis, PostgreSQL with Docker Compose.
* **Modular Email Client:**

  * `EmailClient` abstract class for plug-and-play provider support.
  * `GoDaddyEmailClient`—full IMAP/SMTP implementation for GoDaddy.
* **.env Configuration:** Secure handling of credentials and ports.
* **Helper Functions:**

  * IMAP/SMTP login
  * Inbox listing & unread email fetching
  * PDF attachment extraction & saving
  * Templated email responses

---

## 🛣️ Upcoming Phases

### **Phase 2: Implement GoDaddy Email Ingestion & Sending**

**Goal:** Enable robust send/receive workflows with real Executive Orders.

* Fetch unread emails (filtering PDFs)
* Save PDF attachments for further processing
* Parse and log key email metadata
* Implement & test robust send\_email functionality
* Add unit/test scripts for roundtrip email flows
* *(Optional)*: Add minimal caching to prevent double-processing

---

### **Phase 3: Integrate With Celery Workflow**

**Goal:** Make email handling asynchronous and production-ready.

* Move polling logic to Celery background tasks
* Schedule periodic email checks (e.g., every 10 min)
* After attachment download, queue for LLM extraction
* Log all email actions in PostgreSQL for audit/compliance

---

### **Phase 4: Response Handling & Abstraction Completion**

**Goal:** Finalize intelligent, fully modular email workflows.

* Parse incoming replies: detect “Accepted,” “Declined,” status updates
* Ensure GoDaddy client conforms to the abstract EmailClient API
* Add fallback logic for email provider quirks (sync, sent, etc.)
* Document how to plug in Gmail, Outlook, or any IMAP provider
* Collaborate with AI/NLP team for seamless integration

---

## 💡 Extensibility

* Swap in **any** email provider by extending `EmailClient`
* Future-proof for Gmail, Outlook, or custom IMAP/SMTP

---

## 🏗️ Getting Started

1. Clone repo and copy `.env.template` → `.env`
2. Set your credentials and ports
3. Build & run:

   ```bash
   docker-compose up --build
   ```
4. Test email client with `test_email.py`

---
