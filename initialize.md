# DOL EO Management - Frontend Developer Setup Guide

## 📋 Prerequisites

Before starting, ensure you have the following installed on your system:

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Git** (for cloning the repository)
- **PostgreSQL Client** (optional, for direct database access)

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
- **PostgreSQL Database** (port 5432) - Stores all application data
- **Redis** (port 6379) - Handles background task processing
- **FastAPI Application** (port 8000) - **Your API endpoint**
- **Celery Worker** (background processing) - Handles async tasks

### 4. Initialize Database

```bash
# Run database migrations
docker-compose exec api alembic upgrade head

# Verify database is ready
docker-compose exec db psql -U dol_user -d dol_db -c "\dt"
```

### 5. Add Initial Users

The system comes with pre-configured users. You can add them via API:

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

### Database Access (Optional)

If you need direct database access for debugging:

```bash
# Connect to PostgreSQL database
docker-compose exec db psql -U dol_user -d dol_db

# View tables
\dt

# View sample data
SELECT * FROM users LIMIT 5;
SELECT * FROM executive_orders LIMIT 5;
SELECT * FROM tasks LIMIT 5;
```

## 🧪 Testing the Setup

### 1. Health Check

```bash
curl http://localhost:8000/health_check
```

Expected response:
```json
{
  "success": true,
  "message": "Server is up and running"
}
```

### 2. Authentication Test

```bash
# Login with default user
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jack.smith@lumenlighthouse.ai",
    "password": "Lumen@2025"
  }'
```

### 3. Dashboard Endpoints Test

```bash
# Get user info (requires token from login)
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Test CFO endpoints
curl -X GET "http://localhost:8000/dashboard/cfo/executive-orders" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 📁 API & Database Overview

### Key Services for Frontend Development

```
DOL-EO-Management/
├── src/
│   ├── models/                 # Database models (for reference)
│   ├── routes/                 # API endpoints
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── application.py     # Workflow endpoints
│   │   └── dashboard.py       # Dashboard endpoints
│   └── workflow/              # Background processing
├── docker-compose.yml         # Service configuration
└── initialize.md             # This file
```

### Database Schema Overview

**Main Tables:**
- `users` - User accounts and roles
- `executive_orders` - EO data
- `tasks` - Task assignments and status
- `daily_updates` - Employee progress updates
- `email_logs` - Email communication tracking

## 🔑 Default Users

The system includes these default users with role-based access:

### CFO (Admin Role)
- **Jack Smith** (jack.smith@lumenlighthouse.ai) - CFO
- **Kevin Brown** (Kevin.Brown@lumenlighthouse.ai) - Deputy CFO
- **Westley Everette** (Westley.Everette@lumenlighthouse.ai) - Associate Deputy CFO

### PMO (Reviewer Role)
- **Dylan Sachetti** (Dylan.Sachetti@lumenlighthouse.ai) - Director of Compliance
- **Ayesha Ahsan** (Ayesha.Ahsan@lumenlighthouse.ai) - Director of Business Process Improvement
- **Hibbi Iqbal** (Hibbi.Iqbal@lumenlighthouse.ai) - Director of Financial Reporting
- **Sophia Carty** (Sophia.Carty@lumenlighthouse.ai) - Director of Accounting
- **Robert Springfiled** (Robert.Springfiled@lumenlighthouse.ai) - Director of Security and Technology
- **Micheal Kim** (Micheal.Kim@lumenlighthouse.ai) - Director of Travel Management

### Employees (Executor Role)
- **Zacira Copper** (Zacira.Copper@lumenlighthouse.ai) - Supervisor
- **Jada Mccray** (Jada.Mccray@lumenlighthouse.ai) - Lead Accountant
- **Jose Flores** (Jose.Flores@lumenlighthouse.ai) - Lead Accountant

**Default Password for all users:** `Lumen@2025`

## 🚀 API Endpoints for Frontend Integration

### 🔐 Authentication (Required for all protected endpoints)
```javascript
// Login
POST /auth/login
{
  "email": "user@example.com",
  "password": "password"
}

// Get current user
GET /auth/me
Authorization: Bearer <token>

// Logout
POST /auth/logout
Authorization: Bearer <token>
```

### 📊 Dashboard Endpoints (Role-Based Access)

#### CFO Dashboard (Admin Role)
```javascript
// Get all executive orders
GET /dashboard/cfo/executive-orders
Authorization: Bearer <token>

// Get all employees
GET /dashboard/cfo/employees
Authorization: Bearer <token>

// Get all tasks
GET /dashboard/cfo/tasks
Authorization: Bearer <token>

// Update PMOs for an EO
PUT /dashboard/cfo/executive-orders/{eo_id}/pmo
Authorization: Bearer <token>
{
  "pmo_ids": ["uuid1", "uuid2"]
}
```

#### PMO Dashboard (Reviewer Role)
```javascript
// Get tasks for this PMO
GET /dashboard/pmo/tasks
Authorization: Bearer <token>

// Get employees under this PMO
GET /dashboard/pmo/employees
Authorization: Bearer <token>

// Get daily updates from employees
GET /dashboard/pmo/daily-updates
Authorization: Bearer <token>

// Update task assignee
PUT /dashboard/pmo/tasks/{task_id}/assignee
Authorization: Bearer <token>
{
  "assignee_id": "user_uuid"
}
```

#### Employee Dashboard (Executor Role)
```javascript
// Get employee's own updates
GET /dashboard/employee/my-updates
Authorization: Bearer <token>

// Get assigned active tasks
GET /dashboard/employee/active-tasks
Authorization: Bearer <token>

// Create daily update
POST /dashboard/employee/daily-update
Authorization: Bearer <token>
{
  "task_id": "task_uuid",
  "update_text": "Progress update",
  "progress_pct": 75,
  "hours_spent": 4.5,
  "status_note": "On track",
  "blockers": {"technical": ["API issue"]},
  "risks": {"schedule": "May miss deadline"},
  "next_actions": {"immediate": ["Fix API"]}
}
```

### 🔄 Workflow Endpoints (Backend Processing)
```javascript
// Process new Executive Order
POST /workflow/eo
{
  "title": "EO Title",
  "description": "EO Content",
  "message_id": "unique_id"
}

// Process PMO email response
POST /webhook/pmo_email
{
  "message_id": "email_id",
  "body_text": "PMO response content",
  "related_eo_id": "eo_uuid"
}
```

## 🔧 Troubleshooting for Frontend Developers

### Common API Issues

1. **API Not Responding:**
   ```bash
   # Check if API is running
   curl http://localhost:8000/health_check
   
   # Check service status
   docker-compose ps
   ```

2. **Authentication Errors:**
   - Verify token is included in Authorization header
   - Check if token has expired (30 minutes)
   - Ensure correct Bearer token format

3. **CORS Issues:**
   - API supports CORS for localhost development
   - Check browser console for CORS errors
   - Verify frontend is running on allowed origin

4. **Database Connection Issues:**
   ```bash
   # Restart all services
   docker-compose restart
   
   # Check database logs
   docker-compose logs db
   ```

### API Response Format

All API responses follow this format:
```javascript
{
  "success": true/false,
  "message": "Human readable message",
  "data": {
    // Response data here
  },
  "pagination": {
    "total": 100,
    "limit": 50,
    "offset": 0
  }
}
```

### Error Handling

```javascript
// Example error response
{
  "detail": "Error message",
  "status_code": 400
}

// Authentication error
{
  "detail": "Could not validate credentials",
  "status_code": 401
}
```

### Logs and Debugging

```bash
# View API logs
docker-compose logs api

# Follow API logs in real-time
docker-compose logs -f api

# Check specific endpoint logs
docker-compose logs api | grep "GET /dashboard"
```

## 🧪 Testing API Integration

### Frontend Integration Examples

#### 1. Authentication Flow
```javascript
// Login and store token
const login = async (email, password) => {
  const response = await fetch('http://localhost:8000/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const data = await response.json();
  localStorage.setItem('token', data.access_token);
  return data.user;
};

// Use token for authenticated requests
const getDashboardData = async () => {
  const token = localStorage.getItem('token');
  const response = await fetch('http://localhost:8000/dashboard/cfo/executive-orders', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};
```

#### 2. Role-Based Dashboard Access
```javascript
// Check user role and redirect to appropriate dashboard
const getDashboardByRole = (user) => {
  switch(user.role) {
    case 'admin':
      return '/cfo-dashboard';
    case 'reviewer':
      return '/pmo-dashboard';
    case 'executor':
      return '/employee-dashboard';
    default:
      return '/login';
  }
};
```

#### 3. Daily Update Creation
```javascript
const createDailyUpdate = async (updateData) => {
  const token = localStorage.getItem('token');
  const response = await fetch('http://localhost:8000/dashboard/employee/daily-update', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(updateData)
  });
  return response.json();
};
```

## 📊 API Monitoring & Health Checks

### Health Check Endpoint
```bash
# Check if API is running
curl http://localhost:8000/health_check
```

### API Performance
- **Response Time:** Monitor API response times in browser dev tools
- **Error Rates:** Check browser console for failed requests
- **Authentication:** Monitor token expiration and refresh

## 🔒 Security for Frontend Integration

### Authentication Best Practices
1. **Token Storage:** Store JWT tokens securely (localStorage/sessionStorage)
2. **Token Expiration:** Handle 401 errors and redirect to login
3. **HTTPS:** Always use HTTPS in production
4. **CORS:** Ensure proper CORS configuration for your domain

### API Security
- **Authorization Headers:** Always include Bearer tokens
- **Input Validation:** Validate data before sending to API
- **Error Handling:** Don't expose sensitive error details to users

## 📈 Frontend Development Tips

### Development Workflow
1. **API First:** Use the interactive docs at `/docs` to test endpoints
2. **Mock Data:** Use the provided test users for development
3. **Error Handling:** Implement proper error handling for all API calls
4. **Loading States:** Show loading indicators during API calls

### Testing Strategy
1. **Unit Tests:** Test API integration functions
2. **Integration Tests:** Test complete user flows
3. **E2E Tests:** Test full application workflows

## 📞 Support & Resources

### API Documentation
- **Interactive Docs:** http://localhost:8000/docs
- **Alternative Docs:** http://localhost:8000/redoc
- **OpenAPI Schema:** http://localhost:8000/openapi.json

### Getting Help
1. **API Issues:** Check the troubleshooting section above
2. **Authentication Problems:** Verify token format and expiration
3. **CORS Issues:** Check browser console and network tab
4. **Data Issues:** Use database access commands to verify data

### Development Resources
- **Test Users:** Use the provided default users for testing
- **Sample Data:** Create test EOs and tasks via API
- **Role Testing:** Test different user roles for access control

---

**Last Updated:** August 25, 2025
**Version:** 1.0.0
**Target Audience:** Frontend Developers
