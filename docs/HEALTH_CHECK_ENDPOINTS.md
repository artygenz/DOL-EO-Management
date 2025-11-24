# Health Check Endpoints

This document describes the dedicated health check endpoints for database and Redis connections.

## Overview

The health check endpoints provide detailed diagnostics for specific services:
- **Database Health**: Tests database connectivity, table access, and connection pool status
- **Redis Health**: Tests Redis connectivity, various operations, and Redis server information

These endpoints are more reliable than the general health check endpoint which may return false positives.

## Authentication

All health check endpoints require admin-level authentication. Only users with the `admin` role can access these endpoints.

## Endpoints

### 1. Database Health Check

**Endpoint:** `GET /api/monitoring/health/database`

**Description:** Comprehensive database health check with detailed diagnostics.

**Authentication:** Admin required

**Response:**
```json
{
  "connected": true,
  "response_time_ms": 45.2,
  "test_query_result": 1,
  "database_version": "PostgreSQL 15.4 on x86_64-pc-linux-gnu",
  "table_counts": {
    "users": 25,
    "executive_orders": 150,
    "tasks": 300,
    "email_logs": 1200,
    "celery_task_logs": 500
  },
  "connection_pool": {
    "pool_size": 5,
    "checked_in": 3,
    "checked_out": 2,
    "overflow": 0
  },
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**What it tests:**
- Basic database connectivity
- Table access and record counts
- Database version information
- Connection pool status
- Response time measurement

### 2. Redis Health Check

**Endpoint:** `GET /api/monitoring/health/redis`

**Description:** Comprehensive Redis health check with detailed diagnostics.

**Authentication:** Admin required

**Response:**
```json
{
  "connected": true,
  "host": "redis",
  "port": 6379,
  "url": "redis://redis:6379/0",
  "response_time_ms": 12.5,
  "operations_tested": ["string_ops", "list_ops", "hash_ops"],
  "redis_info": {
    "version": "7.0.5",
    "uptime_seconds": 86400,
    "connected_clients": 3,
    "used_memory_human": "2.5M",
    "keyspace_hits": 1500,
    "keyspace_misses": 50
  },
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**What it tests:**
- Redis connectivity (ping)
- Basic operations (set, get, delete)
- String operations
- List operations
- Hash operations
- Redis server information
- Response time measurement

### 3. General Health Check (Comparison)

**Endpoint:** `GET /api/monitoring/health/connections`

**Description:** Tests all services but may return false positives.

**Note:** This endpoint may show all services as healthy even when they're not working properly.

## Error Responses

### 403 Forbidden
```json
{
  "detail": "Admin access required"
}
```

### 500 Internal Server Error
```json
{
  "connected": false,
  "error": "Connection refused",
  "status": "unhealthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Usage Examples

### Check Database Health
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     "$API_URL/health/database"
```

### Check Redis Health
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     "$API_URL/health/redis"
```

### Compare with General Health Check
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     "$API_URL/health/connections"
```

## Key Differences

| Endpoint | Purpose | Reliability | Details |
|----------|---------|--------------|---------|
| `/health/database` | Database-specific health | High | Tests actual DB operations, table access, connection pool |
| `/health/redis` | Redis-specific health | High | Tests various Redis operations, server info |
| `/health/connections` | All services | Medium | May return false positives, less detailed |

## Monitoring and Alerting

Use these endpoints for:
- **Database monitoring**: Check if database is accessible and tables are working
- **Redis monitoring**: Verify Redis operations and server health
- **Troubleshooting**: Get detailed error information when services fail
- **Performance monitoring**: Track response times and connection pool status

## Implementation Details

### Database Health Check
- Tests basic connectivity with `SELECT 1`
- Checks table access for key tables
- Retrieves database version information
- Monitors connection pool status
- Measures response time

### Redis Health Check
- Tests connection with `ping()`
- Performs basic operations (set, get, delete)
- Tests different data types (strings, lists, hashes)
- Retrieves Redis server information
- Measures response time

## Testing

Use the provided test scripts:
- `scripts/test_health_endpoints.py` - Python test script
- `scripts/test_health_curl.sh` - Bash test script with curl

Make sure to replace `YOUR_ADMIN_TOKEN` with a valid admin JWT token before testing.

## Security Considerations

- All endpoints require admin authentication
- No sensitive data is exposed in responses
- Test operations use temporary keys that are cleaned up
- Connection information is sanitized in responses
