# DOL EO Management - Microservices Migration Guide

## 📋 Table of Contents
1. [Current Architecture Analysis](#current-architecture-analysis)
2. [Target Microservices Architecture](#target-microservices-architecture)
3. [Migration Strategy](#migration-strategy)
4. [Implementation Plan](#implementation-plan)
5. [Service-Specific Details](#service-specific-details)
6. [Infrastructure Changes](#infrastructure-changes)
7. [Testing Strategy](#testing-strategy)
8. [Deployment Strategy](#deployment-strategy)
9. [Monitoring & Observability](#monitoring--observability)
10. [Rollback Plan](#rollback-plan)

---

## 🔍 Current Architecture Analysis

### Current State (Monolithic)
```
dol-eo-management/
├── src/
│   ├── main.py              # FastAPI application
│   ├── routes/              # API endpoints
│   ├── models/              # Database models
│   ├── workflow/            # Celery tasks & workers
│   ├── email/               # Email service
│   ├── core/                # Shared utilities
│   └── db/                  # Database operations
├── Dockerfile               # Single Dockerfile for all services
├── requirements.txt         # All dependencies in one file
└── docker-compose.yml       # All services share same image
```

### Current Anti-Patterns
1. **Single Dockerfile**: All services use the same image
2. **Volume Over-Sharing**: Every service mounts entire codebase
3. **Dependency Bloat**: All services get all dependencies
4. **Security Issues**: Internal services exposed to host
5. **No Resource Limits**: Unlimited resource consumption
6. **Missing Health Checks**: Only email service has health monitoring
7. **Development Settings in Production**: `--reload` flag, source mounting

---

## 🏗️ Target Microservices Architecture

### Service Decomposition
```
dol-eo-management/
├── services/
│   ├── api-gateway/           # FastAPI REST API
│   ├── worker-service/        # Celery background workers
│   ├── scheduler-service/     # Celery Beat scheduler
│   ├── email-service/         # IMAP listener & email processing
│   └── notification-service/  # Email sending & notifications
├── shared/
│   ├── models/               # Shared database models
│   ├── database/             # Database utilities
│   ├── utils/                # Common utilities
│   └── schemas/              # Shared Pydantic schemas
├── infrastructure/
│   ├── docker/               # Service-specific Dockerfiles
│   ├── k8s/                  # Kubernetes manifests
│   └── terraform/            # Infrastructure as Code
└── docs/
    ├── api/                  # API documentation
    └── architecture/         # Architecture diagrams
```

### Service Responsibilities

#### 1. API Gateway Service
- **Purpose**: REST API endpoints, request routing, authentication
- **Technologies**: FastAPI, SQLAlchemy, Pydantic
- **Dependencies**: Database, Redis (for sessions)
- **Ports**: 8000 (HTTP)

#### 2. Worker Service
- **Purpose**: Background task processing, AI integration
- **Technologies**: Celery, OpenAI API, SQLAlchemy
- **Dependencies**: Database, Redis, OpenAI API
- **Queues**: ai, db, email, review

#### 3. Scheduler Service
- **Purpose**: Periodic task scheduling (daily reminders, summaries)
- **Technologies**: Celery Beat, SQLAlchemy
- **Dependencies**: Database, Redis
- **Schedules**: Daily reminders, daily summaries

#### 4. Email Service
- **Purpose**: Email ingestion, IMAP monitoring, webhook processing
- **Technologies**: IMAP, FastAPI webhooks, SQLAlchemy
- **Dependencies**: Database, API Gateway
- **Volumes**: Attachments storage

#### 5. Notification Service
- **Purpose**: Email sending, template rendering
- **Technologies**: SMTP, Jinja2 templates
- **Dependencies**: Database, Email templates
- **Volumes**: Email templates, outbox

---

## 🚀 Migration Strategy

### Phase 1: Preparation & Analysis (Week 1-2)
1. **Code Analysis**
   - Identify shared code and dependencies
   - Map service boundaries
   - Document API contracts

2. **Database Analysis**
   - Review current schema
   - Plan shared database access
   - Design service-specific views/queries

3. **Dependency Analysis**
   - Audit current requirements.txt
   - Separate dependencies by service
   - Identify shared libraries

### Phase 2: Shared Infrastructure (Week 3-4)
1. **Create Shared Libraries**
   - Extract common models
   - Create shared utilities
   - Build shared schemas

2. **Database Refactoring**
   - Create service-specific database modules
   - Implement connection pooling
   - Add database migrations

3. **Configuration Management**
   - Implement environment-based config
   - Add secrets management
   - Create service-specific env files

### Phase 3: Service Extraction (Week 5-8)
1. **API Gateway Service**
   - Extract FastAPI application
   - Create service-specific Dockerfile
   - Implement health checks

2. **Worker Service**
   - Extract Celery workers
   - Create service-specific requirements
   - Implement task routing

3. **Email Service**
   - Extract IMAP functionality
   - Create service-specific volumes
   - Implement webhook processing

4. **Scheduler Service**
   - Extract Celery Beat
   - Create service-specific config
   - Implement schedule management

### Phase 4: Infrastructure & Deployment (Week 9-10)
1. **Docker Optimization**
   - Create service-specific Dockerfiles
   - Implement multi-stage builds
   - Add resource limits

2. **Orchestration Setup**
   - Implement Docker Compose for development
   - Create Kubernetes manifests
   - Add service discovery

3. **Monitoring & Logging**
   - Implement centralized logging
   - Add metrics collection
   - Create dashboards

---

## 📋 Implementation Plan

### Step 1: Create Service Structure
```bash
# Create service directories
mkdir -p services/{api-gateway,worker-service,scheduler-service,email-service,notification-service}
mkdir -p shared/{models,database,utils,schemas}
mkdir -p infrastructure/{docker,k8s,terraform}
```

### Step 2: Extract Shared Code
```python
# shared/models/__init__.py
from .user import User
from .task import Task
from .task_update import TaskUpdate
from .executive_order import ExecutiveOrder
from .daily_eo_summary import DailyEOSummary

__all__ = [
    'User', 'Task', 'TaskUpdate', 
    'ExecutiveOrder', 'DailyEOSummary'
]
```

### Step 3: Service-Specific Requirements
```txt
# services/api-gateway/requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
redis==5.0.1
```

```txt
# services/worker-service/requirements.txt
celery==5.3.4
redis==5.0.1
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
openai==1.3.7
pydantic==2.5.0
pytz==2025.2
```

```txt
# services/email-service/requirements.txt
imaplib2==3.6
requests==2.31.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
fastapi==0.104.1
pydantic==2.5.0
python-multipart==0.0.6
```

### Step 4: Service-Specific Dockerfiles
```dockerfile
# services/api-gateway/Dockerfile
FROM python:3.10-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared libraries
COPY ../shared ./shared

# Copy service code
COPY src ./src

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# services/worker-service/Dockerfile
FROM python:3.10-slim as base

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../shared ./shared
COPY src ./src

RUN useradd --create-home --shell /bin/bash app
USER app

CMD ["celery", "-A", "src.workflow.celery_app", "worker", "--loglevel=info"]
```

### Step 5: Updated Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  api-gateway:
    build: ./services/api-gateway
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker-service:
    build: ./services/worker-service
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    healthcheck:
      test: ["CMD", "celery", "-A", "src.workflow.celery_app", "inspect", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
    depends_on:
      redis:
        condition: service_healthy

  scheduler-service:
    build: ./services/scheduler-service
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    healthcheck:
      test: ["CMD", "celery", "-A", "src.workflow.celery_app", "inspect", "ping"]
      interval: 30s
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
    depends_on:
      redis:
        condition: service_healthy

  email-service:
    build: ./services/email-service
    environment:
      - API_ENDPOINT=http://api-gateway:8000/api/email/webhook
      - DATABASE_URL=${DATABASE_URL}
    volumes:
      - ./attachments:/app/attachments:ro
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://api-gateway:8000/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    depends_on:
      api-gateway:
        condition: service_healthy

  notification-service:
    build: ./services/notification-service
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT}
      - SMTP_USERNAME=${SMTP_USERNAME}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
    volumes:
      - ./outbox:/app/outbox
    healthcheck:
      test: ["CMD", "python", "-c", "import smtplib; smtplib.SMTP('${SMTP_HOST}', ${SMTP_PORT})"]
      interval: 60s
      timeout: 10s
      retries: 3

  db:
    image: postgres:13
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G

  redis:
    image: redis:7
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

volumes:
  postgres_data:
  redis_data:
```

---

## 🔧 Service-Specific Details

### API Gateway Service
```python
# services/api-gateway/src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.database import init_db
from shared.models import Base
from .routes import auth, dashboard, email_webhook

app = FastAPI(title="DOL EO Management API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(email_webhook.router, prefix="/api/email", tags=["Email"])

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}
```

### Worker Service
```python
# services/worker-service/src/workflow/celery_app.py
from celery import Celery
from shared.database import get_database_url

celery_app = Celery(
    "dol_eo_worker",
    broker=get_database_url(),
    backend=get_database_url(),
    include=[
        "src.workflow.tasks",
        "src.workflow.ai_tasks",
        "src.workflow.email_tasks"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "src.workflow.tasks.*": {"queue": "default"},
        "src.workflow.ai_tasks.*": {"queue": "ai"},
        "src.workflow.email_tasks.*": {"queue": "email"},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
```

### Email Service
```python
# services/email-service/src/email/service_manager.py
import asyncio
from shared.database import get_session
from .imap_client import IMAPClient
from .webhook_processor import WebhookProcessor

class EmailServiceManager:
    def __init__(self):
        self.imap_client = IMAPClient()
        self.webhook_processor = WebhookProcessor()
    
    async def start(self):
        """Start email service"""
        await self.imap_client.connect()
        await self.webhook_processor.start()
        
        # Start monitoring
        while True:
            await self.process_emails()
            await asyncio.sleep(30)
    
    async def process_emails(self):
        """Process incoming emails"""
        emails = await self.imap_client.fetch_new_emails()
        for email in emails:
            await self.webhook_processor.process_email(email)

if __name__ == "__main__":
    manager = EmailServiceManager()
    asyncio.run(manager.start())
```

---

## 🏗️ Infrastructure Changes

### Kubernetes Manifests
```yaml
# infrastructure/k8s/api-gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: dol-eo/api-gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
          requests:
            cpu: "500m"
            memory: "256Mi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Terraform Infrastructure
```hcl
# infrastructure/terraform/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ECS Cluster
resource "aws_ecs_cluster" "dol_eo_cluster" {
  name = "dol-eo-management"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# RDS Database
resource "aws_db_instance" "dol_eo_db" {
  identifier           = "dol-eo-db"
  engine               = "postgres"
  engine_version       = "13.7"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  
  db_name  = "dol_db"
  username = var.db_username
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.database.id]
  db_subnet_group_name   = aws_db_subnet_group.dol_eo.name
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "dol_eo_redis" {
  cluster_id           = "dol-eo-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis6.x"
  port                 = 6379
}
```

---

## 🧪 Testing Strategy

### Unit Tests
```python
# services/api-gateway/tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from shared.database import get_test_db
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db():
    return get_test_db()

def test_login_success(client, db):
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Integration Tests
```python
# tests/integration/test_email_workflow.py
import pytest
from services.api_gateway.src.main import app as api_app
from services.worker_service.src.workflow.celery_app import celery_app
from fastapi.testclient import TestClient

@pytest.fixture
def api_client():
    return TestClient(api_app)

def test_email_webhook_to_task_processing(api_client):
    # Send email webhook
    response = api_client.post("/api/email/webhook", json={
        "id": "test-email-001",
        "subject": "Daily Task Update",
        "sender": "test@example.com",
        "body": "Task: Test Task\nProgress: 50%"
    })
    assert response.status_code == 200
    
    # Check task was created
    # This would require checking the database or task queue
```

### Load Testing
```python
# tests/load/test_api_performance.py
import asyncio
import aiohttp
import time

async def test_api_load():
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        tasks = []
        
        # Create 100 concurrent requests
        for i in range(100):
            task = session.get("http://localhost:8000/health")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        success_count = sum(1 for r in responses if r.status == 200)
        print(f"Success rate: {success_count}/100")
        print(f"Total time: {end_time - start_time:.2f}s")
```

---

## 🚀 Deployment Strategy

### Development Environment
```bash
# Local development with Docker Compose
docker-compose up -d

# Service-specific development
cd services/api-gateway
docker-compose up -d api-gateway db redis
```

### Staging Environment
```bash
# Deploy to staging
kubectl apply -f infrastructure/k8s/staging/

# Run database migrations
kubectl exec -it deployment/api-gateway -- alembic upgrade head
```

### Production Environment
```bash
# Deploy to production
kubectl apply -f infrastructure/k8s/production/

# Blue-green deployment
kubectl rollout status deployment/api-gateway-v2
kubectl delete deployment/api-gateway-v1
```

---

## 📊 Monitoring & Observability

### Logging Strategy
```python
# shared/utils/logging.py
import logging
import structlog
from typing import Any

def setup_logging(service_name: str) -> None:
    """Setup structured logging for services"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
```

### Metrics Collection
```python
# shared/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# API Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

# Worker Metrics
TASK_COUNT = Counter('celery_tasks_total', 'Total Celery tasks', ['queue', 'status'])
TASK_DURATION = Histogram('celery_task_duration_seconds', 'Celery task duration')

# Database Metrics
DB_CONNECTIONS = Gauge('database_connections_active', 'Active database connections')
DB_QUERY_DURATION = Histogram('database_query_duration_seconds', 'Database query duration')
```

### Health Checks
```python
# services/api-gateway/src/health.py
from fastapi import APIRouter, Depends
from shared.database import get_db
from shared.utils.metrics import REQUEST_COUNT

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "service": "api-gateway"}

@router.get("/health/detailed")
async def detailed_health_check(db=Depends(get_db)):
    """Detailed health check with dependencies"""
    try:
        # Check database
        db.execute("SELECT 1")
        
        # Check Redis
        # redis.ping()
        
        return {
            "status": "healthy",
            "service": "api-gateway",
            "dependencies": {
                "database": "healthy",
                "redis": "healthy"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "api-gateway",
            "error": str(e)
        }
```

---

## 🔄 Rollback Plan

### Immediate Rollback (5 minutes)
```bash
# Rollback to previous deployment
kubectl rollout undo deployment/api-gateway
kubectl rollout undo deployment/worker-service
kubectl rollout undo deployment/email-service

# Verify rollback
kubectl rollout status deployment/api-gateway
```

### Database Rollback
```bash
# Restore from backup
pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME backup.sql

# Or rollback migrations
kubectl exec -it deployment/api-gateway -- alembic downgrade -1
```

### Service Rollback
```bash
# Switch back to monolithic deployment
docker-compose down
docker-compose -f docker-compose.monolithic.yml up -d
```

---

## 📈 Migration Checklist

### Pre-Migration
- [ ] Complete code analysis and dependency mapping
- [ ] Create shared libraries and utilities
- [ ] Set up CI/CD pipelines for new services
- [ ] Create monitoring and alerting
- [ ] Prepare rollback procedures
- [ ] Train team on new architecture

### Migration Steps
- [ ] Deploy shared infrastructure (database, Redis)
- [ ] Deploy API Gateway service
- [ ] Deploy Worker service
- [ ] Deploy Email service
- [ ] Deploy Scheduler service
- [ ] Deploy Notification service
- [ ] Update DNS and load balancers
- [ ] Verify all services are healthy

### Post-Migration
- [ ] Monitor service performance
- [ ] Verify all functionality works
- [ ] Update documentation
- [ ] Clean up old monolithic code
- [ ] Optimize resource allocation
- [ ] Plan next iteration

---

## 🎯 Success Metrics

### Performance Metrics
- **Response Time**: API Gateway < 200ms
- **Throughput**: 1000+ requests/second
- **Availability**: 99.9% uptime
- **Error Rate**: < 0.1%

### Operational Metrics
- **Deployment Time**: < 5 minutes
- **Rollback Time**: < 2 minutes
- **Mean Time to Recovery**: < 10 minutes
- **Resource Utilization**: 70-80%

### Business Metrics
- **Email Processing**: 100% success rate
- **Task Updates**: Real-time processing
- **Daily Summaries**: Delivered on time
- **User Satisfaction**: Improved response times

---

## 📚 Additional Resources

### Documentation
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Deployment Strategies](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Microservices Patterns](https://microservices.io/patterns/)

### Tools
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Tracing**: Jaeger or Zipkin
- **Service Mesh**: Istio or Linkerd

### Security
- **Secrets Management**: HashiCorp Vault
- **Network Policies**: Kubernetes Network Policies
- **Container Security**: Trivy, Falco
- **API Security**: OAuth2, JWT, Rate Limiting

---

*This document should be updated as the migration progresses and new requirements are discovered.*
