# Email Service Documentation

## Overview

The Email Service is a robust IMAP IDLE listener that monitors the lumenlighthouse.ai inbox in real-time. It fetches new emails, extracts metadata, body content, and attachments, then posts normalized payloads to the FastAPI webhook endpoint for processing.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   IMAP Server   │    │  IMAP IDLE       │    │  FastAPI        │
│  lumenlighthouse│◄──►│  Listener        │───►│  Webhook        │
│  .ai:993        │    │  Service         │    │  Endpoint       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Background      │
                       │  Processing      │
                       │  Tasks           │
                       └──────────────────┘
```

## Components

### 1. IMAP IDLE Listener (`src/email/imap_idle_listener.py`)

**Features:**
- Real-time email monitoring using IMAP IDLE protocol
- Automatic reconnection with exponential backoff
- Fallback to polling when IDLE fails
- Comprehensive email parsing (metadata, body, attachments)
- Base64 encoding for API transmission
- Statistics and monitoring

**Key Classes:**
- `IMAPIDLEListener`: Main listener class
- `EmailMetadata`: Email metadata structure
- `EmailAttachment`: Attachment information
- `EmailPayload`: Complete email payload

### 2. Email Webhook (`src/routes/email_webhook.py`)

**Features:**
- Receives normalized email payloads
- Asynchronous background processing
- Content-based email routing
- Attachment processing and storage
- Health monitoring endpoints

**Endpoints:**
- `POST /api/email/webhook`: Receive email payloads
- `GET /api/email/webhook/health`: Health check
- `GET /api/email/webhook/stats`: Service statistics (admin only)

### 3. Service Manager (`src/email/service_manager.py`)

**Features:**
- Service lifecycle management
- Graceful shutdown handling
- Signal handling (SIGINT, SIGTERM)
- Service status monitoring

## Setup and Configuration

### 1. Environment Variables

Create a `.env` file with the following variables:

```bash
# IMAP Configuration
IMAP_HOST=lumenlighthouse.ai
IMAP_PORT=993
IMAP_USERNAME=your_email@lumenlighthouse.ai
IMAP_PASSWORD=your_app_password
IMAP_MAILBOX=INBOX

# Service Configuration
IMAP_CHECK_INTERVAL=30
IMAP_MAX_RETRIES=5
IMAP_RETRY_DELAY=60

# API Configuration
EMAIL_WEBHOOK_ENDPOINT=http://localhost:8000/api/email/webhook

# Database (if needed)
DATABASE_URL=postgresql://dol_user:artygenz@localhost:5433/dol_db
```

### 2. Dependencies

The service requires these additional packages (already added to `requirements.txt`):

```bash
aioimaplib>=1.0.1
aiohttp>=3.8.0
```

### 3. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p attachments logs
```

## Usage

### 1. Standalone Service

Run the email service as a standalone process:

```bash
# Method 1: Direct execution
python -m src.email.service_manager

# Method 2: Using the main function
python src/email/imap_idle_listener.py
```

### 2. Docker Deployment

Use the main Docker Compose configuration:

```bash
# Start the IMAP service with the main stack
docker-compose up -d imap-listener

# View logs
docker-compose logs -f imap-listener

# Stop the service
docker-compose stop imap-listener

# Or use the simple startup script
./start-imap.sh start
```

### 3. Integration with Main Application

The email service integrates with the main FastAPI application:

```bash
# Start the main application
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# The webhook endpoint will be available at:
# http://localhost:8000/api/email/webhook
```

## API Reference

### Email Webhook Endpoint

**POST** `/api/email/webhook`

Receives normalized email payloads from the IMAP IDLE listener.

**Request Body:**
```json
{
  "metadata": {
    "message_id": "<message-id@domain.com>",
    "subject": "Email Subject",
    "from_email": "sender@example.com",
    "to_emails": ["recipient@example.com"],
    "cc_emails": [],
    "bcc_emails": [],
    "date": "2024-01-01T12:00:00Z",
    "received_date": "2024-01-01T12:00:00Z",
    "size": 1024,
    "flags": ["\\Seen"],
    "headers": {
      "From": "sender@example.com",
      "To": "recipient@example.com",
      "Subject": "Email Subject"
    }
  },
  "body_text": "Plain text email body",
  "body_html": "<html><body>HTML email body</body></html>",
  "attachments": [
    {
      "filename": "document.pdf",
      "content_type": "application/pdf",
      "size": 1024,
      "data": "base64_encoded_data",
      "content_id": null
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Email received and queued for processing",
  "email_id": "email_1704110400_1234",
  "processing_status": "queued"
}
```

### Health Check Endpoint

**GET** `/api/email/webhook/health`

Returns service health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "email_webhook",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Statistics Endpoint

**GET** `/api/email/webhook/stats`

Returns service statistics (admin access required).

**Response:**
```json
{
  "total_emails_processed": 150,
  "success_rate": 0.98,
  "average_processing_time": 2.5,
  "last_email_processed": "2024-01-01T12:00:00Z",
  "service_status": "active"
}
```

## Email Processing Workflow

### 1. Email Reception
- IMAP IDLE listener detects new email
- Fetches complete email data (metadata, body, attachments)
- Normalizes data into structured payload

### 2. Webhook Submission
- Posts payload to FastAPI webhook endpoint
- Receives immediate acknowledgment
- Email queued for background processing

### 3. Background Processing
- Saves email metadata to database
- Processes and stores attachments
- Routes email based on content analysis
- Triggers appropriate business logic

### 4. Content Routing
The service routes emails based on content:

- **PMO Emails**: Contains "pmo", "project management", "executive order"
- **Notifications**: Contains "notification", "update", "status"
- **General**: All other emails

## Testing

### 1. Run Test Suite

```bash
# Test the email service functionality
python test_email_service.py
```

### 2. Manual Testing

```bash
# Test webhook health
curl http://localhost:8000/api/email/webhook/health

# Test webhook endpoint with sample data
curl -X POST http://localhost:8000/api/email/webhook \
  -H "Content-Type: application/json" \
  -d @test_email_payload.json
```

### 3. Monitor Logs

```bash
# View service logs
tail -f logs/email_service.log

# View Docker logs
docker-compose -f docker-compose.email.yml logs -f email-service
```

## Monitoring and Troubleshooting

### 1. Service Status

Check service status through the API:

```bash
curl http://localhost:8000/api/email/webhook/health
```

### 2. Common Issues

**Connection Issues:**
- Verify IMAP credentials
- Check network connectivity
- Ensure IMAP server supports IDLE

**Authentication Errors:**
- Use app-specific passwords for Gmail
- Verify username/password format
- Check account security settings

**Webhook Failures:**
- Verify API endpoint is accessible
- Check payload format
- Monitor server logs for errors

### 3. Log Analysis

The service provides detailed logging:

```python
# Log levels
INFO: Normal operation
WARNING: Non-critical issues
ERROR: Critical errors
DEBUG: Detailed debugging information
```

### 4. Performance Monitoring

Monitor these metrics:

- **Connection Status**: IMAP connection health
- **Processing Rate**: Emails processed per minute
- **Error Rate**: Failed processing attempts
- **Response Time**: Webhook response times

## Security Considerations

### 1. Authentication
- Use app-specific passwords for IMAP
- Implement API authentication for webhooks
- Secure environment variable storage

### 2. Data Protection
- Encrypt sensitive email content
- Implement attachment scanning
- Secure file storage

### 3. Access Control
- Restrict webhook endpoint access
- Implement rate limiting
- Monitor for suspicious activity

## Deployment

### 1. Production Setup

```bash
# Set production environment variables
export IMAP_USERNAME=production@lumenlighthouse.ai
export IMAP_PASSWORD=secure_app_password
export EMAIL_WEBHOOK_ENDPOINT=https://api.lumenlighthouse.ai/api/email/webhook

# Start with Docker
docker-compose -f docker-compose.email.yml up -d
```

### 2. Scaling

- Run multiple listener instances
- Implement load balancing
- Use message queues for processing

### 3. Backup and Recovery

- Backup email processing logs
- Implement retry mechanisms
- Monitor service health

## Future Enhancements

### 1. Planned Features
- Email filtering and rules
- Advanced content analysis
- Integration with AI processing
- Real-time notifications

### 2. Performance Improvements
- Connection pooling
- Caching mechanisms
- Optimized attachment handling

### 3. Monitoring Enhancements
- Prometheus metrics
- Grafana dashboards
- Alert systems

## Support

For issues and questions:

1. Check the logs for error messages
2. Verify configuration settings
3. Test connectivity manually
4. Review this documentation
5. Contact the development team

---

**Last Updated:** January 2024
**Version:** 1.0.0
