# Daily Task Update System

## Overview

The Daily Task Update System allows employees (executors) to email their daily task updates, which are automatically processed, extracted, and aggregated into daily summaries for PMOs.

## Features

### Email Processing
- **C1**: One consolidated email covering all tasks
- **C2**: One daily email with detailed per-task breakdown  
- **C3**: Separate emails, one per task
- Automatic intent detection and routing
- AI-powered extraction of structured updates

### Workflow
1. **IMAP Listener** forwards emails to FastAPI webhook
2. **FastAPI** routes to "daily task update" handler
3. **Celery Worker** resolves user_id from sender email
4. **AI Extraction** processes email content and extracts structured updates
5. **Database Storage** persists updates with deduplication
6. **Daily Aggregation** generates summaries at 6:00 PM ET
7. **PMO Notification** sends summary emails to assigned PMOs

## Database Schema

### Task Updates Table
```sql
CREATE TABLE task_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eo_id UUID REFERENCES executive_orders(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    progress_pct INTEGER,
    status VARCHAR(20), -- NotStarted, InProgress, Blocked, Completed
    notes TEXT,
    blockers JSONB,
    risks JSONB,
    eta DATE,
    spent_hours NUMERIC(5,2),
    source_email_message_id VARCHAR(255),
    dedupe_hash VARCHAR(64),
    is_late BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Daily EO Summaries Table
```sql
CREATE TABLE daily_eo_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eo_id UUID REFERENCES executive_orders(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    progress_summary TEXT,
    key_blockers JSONB,
    risks JSONB,
    attention_items JSONB,
    missing_updates JSONB, -- List of user emails who didn't report
    total_tasks INTEGER DEFAULT 0,
    updated_tasks INTEGER DEFAULT 0,
    summary_email_sent BOOLEAN DEFAULT FALSE,
    summary_email_sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## API Endpoints

### Email Webhook
- **POST** `/api/email/webhook` - Receives emails from IMAP listener
- Automatically detects daily update emails and routes to processing

### Manual Processing (for testing)
- **POST** `/api/daily-updates/process` - Manually process a daily update email
- **POST** `/api/daily-updates/aggregate/{eo_id}` - Manually trigger aggregation
- **GET** `/api/daily-updates/summary/{eo_id}/{date}` - Get daily summary

## Celery Tasks

### Task Update Processing
```python
@celery_app.task(name="src.workflow.tasks.process_daily_update_email")
def process_daily_update_email(email_payload: Dict):
    """
    1. Resolve user_id from sender email
    2. Fetch user's active tasks
    3. Extract task updates using AI
    4. Save updates to database
    """
```

### Daily Aggregation
```python
@celery_app.task(name="src.workflow.tasks.aggregate_daily_updates")
def aggregate_daily_updates(eo_id: str, target_date: str = None):
    """
    1. Get all task updates for the EO and date
    2. Generate summary using AI
    3. Save summary to database
    4. Send email to PMOs
    """
```

### Reminder Emails
```python
@celery_app.task(name="src.workflow.tasks.send_daily_reminders")
def send_daily_reminders(target_date: str = None):
    """
    Send reminder emails to employees who haven't provided daily updates.
    Runs at 4pm ET daily.
    """
```

## Scheduling

### Celery Beat Schedule
- **4:00 PM ET**: Send reminder emails to employees with missing updates
- **6:00 PM ET**: Aggregate daily updates and send PMO summaries

### Timezone Configuration
- All timestamps stored in UTC
- Scheduling based on America/New_York timezone
- Deadline enforcement at 6:00 PM ET

## Email Templates

### Employee Template
```
# Daily Update (YYYY-MM-DD)
- Task: <task short title or ID>
  Status: InProgress
  Progress: 60%
  ETA: 2025-01-20
  Spent: 3.5h
  Blockers: <none|...>
  Notes: <short note>
```

### Reminder Email
```
Hello {user_name},

This is a friendly reminder that you have {task_count} active task(s) assigned to you under Executive Order: {eo.title}

Please provide your daily update by 6:00 PM ET today.

Your tasks:
- {task.title}
- {task.title}

You can reply to this email with your update, or use the following template:

# Daily Update ({target_date})
- Task: [Task Title or ID]
  Status: [NotStarted/InProgress/Blocked/Completed]
  Progress: [0-100]%
  ETA: [YYYY-MM-DD]
  Spent: [X.X]h
  Blockers: [none or description]
  Notes: [brief update]

Thank you!
```

### PMO Summary Email
```
Daily Summary Report - {eo.title}
Date: {summary.date}

{summary.progress_summary}

Key Metrics:
- Total Tasks: {summary.total_tasks}
- Updated Tasks: {summary.updated_tasks}
- Missing Updates: {len(summary.missing_updates)}

Key Blockers:
- {blocker}

Risks:
- {risk}

Attention Items:
- {item}

Missing Updates From:
- {email}
```

## AI Extraction Schema

### Input
- Email body text
- User's active tasks list (id + title)

### Output
```json
{
  "case": "C1|C2|C3",
  "updates": [
    {
      "task_id": "uuid-of-task",
      "status": "InProgress",
      "progress_pct": 60,
      "notes": "Working on implementation",
      "blockers": ["Waiting for approval"],
      "risks": ["Timeline might slip"],
      "eta": "2025-01-15",
      "spent_hours": 3.5
    }
  ],
  "unmatched_mentions": ["any text that didn't map to known tasks"]
}
```

## Configuration

### Environment Variables
```bash
# Email processing
EMAIL_WEBHOOK_ENDPOINT=http://api:8000/api/email/webhook
PMO_EMAIL_ADDRESS=pmo@example.com

# Celery configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Database
DATABASE_URL=postgresql://user:pass@db:5432/dbname

# Timezone
TZ=America/New_York
```

### Celery Queues
- **ingest**: Email ingestion and storage
- **ai**: AI extraction and processing
- **db**: Database operations
- **email**: Email sending
- **review**: PMO review processing

## Testing

### Run Test Suite
```bash
python test_daily_updates.py
```

### Manual Testing
1. Send test email to IMAP listener
2. Check webhook receives and processes email
3. Verify task updates are saved to database
4. Trigger manual aggregation
5. Check PMO summary email is sent

## Monitoring

### Key Metrics
- Number of daily updates received
- Number of updates processed successfully
- Number of summaries generated
- Number of reminder emails sent
- Processing time for updates
- Error rates

### Logs
- Email webhook processing logs
- Celery task execution logs
- AI extraction logs
- Database operation logs

## Troubleshooting

### Common Issues

1. **User not found**
   - Ensure user exists in database with correct email
   - Check user role is "executor"

2. **No active tasks**
   - Verify user has assigned tasks
   - Check task status is active (pending, in_progress, Pending PMO approval)

3. **AI extraction fails**
   - Check email format matches expected template
   - Verify task titles are mentioned in email
   - Review unmatched_mentions for debugging

4. **Duplicate updates**
   - Check dedupe_hash is working correctly
   - Verify email content is unique

5. **Late updates**
   - Check timezone configuration
   - Verify deadline enforcement logic

### Debug Commands
```bash
# Check Celery worker status
docker-compose exec worker celery -A src.workflow.celery_app inspect active

# Check Celery Beat schedule
docker-compose exec worker celery -A src.workflow.celery_app inspect scheduled

# View task results
docker-compose exec worker celery -A src.workflow.celery_app inspect reserved

# Check database tables
docker-compose exec db psql -U dol_user -d dol_db -c "SELECT COUNT(*) FROM task_updates;"
docker-compose exec db psql -U dol_user -d dol_db -c "SELECT COUNT(*) FROM daily_eo_summaries;"
```

## Future Enhancements

1. **Advanced AI Integration**
   - Replace regex fallback with full LLM processing
   - Add sentiment analysis for risk assessment
   - Implement natural language task mapping

2. **Enhanced Templates**
   - Rich text email templates
   - Interactive forms for updates
   - Mobile-friendly templates

3. **Advanced Scheduling**
   - Custom reminder schedules per user
   - Escalation workflows for missing updates
   - Integration with calendar systems

4. **Analytics Dashboard**
   - Real-time update tracking
   - Progress visualization
   - Trend analysis and reporting

5. **Integration Features**
   - Slack/Teams notifications
   - Jira/Asana integration
   - Calendar event creation
