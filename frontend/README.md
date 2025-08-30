# DOL EO Management Frontend

A modern React-based frontend for the Department of Labor Executive Order Management System.

## 🚀 Features

### **Role-Based Dashboards**
- **Admin Dashboard**: Full system overview, user management, comprehensive statistics
- **Reviewer Dashboard**: EO review, task approval/rejection, oversight capabilities
- **Executor Dashboard**: Task management, status updates, progress tracking

### **Key Functionality**
- 🔐 **Authentication**: JWT-based login/logout with role-based access control
- 📊 **Real-time Data**: Live updates from backend API
- 📱 **Responsive Design**: Mobile-friendly Material-UI interface
- 🔄 **State Management**: Redux Toolkit for centralized state
- 📈 **Statistics**: Visual representation of system metrics
- 📋 **Task Management**: Create, update, and track task progress
- 📧 **Email Integration**: View email logs and communication history

## 🛠️ Technology Stack

- **React 18** - Modern React with hooks
- **Material-UI (MUI)** - Google's Material Design components
- **Redux Toolkit** - State management
- **React Router** - Client-side routing
- **Axios** - HTTP client for API calls
- **Date-fns** - Date manipulation utilities

## 📁 Project Structure

```
frontend/
├── public/                 # Static assets
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── auth/          # Authentication components
│   │   ├── common/        # Shared components
│   │   └── layout/        # Layout components
│   ├── pages/             # Page components
│   │   ├── AdminDashboard.js
│   │   ├── ReviewerDashboard.js
│   │   ├── ExecutorDashboard.js
│   │   └── LoginPage.js
│   ├── store/             # Redux store and slices
│   │   ├── slices/        # Redux slices
│   │   └── index.js       # Store configuration
│   ├── services/          # API services
│   ├── App.js             # Main app component
│   └── index.js           # Entry point
├── package.json            # Dependencies and scripts
└── README.md              # This file
```

## 🚀 Getting Started

### Prerequisites
- Node.js 16+ and npm
- Backend API running on `http://localhost:8000`

### Installation

1. **Clone the repository**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm start
   ```

4. **Open your browser**
   Navigate to `http://localhost:3000`

### Build for Production

```bash
npm run build
```

## 🔐 Authentication & Roles

### **User Roles**

#### **Admin Users**
- Access to all system features
- User management capabilities
- Full dashboard overview
- System statistics and reports

#### **Reviewer Users**
- EO review and approval
- Task oversight and approval
- Limited access to system data
- PMO approval workflows

#### **Executor Users**
- Task execution and updates
- Progress tracking
- Status updates and remarks
- Limited to assigned tasks

### **Login Credentials**
Use the credentials from your backend system:
- Email: `jack.smith@lumenlighthouse.ai`
- Password: `Lumen@2025`

## 📊 Dashboard Features

### **Admin Dashboard**
- System-wide statistics
- User management
- Executive order overview
- Task management
- Email log access
- Quick action buttons

### **Reviewer Dashboard**
- Pending task approvals
- EO review interface
- Approval/rejection actions
- Task oversight
- Email communication logs

### **Executor Dashboard**
- Personal task list
- Task status updates
- Progress tracking
- Due date management
- Quick status changes

## 🔧 Configuration

### **Environment Variables**
Create a `.env` file in the frontend root:

```env
REACT_APP_API_URL=http://localhost:8000
```

### **API Configuration**
The frontend automatically:
- Connects to backend API
- Handles authentication tokens
- Manages API requests/responses
- Provides error handling

## 📱 Responsive Design

The application is fully responsive and works on:
- Desktop computers
- Tablets
- Mobile phones
- All modern browsers

## 🎨 UI Components

### **Material-UI Components Used**
- Cards and Paper for content sections
- Data tables for information display
- Chips for status indicators
- Buttons and icons for actions
- Dialogs for forms and confirmations
- Grid system for responsive layouts

### **Custom Components**
- LoadingSpinner - Loading states
- ProtectedRoute - Authentication guards
- DashboardLayout - Main navigation layout

## 🔄 State Management

### **Redux Store Structure**
```javascript
{
  auth: {
    user: null,
    token: null,
    isAuthenticated: false,
    loading: false,
    error: null
  },
  dashboard: {
    executiveOrders: [],
    stats: null,
    emailLogs: [],
    loading: false
  },
  task: {
    tasks: [],
    selectedTask: null,
    loading: false
  }
}
```

### **Key Actions**
- `login/logout` - Authentication
- `fetchExecutiveOrders` - Get EO data
- `fetchUserTasks` - Get user tasks
- `updateTaskStatus` - Update task progress

## 📡 API Integration

### **Backend Endpoints Used**
- `POST /auth/login` - User authentication
- `GET /auth/me` - Get current user
- `GET /dashboard/stats` - Dashboard statistics
- `GET /dashboard/executive-orders` - EO list
- `GET /dashboard/tasks` - User tasks
- `PATCH /dashboard/tasks/{id}` - Update task

### **Error Handling**
- Automatic token refresh
- 401 redirects to login
- User-friendly error messages
- Loading states for better UX

## 🧪 Testing

### **Run Tests**
```bash
npm test
```

### **Test Coverage**
```bash
npm run test -- --coverage
```

## 🚀 Deployment

### **Build for Production**
```bash
npm run build
```

### **Deploy Options**
- **Netlify**: Drag and drop `build` folder
- **Vercel**: Connect GitHub repository
- **AWS S3**: Upload `build` folder
- **Docker**: Use provided Dockerfile

## 🔒 Security Features

- JWT token authentication
- Role-based access control
- Protected routes
- Secure API communication
- Token expiration handling

## 📈 Performance

- Lazy loading of components
- Optimized bundle size
- Efficient state management
- Responsive image handling
- Minimal re-renders

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is part of the DOL EO Management System.

## 🆘 Support

For technical support or questions:
- Check the backend API documentation
- Review the console for error messages
- Ensure backend is running on correct port
- Verify user credentials and permissions

## 🔮 Future Enhancements

- Real-time notifications
- Advanced filtering and search
- Export functionality
- Mobile app version
- Advanced reporting
- Integration with external systems
