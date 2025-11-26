import axios from 'axios';

// Read from .env or fallback to 8000 (matching your backend)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
console.log("🌐 Using Backend API:", API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 120 second timeout for long RAG queries
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

// -------------- PTO Agent APIs --------------

// Chat with PTO Agent
export const ptoChatAgent = async (message) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.post('/api/pto/chat', {
      message,
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("PTO Chat Error:", error.response?.data || error.message);
    throw error;
  }
};

// Get user's PTO balance
export const getPTOBalance = async () => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.get('/api/pto/balance', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Get PTO Balance Error:", error.response?.data || error.message);
    throw error;
  }
};

// Get user's PTO requests
export const getPTORequests = async () => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.get('/api/pto/requests', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Get PTO Requests Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Get all employee balances
export const getAllPTOBalances = async () => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.get('/api/pto/admin/balances', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Get All Balances Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Get all PTO requests
export const getAllPTORequests = async (statusFilter = null) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const url = statusFilter 
      ? `/api/pto/admin/requests?status_filter=${statusFilter}`
      : '/api/pto/admin/requests';
    
    const response = await api.get(url, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Get All Requests Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Approve or deny PTO request
export const approvePTORequest = async (requestId, status, adminNotes = null) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.post('/api/pto/admin/approve', {
      request_id: requestId,
      status: status, // "approved" or "denied"
      admin_notes: adminNotes
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Approve PTO Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Update employee PTO balance
export const updatePTOBalance = async (email, totalDays) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.put(`/api/pto/admin/balance/${email}?total_days=${totalDays}`, null, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Update Balance Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Reset employee PTO balance
export const resetPTOBalance = async (email) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.post(`/api/pto/admin/reset-balance/${email}`, null, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Reset Balance Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Reset all employee PTO balances
export const resetAllPTOBalances = async () => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.post('/api/pto/admin/reset-all-balances', null, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Reset All Balances Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Delete employee PTO balance
export const deletePTOBalance = async (email) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.delete(`/api/pto/admin/balance/${email}`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Delete Balance Error:", error.response?.data || error.message);
    throw error;
  }
};

// -------------- HR Ticket Agent APIs --------------

// Chat with HR Ticket Agent
export const hrTicketChatAgent = async (message) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.post('/api/hr-tickets/chat', {
      message,
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("HR Ticket Chat Error:", error.response?.data || error.message);
    throw error;
  }
};

// Get user's HR tickets
export const getMyHRTickets = async () => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.get('/api/hr-tickets/my-tickets', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Get My Tickets Error:", error.response?.data || error.message);
    throw error;
  }
};

// Cancel a ticket
export const cancelHRTicket = async (ticketId) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.delete(`/api/hr-tickets/${ticketId}`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Cancel Ticket Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Get ticket queue
export const getHRTicketQueue = async (filters = {}) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    
    const params = new URLSearchParams();
    if (filters.status) params.append('status_filter', filters.status);
    if (filters.category) params.append('category_filter', filters.category);
    if (filters.urgency) params.append('urgency_filter', filters.urgency);
    if (filters.sortBy) params.append('sort_by', filters.sortBy);
    
    const url = `/api/hr-tickets/admin/queue${params.toString() ? '?' + params.toString() : ''}`;
    
    const response = await api.get(url, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Get Queue Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Pick up ticket
export const pickUpHRTicket = async (ticketId) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.post('/api/hr-tickets/admin/pick-ticket', {
      ticket_id: ticketId
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Pick Ticket Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Schedule meeting
export const scheduleHRMeeting = async (ticketId, meetingData) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.post('/api/hr-tickets/admin/schedule-meeting', {
      ticket_id: ticketId,
      scheduled_datetime: meetingData.datetime,
      meeting_link: meetingData.link || null,
      meeting_location: meetingData.location || null,
      admin_notes: meetingData.notes || null
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Schedule Meeting Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Resolve ticket
export const resolveHRTicket = async (ticketId, status, resolutionNotes = null) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.post('/api/hr-tickets/admin/resolve', {
      ticket_id: ticketId,
      status: status, // "resolved" or "closed"
      resolution_notes: resolutionNotes
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Resolve Ticket Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Add note to ticket
export const addHRTicketNote = async (ticketId, note) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.post('/api/hr-tickets/admin/add-note', {
      ticket_id: ticketId,
      note: note
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Add Note Error:", error.response?.data || error.message);
    throw error;
  }
};

// Admin: Get ticket stats
export const getHRTicketStats = async () => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.get('/api/hr-tickets/admin/stats', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Get Stats Error:", error.response?.data || error.message);
    throw error;
  }
};

export default api;