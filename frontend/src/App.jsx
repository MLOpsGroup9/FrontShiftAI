import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Sidebar from './components/Sidebar';
import UserChatPage from './components/UserChatPage';
import ConnectionStatus from './components/ConnectionStatus';
import Login from './components/Login';
import SuperAdminDashboard from './components/SuperAdminDashboard';
import CompanyAdminDashboard from './components/CompanyAdminDashboard';
import { logout, getUserInfo } from './services/api';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  
  const [activeView, setActiveView] = useState('home');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('sidebarWidth');
    return saved ? parseInt(saved, 10) : 320;
  });
  const [isResizing, setIsResizing] = useState(false);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [chatHistory, setChatHistory] = useState(() => {
    const saved = localStorage.getItem('chatHistory');
    return saved ? JSON.parse(saved) : [];
  });

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      const email = localStorage.getItem('user_email');
      
      if (token && email) {
        try {
          const userData = await getUserInfo();
          setUserInfo(userData);
          setIsAuthenticated(true);
        } catch (error) {
          console.error('Token validation failed:', error);
          logout();
          setIsAuthenticated(false);
        }
      } else {
        setIsAuthenticated(false);
      }
      
      setIsCheckingAuth(false);
    };

    checkAuth();
  }, []);

  useEffect(() => {
    localStorage.setItem('sidebarWidth', sidebarWidth.toString());
  }, [sidebarWidth]);

  useEffect(() => {
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
  }, [chatHistory]);

  const handleLoginSuccess = (loginData) => {
    setUserInfo({
      email: loginData.email,
      company: loginData.company,
      role: loginData.role
    });
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    logout();
    setIsAuthenticated(false);
    setUserInfo(null);
    setMessages([]);
    setChatHistory([]);
    setCurrentChatId(null);
  };

  const handleNewChat = () => {
    setCurrentChatId(null);
    setMessages([]);
  };

  const handleLoadChat = (chatId) => {
    const chat = chatHistory.find(c => c.id === chatId);
    if (chat) {
      setCurrentChatId(chat.id);
      setMessages(chat.messages);
    }
  };

  const handleDeleteChat = (chatId) => {
    setChatHistory(prev => prev.filter(chat => chat.id !== chatId));
    if (currentChatId === chatId) {
      setCurrentChatId(null);
      setMessages([]);
    }
  };

  const getTimeLabel = (timestamp) => {
    const now = new Date();
    const chatDate = new Date(timestamp);
    const diffTime = Math.abs(now - chatDate);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays} days ago`;
    if (diffDays <= 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return `${Math.floor(diffDays / 30)} months ago`;
  };

  const groupedChats = chatHistory.reduce((groups, chat) => {
    const timeLabel = getTimeLabel(chat.timestamp);
    if (!groups[timeLabel]) {
      groups[timeLabel] = [];
    }
    groups[timeLabel].push(chat);
    return groups;
  }, {});

  const formattedChatHistory = Object.entries(groupedChats).map(([time, chats]) => ({
    time,
    chats: chats
      .sort((a, b) => (b.lastUpdated || b.timestamp) - (a.lastUpdated || a.timestamp))
      .map(chat => {
        const firstUserMessage = chat.messages.find(m => m.role === 'user');
        const title = firstUserMessage?.content 
          ? (firstUserMessage.content.length > 50 
            ? firstUserMessage.content.substring(0, 50) + '...' 
            : firstUserMessage.content)
          : 'New Chat';
        return {
          id: chat.id,
          title,
          timestamp: chat.timestamp
        };
      })
  })).sort((a, b) => {
    const aTime = a.chats[0]?.timestamp || 0;
    const bTime = b.chats[0]?.timestamp || 0;
    return bTime - aTime;
  });

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      e.preventDefault();
      const newWidth = Math.min(Math.max(240, e.clientX), 600);
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      document.body.style.pointerEvents = 'auto';
    } else {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      if (!isResizing) {
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };
  }, [isResizing]);

  const handleSendMessage = async (message) => {
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: Date.now(),
    };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setIsLoading(true);

    try {
      console.log('📤 Sending message to smart router:', message);
      
      const token = localStorage.getItem('access_token');
      const response = await axios.post(
        `${API_BASE_URL}/api/chat/message`,
        { message },
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      console.log('📥 Received response from', response.data.agent_used, 'agent');
      
      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        agentType: response.data.agent_used,
        ...(response.data.agent_used === 'pto' && response.data.balance_info && {
          ptoInfo: {
            requestCreated: response.data.request_created,
            requestId: response.data.request_id,
            balanceInfo: response.data.balance_info
          }
        }),
        ...(response.data.agent_used === 'hr_ticket' && response.data.ticket_id && {
          hrTicketInfo: {
            ticketCreated: response.data.ticket_created,
            ticketId: response.data.ticket_id,
            queuePosition: response.data.queue_position
          }
        }),
        timestamp: Date.now(),
      };
      const finalMessages = [...updatedMessages, assistantMessage];
      setMessages(finalMessages);

      setChatHistory(prev => {
        const chatId = currentChatId || Date.now().toString();
        const existingChat = prev.find(c => c.id === currentChatId);
        const chatData = {
          id: chatId,
          messages: finalMessages,
          agentType: response.data.agent_used,
          timestamp: existingChat?.timestamp || Date.now(),
          lastUpdated: Date.now(),
        };

        if (currentChatId && existingChat) {
          return prev.map(chat => 
            chat.id === currentChatId ? chatData : chat
          );
        } else {
          setCurrentChatId(chatId);
          return [chatData, ...prev];
        }
      });
    } catch (error) {
      console.error('❌ Error sending message:', error);
      
      let errorMsg = 'Sorry, I encountered an error.';
      if (error.response?.status === 401 || error.message === 'Not authenticated') {
        errorMsg = '🔒 Session expired. Please log in again.';
        setTimeout(() => handleLogout(), 2000);
      } else if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
        errorMsg = '🔌 Cannot connect to backend. Please ensure the backend server is running on port 8000.';
      } else if (error.response?.data?.detail) {
        errorMsg = `Backend error: ${error.response.data.detail}`;
      }
      
      const errorMessage = {
        role: 'assistant',
        content: errorMsg,
        timestamp: Date.now(),
      };
      const finalMessages = [...updatedMessages, errorMessage];
      setMessages(finalMessages);

      setChatHistory(prev => {
        const chatId = currentChatId || Date.now().toString();
        const existingChat = prev.find(c => c.id === currentChatId);
        const chatData = {
          id: chatId,
          messages: finalMessages,
          timestamp: existingChat?.timestamp || Date.now(),
          lastUpdated: Date.now(),
        };

        if (currentChatId && existingChat) {
          return prev.map(chat => 
            chat.id === currentChatId ? chatData : chat
          );
        } else {
          setCurrentChatId(chatId);
          return [chatData, ...prev];
        }
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0a0a0f] via-[#1a1a24] to-[#0a0a0f] flex items-center justify-center">
        <div className="text-white/60">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  if (userInfo?.role === 'super_admin') {
    return <SuperAdminDashboard onLogout={handleLogout} userInfo={userInfo} />;
  }

  if (userInfo?.role === 'company_admin') {
    return <CompanyAdminDashboard onLogout={handleLogout} userInfo={userInfo} />;
  }

  // Regular user - show chat interface
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0f] via-[#1a1a24] to-[#0a0a0f] relative overflow-hidden">
      <div className="fixed top-1/4 right-1/4 w-96 h-96 bg-gradient-to-r from-white/10 to-gray-500/10 rounded-full blur-3xl opacity-20 animate-float-orb pointer-events-none z-0"></div>

      <div className="relative z-10 flex min-h-screen">
        <Sidebar 
          activeView={activeView} 
          setActiveView={setActiveView}
          width={sidebarWidth}
          chatHistory={formattedChatHistory}
          onNewChat={handleNewChat}
          onLoadChat={handleLoadChat}
          onDeleteChat={handleDeleteChat}
          currentChatId={currentChatId}
          userInfo={userInfo}
          onLogout={handleLogout}
        />
        
        <div
          className={`fixed top-0 h-screen w-3 cursor-col-resize z-20 transition-all ${
            isResizing ? 'bg-white/10' : ''
          }`}
          style={{ left: `${sidebarWidth - 1}px` }}
          onMouseDown={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsResizing(true);
          }}
        >
          <div className={`absolute inset-y-0 left-1/2 transform -translate-x-1/2 w-0.5 transition-colors ${
            isResizing ? 'bg-white/40' : 'bg-white/10 hover:bg-white/30'
          }`}></div>
        </div>
        
        {isResizing && (
          <div className="fixed inset-0 bg-black/0 z-[15] cursor-col-resize" />
        )}
        
        <div 
          className="flex-1 flex flex-col min-h-screen"
          style={{ marginLeft: `${sidebarWidth}px` }}
        >
          <UserChatPage
            messages={messages}
            isLoading={isLoading}
            onSendMessage={handleSendMessage}
            userInfo={userInfo}
          />
        </div>
      </div>

      <ConnectionStatus />
    </div>
  );
}

export default App;