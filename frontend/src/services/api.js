import axios from 'axios';
import { toast } from 'sonner';

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

// Add response interceptor for debugging and global error handling
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.config.url}`, response.data);
    return response;
  },
  (error) => {
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const detail = error.response.data?.detail || "An unexpected error occurred.";

      console.error(`❌ API Error [${status}]:`, error.response.data);

      if (status === 401) {
        toast.error("Session expired. Please log in again.");
        // Optional: trigger logout logic if not handled by components
        localStorage.removeItem('access_token');
        // Let component handle redirect via state check if possible, or reload
        // window.location.reload(); // Can be aggressive, let's just toast for now.
      } else if (status === 403) {
        toast.error("You don't have permission to perform this action.");
      } else if (status === 422) {
        toast.error("Invalid input. Please check your data.");
      } else if (status >= 500) {
        toast.error("Server error. We're working on fixing it.");
      } else {
        toast.error(detail);
      }
    } else if (error.request) {
      // Request made but no response
      console.error('❌ No response from server.');
      toast.error("Unable to connect to the server. Please check your connection.");
    } else {
      // Something else happened
      console.error('❌ Request setup error:', error.message);
      toast.error("Error setting up request.");
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

export const bulkAddUsers = async (users) => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.post('/api/admin/bulk-add-users', {
      users: users
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Bulk Add Users Error:", error.response?.data || error.message);
    throw error;
  }
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

// Admin: Get monitoring dashboard stats
export const getMonitoringStats = async (timeRange = '7d') => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await api.get(`/api/admin/monitoring/stats?time_range=${timeRange}`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error("Get Monitoring Stats Error:", error.response?.data || error.message);
    throw error;
  }
};

// -------------- Voice Agent APIs --------------

// Create voice session with LiveKit
export const createVoiceSession = async (userEmail = null, company = null) => {
  try {
    // Use VITE_VOICE_API_URL for voice agent (Modal or local)
    const voiceApiUrl = import.meta.env.VITE_VOICE_API_URL || import.meta.env.VITE_MODAL_VOICE_AGENT_URL || 'http://localhost:8001';
    
    // Get user's JWT token for backend authentication passthrough
    const userToken = localStorage.getItem('access_token');
    if (!userToken) {
      throw new Error('Not authenticated - please login first');
    }
    
    console.log('🎙️ Creating voice session...');
    console.log('   Voice API URL:', voiceApiUrl);
    console.log('   User:', userEmail);
    console.log('   Company:', company);
    
    const response = await axios.post(`${voiceApiUrl}/session`, {
      user_email: userEmail,
      company: company,
      user_token: userToken  // Pass user's JWT for backend auth
    });
    
    console.log('✅ Voice session created:', response.data);
    return response.data;  // {session_id, room_name, token, livekit_url}
  } catch (error) {
    console.error("Create Voice Session Error:", error.response?.data || error.message);
    throw error;
  }
};

// End voice session (optional cleanup)
export const endVoiceSession = async (sessionId) => {
  try {
    console.log('🔚 Voice session ended:', sessionId);
    return { success: true };
  } catch (error) {
    console.error("End Voice Session Error:", error);
    return { success: false };
  }
};

// Voice agent health check
export const voiceAgentHealthCheck = async () => {
  try {
    const voiceApiUrl = import.meta.env.VITE_VOICE_API_URL || import.meta.env.VITE_MODAL_VOICE_AGENT_URL || 'http://localhost:8001';
    const response = await axios.get(`${voiceApiUrl}/health`, { timeout: 10000 });
    return response.data;
  } catch (error) {
    console.error("Voice Agent Health Check Error:", error.message);
    throw error;
  }
};

export default api;
