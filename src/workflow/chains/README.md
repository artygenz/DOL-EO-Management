# Workflow Chains - Orchestrated Task Processing

## 📋 Overview

This directory contains orchestrated task chains that replace the fire-and-forget pattern in the original `tasks.py`. These chains use the refactored services from `workflow/services/` to provide proper task sequencing, error handling, and state management.

## 🏗️ Architecture

### **Before: Fire-and-Forget Anti-Pattern**
```python
# ❌ Problematic pattern in tasks.py
def store_email(eo_payload):
    # ... do work ...
    ai_extract_tasks.delay(eo_id, eo_text)  # Fire-and-forget
    return {"eo_id": str(eo_row.id)}        # Returns before next task starts
```

### **After: Orchestrated Chains**
```python
# ✅ Proper orchestration in chains/
def process_eo_chain(eo_payload):
    try:
        # Step 1: Process email
        email_result = email_processing_service.process_eo_email(eo_payload)
        
        # Step 2: Extract tasks
        ai_result = ai_extraction_service.extract_tasks_from_eo(eo_id, text)
        
        # Step 3: Persist tasks
        persistence_result = task_persistence_service.persist_tasks_for_eo(eo_id, tasks)
        
        # Step 4: Send PMO email
        pmo_result = pmo_review_service.send_pmo_review_email(eo_id, tasks)
        
        return {"success": True, "pipeline_status": "completed"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## 📦 Chain Modules

### **1. EO Processing Chain** (`eo_processing_chain.py`)

**Purpose**: Orchestrates complete Executive Order processing pipeline

**Pipeline**:
1. Process EO email (store, extract text, update status)
2. Extract tasks using AI
3. Persist tasks to database
4. Send PMO review email
5. Notify assignees (if auto-approved)

**Key Functions**:
- `process_eo_chain()` - Main EO processing pipeline
- `process_eo_with_auto_approval()` - EO processing with automatic approval
- `retry_failed_eo()` - Retry failed EO processing

### **2. PMO Response Chain** (`pmo_response_chain.py`)

**Purpose**: Orchestrates PMO response processing pipeline

**Pipeline**:
1. Parse PMO response email
2. Update task statuses (approve/reject)
3. Handle rejected tasks (rewire if needed)
4. Notify assignees of approved tasks
5. Send improved tasks back to PMO (if any)

**Key Functions**:
- `process_pmo_response_chain()` - Main PMO response processing
- `handle_bulk_approval()` - Handle bulk approval/rejection
- `retry_pmo_response()` - Retry PMO response processing

### **3. Daily Update Chain** (`daily_update_chain.py`)

**Purpose**: Orchestrates daily update processing pipeline

**Pipeline**:
1. Process daily update email
2. Extract task updates using AI
3. Save task updates to database
4. Trigger aggregation (if needed)
5. Send summary emails

**Key Functions**:
- `process_daily_update_chain()` - Main daily update processing
- `aggregate_daily_updates_chain()` - Aggregate and summarize updates
- `send_daily_reminders_chain()` - Send reminder emails
- `retry_daily_update()` - Retry daily update processing

## ✅ Benefits of Orchestrated Chains

### **1. Proper Task Sequencing**
- Tasks run in order, waiting for completion
- No race conditions or timing issues
- Clear pipeline progression

### **2. Error Propagation**
- Failures bubble up to the orchestrator
- Can implement rollback logic
- Centralized error handling

### **3. Transactional Guarantees**
- Can implement transaction boundaries
- Rollback capabilities
- Data consistency

### **4. Better Observability**
- Single entry point for monitoring
- End-to-end pipeline tracking
- Centralized logging

### **5. State Management**
- Explicit pipeline state tracking
- Retry capabilities
- Failure recovery

## 🔄 Usage Examples

### **EO Processing**
```python
from src.workflow.chains.eo_processing_chain import process_eo_chain

# Process EO with full orchestration
result = process_eo_chain.delay(eo_payload)
```

### **PMO Response**
```python
from src.workflow.chains.pmo_response_chain import process_pmo_response_chain

# Process PMO response with full orchestration
result = process_pmo_response_chain.delay(pmo_email_payload)
```

### **Daily Updates**
```python
from src.workflow.chains.daily_update_chain import process_daily_update_chain

# Process daily update with full orchestration
result = process_daily_update_chain.delay(daily_update_payload)
```

## 🎯 Integration with Services

The chains use the refactored services from `workflow/services/`:

- **EmailProcessingService** - EO email processing
- **AITaskExtractionService** - AI task extraction
- **TaskPersistenceService** - Task database operations
- **PMOReviewService** - PMO email handling
- **PMOResponseService** - PMO response processing
- **NotificationService** - Assignee notifications
- **DailyUpdateService** - Daily update processing

## 📊 Monitoring and Debugging

### **Pipeline Status Tracking**
Each chain returns a status indicating the pipeline state:
- `"completed"` - Pipeline completed successfully
- `"failed"` - Pipeline failed
- `"retry_completed"` - Retry attempt completed
- `"bulk_approval_completed"` - Bulk approval completed

### **Error Handling**
- Centralized error logging
- Failure step identification
- Retry capabilities
- Rollback support

### **Result Structure**
```python
{
    "success": True/False,
    "eo_id": "uuid",
    "pipeline_status": "completed|failed|retry_completed",
    "error": "error_message",  # if failed
    "failed_step": "step_name",  # if failed
    # ... other result data
}
```

## 🚀 Deployment

The chains are automatically registered with Celery and can be called from:
- Email webhook routes
- API endpoints
- Scheduled tasks
- Manual triggers

## 🔧 Configuration

No additional configuration is required. The chains use the same Celery configuration as the original tasks.

## 📈 Performance

- **Same execution time** as individual tasks
- **Better error handling** and recovery
- **Improved observability** and debugging
- **Transactional safety** and consistency

The orchestrated chains provide the same functionality as the original tasks but with proper sequencing, error handling, and state management.
