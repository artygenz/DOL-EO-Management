# DOL EO Management Chatbot System Documentation

## Overview

The DOL EO Management Chatbot is an intelligent conversational interface that provides role-based access to Executive Order data, task management, and operational insights. The system combines natural language processing with structured data access to deliver real-time, context-aware responses to users across different organizational roles.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                CHATBOT SYSTEM ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │   Frontend UI   │    │   Test UI       │    │   Postman/API   │            │
│  │   (Dashboard)   │    │   (HTML/JS)     │    │   Clients       │            │
│  └─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘            │
│            │                      │                      │                    │
│            └──────────────────────┼──────────────────────┘                    │
│                                   │                                           │
│  ┌─────────────────────────────────▼─────────────────────────────────┐        │
│  │                    FASTAPI ROUTES LAYER                          │        │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │        │
│  │  │ /chat/query │  │/chat/stream │  │ /auth/login │              │        │
│  │  │ (Normal)    │  │ (Streaming) │  │ (JWT Auth)  │              │        │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │        │
│  └─────────────────────────────────┬─────────────────────────────────┘        │
│                                    │                                           │
│  ┌─────────────────────────────────▼─────────────────────────────────┐        │
│  │                    AUTHENTICATION LAYER                          │        │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │        │
│  │  │ JWT Token   │  │ Role-Based  │  │ User        │              │        │
│  │  │ Validation  │  │ Access      │  │ Context     │              │        │
│  │  │ & Blacklist │  │ Control     │  │ Injection   │              │        │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │        │
│  └─────────────────────────────────┬─────────────────────────────────┘        │
│                                    │                                           │
│  ┌─────────────────────────────────▼─────────────────────────────────┐        │
│  │                    CHAT BRAIN LAYER                              │        │
│  │                                                                 │        │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │        │
│  │  │ Pre-Router  │  │ Tool        │  │ Query       │              │        │
│  │  │ (Classify)  │  │ Selector    │  │ Runner      │              │        │
│  │  │             │  │ (RBAC)      │  │ (Execute)   │              │        │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │        │
│  │         │                │                │                    │        │
│  │         ▼                ▼                ▼                    │        │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │        │
│  │  │ Entity      │  │ Available   │  │ Tool        │              │        │
│  │  │ Detection   │  │ Tools       │  │ Execution   │              │        │
│  │  │ Intent      │  │ Filtering   │  │ & Response  │              │        │
│  │  │ Extraction  │  │ by Role     │  │ Generation  │              │        │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │        │
│  └─────────────────────────────────┬─────────────────────────────────┘        │
│                                    │                                           │
│  ┌─────────────────────────────────▼─────────────────────────────────┐        │
│  │                    NATURAL LANGUAGE GENERATION                   │        │
│  │                                                                 │        │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │        │
│  │  │ Response    │  │ Streaming   │  │ Context     │              │        │
│  │  │ Formatter   │  │ Generator   │  │ Builder     │              │        │
│  │  │ (Structured)│  │ (Real-time) │  │ (Role-aware)│              │        │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │        │
│  └─────────────────────────────────┬─────────────────────────────────┘        │
│                                    │                                           │
│  ┌─────────────────────────────────▼─────────────────────────────────┐        │
│  │                    TOOL LAYER                                   │        │
│  │                                                                 │        │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │        │
│  │  │ Task Tools  │  │ EO Tools    │  │ Update      │              │        │
│  │  │ (Search,    │  │ (Search,    │  │ Tools       │              │        │
│  │  │ Aggregate,  │  │ List)       │  │ (Search,    │              │        │
│  │  │ Get My)     │  │             │  │ Filter)     │              │        │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │        │
│  └─────────────────────────────────┬─────────────────────────────────┘        │
│                                    │                                           │
│  ┌─────────────────────────────────▼─────────────────────────────────┐        │
│  │                    DATA LAYER                                   │        │
│  │                                                                 │        │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │        │
│  │  │ PostgreSQL  │  │ Redis       │  │ File        │              │        │
│  │  │ Database    │  │ Cache       │  │ Storage     │              │        │
│  │  │ (Tasks,     │  │ (Sessions)  │  │ (Logs)      │              │        │
│  │  │ EOs, Users) │  │             │  │             │              │        │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │        │
│  └─────────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## How the Chatbot Works

### 1. Request Processing Flow

**Step 1: Authentication & Authorization**
- User sends request with JWT Bearer token
- System validates token and extracts user context (role, ID, permissions)
- Role-based access control determines available data scope

**Step 2: Intent Classification**
- Pre-router analyzes user message using LLM
- Extracts entity type (tasks, executive_orders, task_updates, users)
- Identifies user intents (search, aggregate, get_my, etc.)
- Extracts hints and parameters from natural language

**Step 3: Tool Selection**
- Tool selector filters available tools based on user role
- Maps intents to appropriate tool functions
- Ensures RBAC compliance at tool level

**Step 4: Query Execution**
- Query runner executes selected tool with extracted parameters
- Tools perform database queries with role-based filtering
- Results are returned with metadata and processing information

**Step 5: Response Generation**
- Natural Language Generator creates human-readable responses
- Two modes available:
  - **Normal**: Complete response returned at once
  - **Streaming**: Real-time token-by-token delivery

### 2. Role-Based Access Control (RBAC)

**Admin Role:**
- Full access to all data across the organization
- Can view all tasks, executive orders, and updates
- Access to aggregate statistics and cross-role data

**Reviewer Role:**
- Limited to Executive Orders assigned to them
- Can view tasks under their assigned EOs
- Access to task updates within their scope

**Executor Role:**
- Restricted to their own assigned tasks
- Can view updates from their tasks only
- No access to other users' data

### 3. Streaming vs Normal Responses

**Normal Mode (`/chat/query`):**
- Complete response returned as JSON
- Includes metadata: tool used, arguments, data, processing steps
- Suitable for dashboard integration
- Faster for simple queries

**Streaming Mode (`/chat/stream`):**
- Server-Sent Events (SSE) format
- Real-time token-by-token delivery
- Metadata sent first, then content chunks
- Better user experience for longer responses
- Includes artificial delay (50ms) for visibility

### 4. Available Tools & Capabilities

**Task Management:**
- `search_tasks`: Search tasks with filters
- `get_my_tasks`: Get user's assigned tasks
- `aggregate_tasks`: Group tasks by category/status
- `get_nearest_due_task`: Find upcoming deadlines

**Executive Orders:**
- `search_eos`: Search executive orders
- `list_eos`: List available EOs (role-filtered)

**Task Updates:**
- `search_task_updates`: Search updates with filters
- `get_updates_with_blockers`: Find updates with issues

**User Management:**
- `search_users`: Find users by name/email
- `get_user_tasks`: Get tasks for specific user

### 5. Natural Language Processing

**Intent Recognition:**
- "Show tasks by category" → `aggregate_tasks` with `group_by: category`
- "List updates with blockers" → `search_task_updates` with `has_blockers: true`
- "Show my tasks" → `get_my_tasks`

**Entity Extraction:**
- Automatic detection of user names, task IDs, EO references
- Parameter extraction from natural language
- Context-aware filtering based on user role

**Response Generation:**
- Role-appropriate language and detail level
- Structured data presentation
- Actionable insights and recommendations
- Error handling with helpful suggestions

## API Endpoints

### Authentication
- `POST /auth/login` - User authentication
- `GET /auth/me` - Get current user info
- `POST /auth/logout` - Token revocation

### Chat Endpoints
- `POST /chat/query` - Non-streaming chat
- `POST /chat/stream` - Streaming chat
- `GET /chat/health` - Health check

### Request Format
```json
{
  "message": "Show tasks by category",
  "context": {
    "additional_params": "optional"
  }
}
```

### Response Format (Normal)
```json
{
  "response": "Here is a breakdown of tasks by category...",
  "tool": "aggregate_tasks",
  "args": {"group_by": "category"},
  "data": {"Director of Compliance": 3, "Director of Accounting": 3},
  "processing": ["Signed in as admin.", "Understanding your question..."]
}
```

### Response Format (Streaming)
```
data: {"type": "metadata", "tool": "aggregate_tasks", "args": {...}}
data: {"type": "chunk", "content": "Here"}
data: {"type": "chunk", "content": " is"}
data: {"type": "complete", "message": "Stream completed"}
```

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **Token Blacklisting**: Revoked tokens are invalidated
- **Role-Based Access**: Data access controlled by user roles
- **Input Validation**: All inputs validated and sanitized
- **CORS Protection**: Cross-origin requests properly handled
- **SQL Injection Prevention**: Parameterized queries used throughout

## Testing & Development

**Test UI**: HTML interface at `scripts/chat_test_ui.html`
- Real-time streaming demonstration
- Mode switching (streaming vs normal)
- Authentication testing
- Role-based access testing

**API Testing**: Postman collection available
- Pre-configured requests
- Authentication flow
- Both streaming and normal endpoints

**RBAC Testing**: Automated test suite
- Role-based access validation
- Permission boundary testing
- Data visibility verification

## Performance & Scalability

- **Streaming Responses**: Real-time delivery for better UX
- **Caching**: Redis for session management
- **Database Optimization**: Indexed queries for fast responses
- **Async Processing**: Non-blocking I/O operations
- **Load Balancing**: Ready for horizontal scaling

## Future Enhancements

- **Conversation Memory**: Multi-turn conversation support
- **Advanced Analytics**: Trend analysis and insights
- **Integration APIs**: Third-party system connections
- **Mobile App**: Native mobile interface
- **Voice Interface**: Speech-to-text integration
