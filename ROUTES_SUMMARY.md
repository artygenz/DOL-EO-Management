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

### **Reviewer Users**
- Can see executive orders assigned to their org role
- Limited access to tasks and email logs

### **Executor Users**
- Can only see their assigned tasks
- Limited access to executive orders and email logs

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
