# IMAP Service Setup Guide

## Overview

The IMAP IDLE listener service has been integrated into the main `docker-compose.yml` file. This provides a clean, unified deployment approach.

## Quick Setup

### 1. Environment Configuration

Add these variables to your `.env` file:

```bash
# IMAP Configuration
IMAP_USERNAME=your_email@lumenlighthouse.ai
IMAP_PASSWORD=your_app_password
IMAP_HOST=lumenlighthouse.ai
IMAP_PORT=993
IMAP_MAILBOX=INBOX

# Service Configuration
IMAP_CHECK_INTERVAL=30
IMAP_MAX_RETRIES=5
IMAP_RETRY_DELAY=60
```

### 2. Start the Service

#### Option A: Using Docker Compose
```bash
# Start the IMAP service
docker-compose up -d imap-listener

# View logs
docker-compose logs -f imap-listener

# Stop the service
docker-compose stop imap-listener
```

#### Option B: Using the Startup Script
```bash
# Make script executable
chmod +x start-imap.sh

# Start the service
./start-imap.sh start

# View logs
./start-imap.sh logs

# Check status
./start-imap.sh status
```

### 3. Service Management

```bash
# Check if service is running
./start-imap.sh status

# Restart the service
./start-imap.sh restart

# Test webhook endpoint
./start-imap.sh test

# Stop the service
./start-imap.sh stop
```

## What's Included

The IMAP service in `docker-compose.yml` includes:

- ✅ **IMAP IDLE listener** with real-time monitoring
- ✅ **Health checks** and monitoring
- ✅ **Persistent storage** for attachments and logs
- ✅ **Integration** with main API server
- ✅ **Automatic restart** on failure
- ✅ **Logging** and monitoring

## Service Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   IMAP Server   │    │  IMAP Listener   │    │  FastAPI Server │
│  lumenlighthouse│◄──►│  Container       │───►│  Container      │
│  .ai:993        │    │  dol-imap-listener│    │  dol-api-server │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  Redis Cache     │    │  PostgreSQL DB  │
                       │  dol-redis       │    │  dol-database   │
                       └──────────────────┘    └─────────────────┘
```

## Testing

### Test the Webhook Endpoint
```bash
# Test health endpoint
curl http://localhost:8000/api/email/webhook/health

# Test with sample data
python simple_webhook_test.py
```

### Monitor the Service
```bash
# View real-time logs
docker-compose logs -f imap-listener

# Check service status
docker-compose ps imap-listener
```

## Troubleshooting

### Common Issues

1. **Service won't start**: Check IMAP credentials in `.env`
2. **Connection errors**: Verify network connectivity to lumenlighthouse.ai
3. **Webhook failures**: Ensure API server is running on port 8000

### Debug Mode
Enable debug logging by adding to `.env`:
```bash
LOG_LEVEL=DEBUG
```

## Next Steps

1. ✅ **Set up IMAP credentials** in `.env`
2. ✅ **Start the service** with `./start-imap.sh start`
3. ✅ **Monitor logs** to verify it's working
4. ✅ **Test webhook** with sample data
5. ✅ **Deploy to production** when ready

The IMAP service is now fully integrated with your main application stack!
