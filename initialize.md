# DOL EO Management - Frontend Developer Setup Guide

## 📋 Prerequisites

Before starting, ensure you have the following installed on your system:

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Git** (for cloning the repository)
- **PostgreSQL Client** (optional, for direct database access)
- **Node.js/npm** (for frontend development)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd DOL-EO-Management
```

### 2. Environment Setup

Create a `.env` file in the root directory:

```bash
# Copy the example environment file
cp env.txt .env
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
OPENAI_MODEL=gpt-4.1

# Application Environment
APP_ENV=local

# JWT Configuration
JWT_SECRET=your-secret-key-change-in-production
JWT_ALG=HS256
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
curl -X POST "http://localhost:8000/users/bulk" \
  -H "Content-Type: application/json" \
  -d @phaseandtasks.txt
```

## 🔧 Frontend Development Setup

### API Documentation

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

2. **Reviewer** (`role: "reviewer"`) - PMOs and managers
   - Can review and approve/reject tasks
   - Access to assigned EOs and tasks

3. **Executor** (`role: "executor"`) - Employees and workers
   - Can work on assigned tasks
   - Can create daily updates

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
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  }
});
```

## 📡 API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | User login |
| GET | `/auth/me` | Get current user info |
| POST | `/auth/logout` | User logout |

### Application Workflow Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/workflow/eo` | Process new Executive Order |
| POST | `/webhook/pmo_email` | Process PMO email response |
| POST | `/users/bulk` | Add multiple users |

### Dashboard Endpoints (Protected)

| Method | Endpoint | Description | Role Required |
|--------|----------|-------------|---------------|
| GET | `/dashboard/health` | Health check | Any authenticated |
| GET | `/dashboard/executive-orders` | List EOs | Role-based access |
| GET | `/dashboard/tasks` | List tasks | Role-based access |
| GET | `/dashboard/email-logs` | List email logs | Role-based access |

### CFO/Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/dashboard/cfo/assign-pmos/{eo_id}` | Assign PMOs to EO |
| GET | `/dashboard/cfo/eo-pmo-assignments/{eo_id}` | Get EO PMO assignments |
| DELETE | `/dashboard/cfo/remove-pmo/{eo_id}/{pmo_id}` | Remove PMO from EO |

### PMO Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/pmo/assigned-eos` | Get assigned EOs |
| GET | `/dashboard/pmo/assigned-tasks` | Get assigned tasks |
| GET | `/dashboard/pmo/employee-updates` | Get employee updates |

### Employee Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/employee/active-tasks` | Get active tasks |
| POST | `/dashboard/employee/daily-update` | Create daily update |
| GET | `/dashboard/employee/my-updates` | Get own updates |

## 🗄️ Data Models

### Executive Order
```json
{
  "id": "uuid",
  "title": "string",
  "message_id": "string",
  "status": "received|processed|error",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Task
```json
{
  "id": "uuid",
  "title": "string",
  "description": "string",
  "status": "pending|in_progress|completed|approved|rejected",
  "assignee_id": "uuid",
  "due_date": "date",
  "category": "string",
  "remarks": "string"
}
```

### User
```json
{
  "id": "uuid",
  "name": "string",
  "email": "string",
  "role": "admin|reviewer|executor",
  "org_role": "string",
  "is_active": "boolean"
}
```

### Daily Update
```json
{
  "id": "uuid",
  "task_id": "uuid",
  "user_id": "uuid",
  "update_text": "string",
  "progress_pct": "integer",
  "hours_spent": "float",
  "status_note": "string",
  "blockers": "object",
  "risks": "object",
  "next_actions": "object"
}
```

## 🔄 Workflow Overview

### 1. EO Processing
1. **Submit EO** → `/workflow/eo`
2. **System extracts tasks** using AI
3. **Tasks assigned** to executors
4. **PMO review email** sent automatically

### 2. PMO Review
1. **PMO receives email** with tasks
2. **PMO responds** via email
3. **System processes** response via `/webhook/pmo_email`
4. **Tasks updated** based on approval/rejection

### 3. Task Execution
1. **Employees work** on assigned tasks
2. **Daily updates** submitted via API
3. **PMOs review** progress
4. **CFOs monitor** overall progress

## 🧪 Testing

### Test API Endpoints

```bash
# Test authentication
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "jack.smith@lumenlighthouse.ai", "password": "Lumen@2025"}'

# Test protected endpoint
curl -X GET "http://localhost:8000/dashboard/health" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Run Tests

```bash
# Run all tests
docker-compose run --rm pytest

# Run specific test file
docker-compose run --rm pytest tests/test_auth.py
```

## 🐛 Troubleshooting

### Common Issues

1. **Database connection failed**
   ```bash
   # Check if database is running
   docker-compose ps
   
   # Restart database
   docker-compose restart db
   ```

2. **API not responding**
   ```bash
   # Check API logs
   docker-compose logs api
   
   # Restart API
   docker-compose restart api
   ```

3. **Authentication errors**
   ```bash
   # Check if users exist
   docker-compose exec db psql -U dol_user -d dol_db -c "SELECT email, role FROM users;"
   ```

### Service Management

```bash
# View all services
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f db

# Restart specific service
docker-compose restart api

# Stop all services
docker-compose down

# Remove all data (fresh start)
docker-compose down -v
```

## 📚 Additional Resources

- **API Documentation:** http://localhost:8000/docs
- **Database Schema:** Check `src/models/` directory
- **Workflow Logic:** Check `src/workflow/` directory
- **Email Templates:** Check `src/email/` directory

## 🚀 Next Steps

1. **Explore the API** using the interactive docs
2. **Test authentication** with the provided users
3. **Review the data models** to understand the structure
4. **Build your frontend** using the API endpoints
5. **Test the workflow** by processing an EO

Happy coding! 🎉
