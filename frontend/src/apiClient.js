import axios from 'axios';

// Base API instance — uses VITE_BACKEND_URL in production (set to EC2 public IP)
// Falls back to localhost:5000 for local development
const apiClient = axios.create({
  baseURL: `${import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000'}/api`,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Intercept requests to attach securely stored JWT tokens
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Intercept responses for global 401 unauthenticated redirect logic
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      console.warn("Unauthorized access: Redirecting to login or missing token.");
      localStorage.removeItem('token');
      // window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
