import React from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { ThemeModeProvider } from './ui/ThemeModeProvider';
import AppShell from './components/AppShell';
import LoginPage from './pages/LoginPage';
import AdminDashboard from './pages/AdminDashboard';
import PMODashboard from './pages/PMODashboard';
import ResourceDashboard from './pages/ResourceDashboard';
import EOsPage from './pages/EOsPage';
import TasksPage from './pages/TasksPage';
import ProtectedRoute from './components/auth/ProtectedRoute';
import RoleBasedRedirect from './components/auth/RoleBasedRedirect';
import { useAuth } from './hooks/useAuth';

function App() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <ThemeModeProvider>
      <Routes>
        <Route 
          path="/login" 
          element={
            isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />
          } 
        />
        
        <Route 
          path="/" 
          element={
            isAuthenticated ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />
          } 
        />

        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              <AppShell>
                <Outlet />
              </AppShell>
            </ProtectedRoute>
          }
        >
          <Route index element={<RoleBasedRedirect />} />
          <Route path="admin" element={<AdminDashboard />} />
          <Route path="reviewer" element={<PMODashboard />} />
          <Route path="executor" element={<ResourceDashboard />} />
        </Route>

        {/* Standalone pages for EOs and Tasks */}
        <Route 
          path="/eos" 
          element={
            <ProtectedRoute>
              <AppShell>
                <EOsPage />
              </AppShell>
            </ProtectedRoute>
          } 
        />
        
        <Route 
          path="/eos/:id" 
          element={
            <ProtectedRoute>
              <AppShell>
                <EOsPage />
              </AppShell>
            </ProtectedRoute>
          } 
        />
        
        <Route 
          path="/tasks" 
          element={
            <ProtectedRoute>
              <AppShell>
                <TasksPage />
              </AppShell>
            </ProtectedRoute>
          } 
        />
        
        <Route 
          path="/tasks/:id" 
          element={
            <ProtectedRoute>
              <AppShell>
                <TasksPage />
              </AppShell>
            </ProtectedRoute>
          } 
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ThemeModeProvider>
  );
}

export default App; 