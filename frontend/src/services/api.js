import axios from 'axios';

// Read from .env or fallback to 8001 (matching your backend)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

console.log("🌐 Using Backend API:", API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout for long RAG queries
});

// Add request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log(`🚀 API Request: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('❌ Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for debugging
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.config.url}`, response.data);
    return response;
  },
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error(`❌ API Error [${error.response.status}]:`, error.response.data);
    } else if (error.request) {
      // Request made but no response
      console.error('❌ No response from server. Is the backend running?');
    } else {
      // Something else happened
      console.error('❌ Request setup error:', error.message);
    }
    return Promise.reject(error);
  }
);

// -------------- RAG Query (with Auth) --------------
export const ragQuery = async (query, companyName = null, topK = 4) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }

    const response = await api.post('/api/rag/query', {
      query,
      top_k: topK,
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("RAG Query Error:", error.response?.data || error.message);
    throw error;
  }
};

// -------------- Health Check --------------
export const healthCheck = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    console.error("Health check error:", error.message);
    throw error;
  }
};

// -------------- Authentication --------------
export const login = async (email, password) => {
  try {
    const response = await api.post('/api/auth/login', {
      email,
      password,
    });
    return response.data;
  } catch (error) {
    console.error("Login error:", error.response?.data || error.message);
    throw error;
  }
};

export const getUserInfo = async () => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('No token found');
    }
    
    const response = await api.get('/api/auth/me', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Get user info error:", error);
    throw error;
  }
};

export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_email');
  localStorage.removeItem('user_company');
};

export default api;