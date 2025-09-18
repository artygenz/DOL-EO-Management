import axios from 'axios';

const api = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout for all requests
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => {
    // Log API responses for debugging
    console.log(`API Response [${response.config.url}]:`, response.data);
    return response;
  },
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url || '';
    const isTimeout = error.code === 'ECONNABORTED' || error.message.includes('timeout');
    
    console.error(`API Error [${url}]:`, error.response?.data || error.message);
    
    // Handle timeout errors with user-friendly messages
    if (isTimeout) {
      error.userMessage = 'Request timed out. The server is taking too long to respond. Please try again.';
    }
    
    // ⛔ Don't hard-redirect on 401 from the login (or me) endpoints.
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/me');
    
    if (status === 401) {
      if (!isAuthEndpoint) {
        localStorage.removeItem('token');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
