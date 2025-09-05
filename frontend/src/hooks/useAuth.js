import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { getCurrentUser, logout } from '../store/slices/authSlice';

export const useAuth = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { isAuthenticated, loading, user, token } = useSelector((state) => state.auth);

  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    console.log('useAuth useEffect:', { storedToken, user, loading, isAuthenticated });
    
    // Only fetch user if we have a stored token but no user data and not currently loading
    if (storedToken && !user && !loading) {
      console.log('useAuth: Dispatching getCurrentUser');
      dispatch(getCurrentUser());
    }
  }, [dispatch, user, loading]); // Removed isAuthenticated from dependencies

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  return {
    isAuthenticated,
    loading,
    user,
    token,
    logout: handleLogout
  };
};
