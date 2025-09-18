# 🚀 FastAPI Modular Routes Structure

## **📁 Route Organization**

The FastAPI application has been modularized into separate route files for better organization and maintainability.

### **🔐 Authentication Routes (`/src/routes/auth.py`)**
**Prefix**: `/auth`
**Authentication**: None (public endpoints)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | POST | User login with email/password |
| `/auth/me` | GET | Get current user info (requires auth) |
| `/auth/logout` | POST | Logout and revoke token (requires auth) |

### **🔧 Application Routes (`/src/routes/application.py`)**
**Prefix**: `/app`
**Authentication**: None (system endpoints)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/app/workflow/eo` | POST | Queue EO for processing |
| `/app/webhook/pmo_email` | POST | PMO email webhook |
| `/app/users` | POST | Create single user |
| `/app/users/bulk` | POST | Create multiple users |

### **📊 Dashboard Routes (`/src/routes/dashboard.py`)**
**Prefix**: `/dashboard`
**Authentication**: Required (Bearer token)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/dashboard/health` | GET | Dashboard health check |
| `/dashboard/executive-orders` | GET | List executive orders |
| `/dashboard/executive-orders/{eo_id}` | GET | Get EO details |
| `/dashboard/tasks` | GET | Get user tasks |
| `/dashboard/tasks/{task_id}` | GET | Get task details |
| `/dashboard/email-logs` | GET | Get email logs |
| `/dashboard/stats` | GET | Get dashboard statistics |

### **📋 PMO-Specific Routes (`/src/routes/dashboard.py`)**
**Prefix**: `/dashboard/pmo`
**Authentication**: Required (PMO/Reviewer role only)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/dashboard/pmo/assigned-eos` | GET | Get all EOs assigned to PMO |
| `/dashboard/pmo/assigned-eos/{eo_id}/tasks` | GET | Get tasks for specific EO |
| `/dashboard/pmo/assigned-eos-with-tasks` | GET | Get all EOs with tasks (combined) |
| `/dashboard/pmo/tasks` | GET | Get all tasks for PMO's EOs |

### **🏥 System Routes (`/src/main.py`)**
**Prefix**: None
**Authentication**: None

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health_check` | GET | System health check |
| `/docs` | GET | API documentation |
| `/openapi.json` | GET | OpenAPI schema |

## **🔐 Authentication Flow**

1. **Login**: `POST /auth/login`
   ```json
   {
     "email": "user@example.com",
     "password": "password"
   }
   ```

2. **Get Token**: Response includes JWT token
   ```json
   {
     "access_token": "eyJ...",
     "token_type": "bearer",
     "user": {...}
   }
   ```

3. **Use Token**: Include in Authorization header
   ```
   Authorization: Bearer eyJ...
   ```

4. **Logout**: Revoke token
   ```bash
   curl -X POST "/auth/logout" -H "Authorization: Bearer eyJ..."
   ```

## **👥 Role-Based Access Control**

### **Admin Users**
- Can access all dashboard endpoints
- Can see all executive orders and tasks
- Full system access

### **Reviewer/PMO Users**
- Can see executive orders assigned to their org role
- Can access PMO-specific endpoints
- Limited access to tasks and email logs

### **Executor Users**
- Can only see their assigned tasks
- Limited access to executive orders and email logs

## **📋 PMO Endpoints Details**

### **1. Get All EOs Assigned to PMO**
**Endpoint**: `GET /dashboard/pmo/assigned-eos`

**Description**: Fetches all Executive Orders assigned to the current PMO user.

**Query Parameters**:
- `limit` (optional): Number of EOs to return (default: 50, max: 100)
- `offset` (optional): Number of EOs to skip (default: 0)

**Response Example**:
```json
{
  "success": true,
  "message": "Retrieved 3 Executive Orders assigned to PMO",
  "data": {
    "executive_orders": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "title": "Executive Order 2024-01",
        "description": "Implementation of new policies",
        "status": "in_progress",
        "message_id": "msg_123",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-16T14:20:00Z",
        "task_count": 5,
        "pmo_assignment": {
          "assigned_at": "2024-01-15T11:00:00Z",
          "is_primary": true,
          "assigned_by": "admin_user_id"
        }
      }
    ],
    "pagination": {
      "total": 3,
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  }
}
```

### **2. Get Tasks for Specific EO**
**Endpoint**: `GET /dashboard/pmo/assigned-eos/{eo_id}/tasks`

**Description**: Fetches all tasks for a specific Executive Order that is assigned to the current PMO.

**Path Parameters**:
- `eo_id`: UUID of the Executive Order

**Query Parameters**:
- `limit` (optional): Number of tasks to return (default: 50, max: 100)
- `offset` (optional): Number of tasks to skip (default: 0)

### **3. Get All EOs with Tasks (Combined)**
**Endpoint**: `GET /dashboard/pmo/assigned-eos-with-tasks`

**Description**: Fetches all Executive Orders assigned to the current PMO along with their tasks in a single response.

**Query Parameters**:
- `limit` (optional): Number of EOs to return (default: 20, max: 50)
- `offset` (optional): Number of EOs to skip (default: 0)

### **4. Get All Tasks for PMO's EOs**
**Endpoint**: `GET /dashboard/pmo/tasks`

**Description**: Fetches all tasks for all Executive Orders assigned to the current PMO.

**Query Parameters**:
- `limit` (optional): Number of tasks to return (default: 50, max: 100)
- `offset` (optional): Number of tasks to skip (default: 0)

## **📋 API Usage Examples**

### **Login**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "jack.smith@lumenlighthouse.ai", "password": "Lumen@2025"}'
```

### **Access Protected Endpoint**
```bash
curl -X GET "http://localhost:8000/dashboard/health" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### **PMO Endpoints Examples**
```bash
# Get assigned EOs
curl -X GET "http://localhost:8000/dashboard/pmo/assigned-eos" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get tasks for specific EO
curl -X GET "http://localhost:8000/dashboard/pmo/assigned-eos/123e4567-e89b-12d3-a456-426614174000/tasks" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get EOs with tasks
curl -X GET "http://localhost:8000/dashboard/pmo/assigned-eos-with-tasks?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### **Logout**
```bash
curl -X POST "http://localhost:8000/auth/logout" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### **Create Users**
```bash
curl -X POST "http://localhost:8000/app/users/bulk" \
  -H "Content-Type: application/json" \
  -d '[{"name": "User", "email": "user@example.com", "role": "executor"}]'
```

### **Queue EO Processing**
```bash
curl -X POST "http://localhost:8000/app/workflow/eo" \
  -H "Content-Type: application/json" \
  -d '{"message_id": "test-123", "body_text": "EO content..."}'
```

## **🔐 Security & Access Control**

### **Role Requirements**
- PMO endpoints require **PMO/Reviewer role**
- Users with other roles (admin, executor) will receive 403 Forbidden

### **Data Access**
- PMOs can only access EOs they are assigned to
- PMOs can only access tasks for their assigned EOs
- Proper validation ensures no unauthorized access

### **Error Responses**
```json
{
  "detail": "Access denied - PMO role required"
}
```

```json
{
  "detail": "Access denied - PMO not assigned to this EO"
}
```

## **🔧 Development Notes**

- **Modular Structure**: Each route type is in its own file
- **Dependencies**: Properly injected using FastAPI's dependency system
- **Error Handling**: Consistent error responses across all endpoints
- **Documentation**: Auto-generated with FastAPI's built-in docs
- **Testing**: Each route module can be tested independently

## **🚀 Benefits**

1. **Maintainability**: Easier to find and modify specific functionality
2. **Scalability**: Easy to add new route modules
3. **Testing**: Isolated testing of different route types
4. **Documentation**: Clear separation in API docs
5. **Security**: Proper authentication and authorization separation

## **📊 Use Cases**

### **Use Case 1: PMO Dashboard Overview**
**Endpoint**: `GET /dashboard/pmo/assigned-eos`
**Purpose**: Show PMO all their assigned EOs with basic info and task counts

### **Use Case 2: EO Detail View**
**Endpoint**: `GET /dashboard/pmo/assigned-eos/{eo_id}/tasks`
**Purpose**: Show PMO all tasks for a specific EO they're managing

### **Use Case 3: Comprehensive Overview**
**Endpoint**: `GET /dashboard/pmo/assigned-eos-with-tasks`
**Purpose**: Show PMO all their EOs with full task details in one request

### **Use Case 4: Task Management**
**Endpoint**: `GET /dashboard/pmo/tasks`
**Purpose**: Show PMO all tasks across all their assigned EOs
