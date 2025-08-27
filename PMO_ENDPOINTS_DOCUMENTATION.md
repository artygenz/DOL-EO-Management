# 📋 PMO Endpoints Documentation

## 🎯 **Overview**

This document describes the **new PMO-specific endpoints** that allow PMOs (reviewers) to fetch Executive Orders assigned to them and their associated tasks.

## ✅ **Available Endpoints**

### **1. Get All EOs Assigned to PMO**
**Endpoint**: `GET /dashboard/pmo/assigned-eos`

**Description**: Fetches all Executive Orders assigned to the current PMO user.

**Authentication**: Required (PMO/Reviewer role only)

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

---

### **2. Get Tasks for Specific EO**
**Endpoint**: `GET /dashboard/pmo/assigned-eos/{eo_id}/tasks`

**Description**: Fetches all tasks for a specific Executive Order that is assigned to the current PMO.

**Authentication**: Required (PMO/Reviewer role only)

**Path Parameters**:
- `eo_id`: UUID of the Executive Order

**Query Parameters**:
- `limit` (optional): Number of tasks to return (default: 50, max: 100)
- `offset` (optional): Number of tasks to skip (default: 0)

**Response Example**:
```json
{
  "success": true,
  "message": "Retrieved 5 tasks for EO Executive Order 2024-01",
  "data": {
    "executive_order": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Executive Order 2024-01",
      "description": "Implementation of new policies",
      "status": "in_progress",
      "message_id": "msg_123",
      "created_at": "2024-01-15T10:30:00Z"
    },
    "tasks": [
      {
        "id": "456e7890-e89b-12d3-a456-426614174001",
        "title": "Review Policy Documents",
        "description": "Review and approve policy documents",
        "status": "in_progress",
        "category": "review",
        "due_date": "2024-01-20T17:00:00Z",
        "remarks": "Need additional clarification",
        "assignee": {
          "id": "789e0123-e89b-12d3-a456-426614174002",
          "name": "John Doe",
          "email": "john.doe@example.com",
          "org_role": "Policy Analyst"
        }
      }
    ],
    "pagination": {
      "total": 5,
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  }
}
```

---

### **3. Get All EOs with Tasks (Combined)**
**Endpoint**: `GET /dashboard/pmo/assigned-eos-with-tasks`

**Description**: Fetches all Executive Orders assigned to the current PMO along with their tasks in a single response.

**Authentication**: Required (PMO/Reviewer role only)

**Query Parameters**:
- `limit` (optional): Number of EOs to return (default: 20, max: 50)
- `offset` (optional): Number of EOs to skip (default: 0)

**Response Example**:
```json
{
  "success": true,
  "message": "Retrieved 2 Executive Orders with tasks for PMO",
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
        "tasks": [
          {
            "id": "456e7890-e89b-12d3-a456-426614174001",
            "title": "Review Policy Documents",
            "description": "Review and approve policy documents",
            "status": "in_progress",
            "category": "review",
            "due_date": "2024-01-20T17:00:00Z",
            "remarks": "Need additional clarification",
            "assignee": {
              "id": "789e0123-e89b-12d3-a456-426614174002",
              "name": "John Doe",
              "email": "john.doe@example.com",
              "org_role": "Policy Analyst"
            }
          }
        ],
        "task_count": 1,
        "pmo_assignment": {
          "assigned_at": "2024-01-15T11:00:00Z",
          "is_primary": true,
          "assigned_by": "admin_user_id"
        }
      }
    ],
    "pagination": {
      "total": 2,
      "limit": 20,
      "offset": 0,
      "has_more": false
    }
  }
}
```

---

### **4. Get All Tasks for PMO's EOs (Updated)**
**Endpoint**: `GET /dashboard/pmo/tasks`

**Description**: Fetches all tasks for all Executive Orders assigned to the current PMO.

**Authentication**: Required (PMO/Reviewer role only)

**Query Parameters**:
- `limit` (optional): Number of tasks to return (default: 50, max: 100)
- `offset` (optional): Number of tasks to skip (default: 0)

**Response Example**:
```json
{
  "success": true,
  "message": "Retrieved 8 tasks for PMO",
  "data": {
    "tasks": [
      {
        "id": "456e7890-e89b-12d3-a456-426614174001",
        "title": "Review Policy Documents",
        "description": "Review and approve policy documents",
        "status": "in_progress",
        "category": "review",
        "due_date": "2024-01-20T17:00:00Z",
        "assignee": {
          "id": "789e0123-e89b-12d3-a456-426614174002",
          "name": "John Doe",
          "email": "john.doe@example.com"
        },
        "executive_order": {
          "id": "123e4567-e89b-12d3-a456-426614174000",
          "title": "Executive Order 2024-01"
        }
      }
    ],
    "pagination": {
      "total": 8,
      "limit": 50,
      "offset": 0
    }
  }
}
```

---

## 🔐 **Security & Access Control**

### **Role Requirements**
- All endpoints require **PMO/Reviewer role**
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

```json
{
  "detail": "Executive Order not found"
}
```

---

## 📊 **Use Cases**

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

---

## 🚀 **Performance Considerations**

### **Optimization Features**
1. **Eager Loading**: The combined endpoint uses eager loading to reduce database queries
2. **Pagination**: All endpoints support pagination to handle large datasets
3. **Proper Indexing**: Uses existing database indexes on `EOPMOAssignment` table

### **Recommended Usage**
- Use `/assigned-eos` for dashboard overviews
- Use `/assigned-eos/{eo_id}/tasks` for detailed EO views
- Use `/assigned-eos-with-tasks` sparingly (higher data transfer)
- Use `/tasks` for task management interfaces

---

## 🔧 **Integration Examples**

### **Frontend Integration**
```javascript
// Get all EOs assigned to current PMO
const response = await fetch('/dashboard/pmo/assigned-eos', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

// Get tasks for specific EO
const response = await fetch(`/dashboard/pmo/assigned-eos/${eoId}/tasks`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

// Get all EOs with tasks
const response = await fetch('/dashboard/pmo/assigned-eos-with-tasks', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### **cURL Examples**
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

---

## 📋 **Testing Checklist**

### **Functional Testing**
- [ ] PMO can access all assigned EOs
- [ ] PMO cannot access unassigned EOs
- [ ] PMO can see tasks for assigned EOs
- [ ] PMO cannot see tasks for unassigned EOs
- [ ] Pagination works correctly
- [ ] Error handling works for invalid requests

### **Performance Testing**
- [ ] Response times are acceptable (< 500ms)
- [ ] Large datasets handle pagination correctly
- [ ] Memory usage is reasonable
- [ ] Database queries are optimized

### **Security Testing**
- [ ] Non-PMO users cannot access endpoints
- [ ] PMO cannot access other PMOs' EOs
- [ ] Proper authentication required
- [ ] No SQL injection vulnerabilities

---

## 🎯 **Summary**

These new endpoints provide **complete PMO functionality** for:
- ✅ Viewing assigned Executive Orders
- ✅ Viewing tasks for specific EOs
- ✅ Getting comprehensive overviews
- ✅ Managing tasks across all assigned EOs

The endpoints are **secure**, **performant**, and **ready for production use**.
