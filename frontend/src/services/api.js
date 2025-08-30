import axios from 'axios';

const api = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
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
    console.error(`API Error [${url}]:`, error.response?.data || error.message);
    
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
