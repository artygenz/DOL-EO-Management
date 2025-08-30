import React, { useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export default function RoleBasedRedirect() {
  const { user } = useAuth();

  useEffect(() => {
    console.log('RoleBasedRedirect: User role is', user?.role);
  }, [user]);

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Redirect based on user role
  switch (user.role) {
    case 'admin':
      return <Navigate to="/dashboard/admin" replace />;
    case 'reviewer':
      return <Navigate to="/dashboard/reviewer" replace />;
    case 'executor':
      return <Navigate to="/dashboard/executor" replace />;
    default:
      // Fallback to admin for unknown roles
      return <Navigate to="/dashboard/admin" replace />;
  }
}
