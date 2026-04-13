# DOL-EO-Management: Executive Order Task Management System

## 🚀 Project Overview

A comprehensive **Executive Order management system** for the U.S. Department of Labor that automates task assignment, tracking, and daily update workflows through email integration and AI-powered processing.

**Key Features:**
- 📧 **Email-driven workflow** with IMAP integration
- 🤖 **AI-powered task extraction** and processing
- 📊 **Role-based dashboard** for PMOs, admins, and executors
- 📈 **Daily update aggregation** and reporting
- 🔐 **JWT-based authentication** with role-based access control

---

## 🔄 System Workflows

### 📧 Email Processing Workflow

![Email Processing Workflow](diagrams/images/email-processing-workflow.png)

The email processing system automatically handles different types of incoming emails:
- **Executive Orders**: PDF attachments are processed for task extraction
- **Daily Updates**: Employee progress reports are parsed and stored
- **PMO Responses**: Task approval/rejection processing
- **System Emails**: Automated notifications and reminders

### 🔐 Authentication & Authorization Flow

![Authentication Flow](diagrams/images/authentication-flow.png)

The authentication system provides secure, role-based access:
- **JWT Token Generation**: Secure token-based authentication
- **Role-based Filtering**: Data access based on user roles
- **Permission Validation**: Ensures users can only access authorized data

### 📋 Task Management Workflow

![Task Management Workflow](diagrams/images/task-management-workflow.png)

The complete task lifecycle from creation to completion:
- **EO Processing**: AI extracts tasks from Executive Orders
- **PMO Review**: Tasks are reviewed and approved/rejected
- **Executor Assignment**: Approved tasks are assigned to executors
- **Progress Tracking**: Daily updates track task progress
- **Summary Generation**: Automated daily summaries for PMOs

### 📊 Daily Update Aggregation Workflow

The daily update system automatically processes and aggregates task updates:

```mermaid
graph TD
    A[Daily Trigger 6PM] --> B[Scheduler]
    B --> C[Get Active EOs]
    C --> D[Process Each EO]
    
    D --> E[Get Tasks & Updates]
    E --> F[Calculate Progress]
    F --> G[Generate Summary]
    G --> H[Send to PMO]
    H --> I[Update Database]
    
    D --> J{More EOs?}
    J -->|Yes| D
    J -->|No| K[Complete]
```

### 🏗️ System Architecture

![System Architecture](diagrams/images/system-architecture.png)

The system architecture shows the interaction between:
- **External Services**: IMAP server and OpenAI API
- **Application Layer**: FastAPI, Celery workers, and schedulers
- **Data Layer**: PostgreSQL database and Redis cache
- **Services**: Email processing and AI services

### 🔄 User Interaction Flow

![User Interaction Flow](diagrams/images/user-interaction-flow.png)


Different user roles have access to different features:
- **Admin**: Full system access and management
- **PMO/Reviewer**: EO and task management for assigned projects
- **Executor**: Task viewing and daily update submission

---

## 🏗️ Architecture

### **Technology Stack**
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Task Queue**: Celery with Redis
- **Email**: IMAP integration with `lumenlighthouse.ai`
- **AI**: OpenAI GPT-4 integration for content processing
- **Authentication**: JWT tokens with bcrypt password hashing
- **Containerization**: Docker & Docker Compose

### **Core Components**
- **API Gateway**: FastAPI application with modular routes
- **Email Service**: IMAP listener with webhook processing
- **Worker Service**: Celery background tasks for AI processing
- **Scheduler**: Celery Beat for periodic tasks
- **Database**: PostgreSQL with Alembic migrations

---

## 🏗️ Getting Started

### Prerequisites

Before starting, ensure you have the following installed:

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Git** (for cloning the repository)
- **PostgreSQL Client** (optional, for direct database access)

### 1. Clone Repository

```bash
git clone <repository-url>
cd DOL-EO-Management
```

### 2. Environment Setup

Create a `.env` file in the root directory:

```bash
# Copy the example environment file
cp .env.local .env
```

Edit the `.env` file with your configuration:

```env
# Database Configuration
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=dol_db
POSTGRES_USER=dol_user
POSTGRES_PASSWORD=artygenz

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# Application Environment
APP_ENV=local

# JWT Configuration
JWT_SECRET=your-secret-key-change-in-production
JWT_ALG=HS256

# IMAP Configuration (for email service)
IMAP_USERNAME=your_email@lumenlighthouse.ai
IMAP_PASSWORD=your_app_password
IMAP_HOST=lumenlighthouse.ai
IMAP_PORT=993
IMAP_MAILBOX=INBOX
```

### 3. Start the Services

```bash
# Build and start all services
docker-compose up -d

# Or start with logs visible
docker-compose up
```

This will start:
- **PostgreSQL Database** (port 5433) - Stores all application data
- **Redis** (port 6380) - Handles background task processing
- **FastAPI Application** (port 8000) - **Your API endpoint**
- **Celery Worker** (background processing) - Handles async tasks
- **Celery Beat** (scheduler) - Handles periodic tasks
- **IMAP Listener** - Monitors email for new messages

### 4. Initialize Database

```bash
# Run database migrations
docker-compose exec api alembic upgrade head

# Verify database is ready
docker-compose exec db psql -U dol_user -d dol_db -c "\dt"
```

### 5. Load Seed Data (Optional)

The repository includes a database seed file with pre-configured users and test data:

```bash
# Import seed data (users, test EOs, etc.)
docker-compose run --rm import-db
```

### 6. Add Initial Users (Alternative)

If you prefer to add users manually via API:

```bash
# Add users in bulk
curl -X POST "http://localhost:8000/app/users/bulk" \
  -H "Content-Type: application/json" \
  -d @phaseandtasks.txt
```

---

## 🔧 API Documentation

Once the services are running, you can access:

- **Interactive API Docs:** http://localhost:8000/docs
- **Alternative API Docs:** http://localhost:8000/redoc
- **OpenAPI Schema:** http://localhost:8000/openapi.json

## 📊 Database Management

### Export Current Data

To capture the current database state for sharing with others:

```bash
# Export all data to database_seed.sql
./scripts/db_export.sh

# Or run manually
docker-compose run --rm export-db
```

<img width="1280" height="720" alt="image" src="https://github.com/user-attachments/assets/4e9dd2c7-86e5-4a59-804a-80cd2e8567b3" />


### Import Seed Data

To load pre-configured data:

```bash
# Import seed data
docker-compose run --rm import-db
```

### Database Access (Optional)

For direct database access during development:

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U dol_user -d dol_db

# View tables
\dt

# View users
SELECT id, name, email, role, org_role FROM users;

# View executive orders
SELECT id, title, status, created_at FROM executive_orders;

# View tasks
SELECT id, title, status, assignee_id FROM tasks;
```

## 🔐 Authentication & Authorization

### User Roles

The system has three user roles:

1. **Admin** (`role: "admin"`) - CFOs and administrators
   - Can manage all EOs, users, and PMO assignments
   - Access to all dashboard endpoints
   - Can view system statistics and logs

2. **Reviewer** (`role: "reviewer"`) - PMOs and managers
   - Can review and approve/reject tasks
   - Access to assigned EOs and tasks via PMO endpoints
   - Can view daily summaries for their assigned EOs

3. **Executor** (`role: "executor"`) - Employees and workers
   - Can work on assigned tasks
   - Can create daily updates via email
   - Limited access to executive orders and email logs

### Authentication Flow

```javascript
// 1. Login to get JWT token
const loginResponse = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'jack.smith@lumenlighthouse.ai',
    password: 'Lumen@2025'
  })
});

const { access_token, user } = await loginResponse.json();

// 2. Use token for authenticated requests
const response = await fetch('http://localhost:8000/dashboard/executive-orders', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  }
});

// 3. Logout to invalidate token
await fetch('http://localhost:8000/auth/logout', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
```

## 📧 Email Workflow

### Email Processing System

The system includes a comprehensive email processing workflow:

1. **IMAP Listener**: Monitors `lumenlighthouse.ai` inbox for new emails
2. **Webhook Processing**: Forwards emails to FastAPI webhook endpoint
3. **Content Analysis**: AI-powered extraction of task updates and EO content
4. **Task Assignment**: Automatic task creation and assignment
5. **Daily Aggregation**: Automated daily summaries for PMOs

### Email Types Supported

- **Executive Order Emails**: PDF attachments processed for task extraction
- **Daily Update Emails**: Employee progress reports automatically parsed
- **PMO Response Emails**: Task approval/rejection processing
- **System Notifications**: Automated status updates and reminders

## 🗄️ Database Schema

### Core Models

- **Users**: Authentication and role management
- **Executive Orders**: EO metadata and status tracking
- **Tasks**: Individual tasks with assignments and status
- **Task Updates**: Daily progress updates from employees
- **Daily EO Summaries**: Aggregated daily reports for PMOs
- **Email Logs**: Audit trail of all email processing
- **EO-PMO Assignments**: Role-based access control

### Key Relationships

- EOs are assigned to PMOs via `eo_pmo_assignments`
- Tasks are assigned to executors via `tasks.assignee_id`
- Daily updates are linked to tasks and EOs
- Email logs track all processing activities

---

## 📚 Documentation

For detailed documentation, see the `docs/` directory:

- **API Routes**: `docs/ROUTES_SUMMARY.md` - Complete API documentation
- **Email Service**: `docs/EMAIL_SERVICE_DOCUMENTATION.md` - Email processing system
- **Daily Updates**: `docs/DAILY_UPDATE_SYSTEM.md` - Task update workflow
- **Backend Solutions**: `docs/SOLUTIONS_SUMMARY.md` - Implementation fixes
- **Microservices**: `docs/MICROSERVICES_MIGRATION_GUIDE.md` - Future architecture

---

## 🧪 Testing

The project includes comprehensive test suites organized by functionality:

   ```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/auth/          # Authentication tests
pytest tests/email/         # Email service tests
pytest tests/workflow/      # Workflow and task tests
pytest tests/celery/        # Background task tests
pytest tests/pmo/           # PMO-specific tests
```

### Test Coverage

- **API Endpoints**: Authentication, dashboard, and PMO endpoints
- **Email Processing**: IMAP integration and webhook handling
- **Workflow Tasks**: Celery background job processing
- **Database Operations**: Model relationships and queries
- **AI Integration**: OpenAI API integration and content processing

---

## 🚀 Deployment

### Development
```bash
docker-compose up -d
```

### Production
See `docs/MICROSERVICES_MIGRATION_GUIDE.md` for production deployment strategies.

### Environment Variables

Key environment variables for production:

```env
# Security
JWT_SECRET=your-production-secret-key
APP_ENV=production

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Email
IMAP_USERNAME=your_email@lumenlighthouse.ai
IMAP_PASSWORD=your_app_password

# AI
OPENAI_API_KEY=your_openai_api_key
```

---

## 🔧 Development

### Project Structure

```
DOL-EO-Management/
├── src/
│   ├── main.py              # FastAPI application entry point
│   ├── routes/              # API endpoint modules
│   ├── models/              # Database models
│   ├── workflow/            # Celery tasks and workers
│   ├── email/               # Email service components
│   ├── core/                # Shared utilities and config
│   └── db/                  # Database operations
├── tests/                   # Organized test suites
├── docs/                    # Documentation
├── diagrams/                # Workflow diagrams
├── alembic/                 # Database migrations
├── scripts/                 # Utility scripts
└── docker-compose.yml       # Service orchestration
```

### Key Features Implemented

- ✅ **User Authentication** with JWT tokens
- ✅ **Role-based Access Control** (Admin, Reviewer, Executor)
- ✅ **Executive Order Management** with PMO assignments
- ✅ **Task Assignment and Tracking**
- ✅ **Email Integration** with IMAP listener
- ✅ **AI-powered Content Processing**
- ✅ **Daily Update Workflow**
- ✅ **Automated Reporting** and summaries
- ✅ **Database Migrations** with Alembic
- ✅ **Background Task Processing** with Celery
- ✅ **Comprehensive Testing** suite

---

*This system is actively maintained and used for DOL Executive Order management workflows.*
