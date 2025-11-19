import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import MessageInput from './components/MessageInput';
import { ragQuery } from './services/api';

function App() {
  const [activeView, setActiveView] = useState('home');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    // Load from localStorage or default to 320px (w-80)
    const saved = localStorage.getItem('sidebarWidth');
    return saved ? parseInt(saved, 10) : 320;
  });
  const [isResizing, setIsResizing] = useState(false);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [chatHistory, setChatHistory] = useState(() => {
    // Load chat history from localStorage
    const saved = localStorage.getItem('chatHistory');
    return saved ? JSON.parse(saved) : [];
  });
  // Save sidebar width to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('sidebarWidth', sidebarWidth.toString());
  }, [sidebarWidth]);

  // Save chat history to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
  }, [chatHistory]);

  // Create new chat
  const handleNewChat = () => {
    setCurrentChatId(null);
    setMessages([]);
  };

  // Load a chat from history
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

  // Get formatted time for chat grouping
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

  // Group chats by time
  const groupedChats = chatHistory.reduce((groups, chat) => {
    const timeLabel = getTimeLabel(chat.timestamp);
    if (!groups[timeLabel]) {
      groups[timeLabel] = [];
    }
    groups[timeLabel].push(chat);
    return groups;
  }, {});

  // Format chat history for sidebar
  const formattedChatHistory = Object.entries(groupedChats).map(([time, chats]) => ({
    time,
    chats: chats
      .sort((a, b) => (b.lastUpdated || b.timestamp) - (a.lastUpdated || a.timestamp)) // Sort by most recent first within group
      .map(chat => {
        // Get first user message for title
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
    // Sort groups by most recent first
    const aTime = a.chats[0]?.timestamp || 0;
    const bTime = b.chats[0]?.timestamp || 0;
    return bTime - aTime;
  });


  // Handle mouse move for resizing
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      e.preventDefault();
      const newWidth = Math.min(Math.max(240, e.clientX), 600); // Min 240px, Max 600px
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
    // Add user message to chat
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: Date.now(),
    };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setIsLoading(true);

    try {
      // Call RAG API
      const response = await ragQuery(message, null, 4);
      
      // Add assistant response to chat
      const assistantMessage = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources || [],
        timestamp: Date.now(),
      };
      const finalMessages = [...updatedMessages, assistantMessage];
      setMessages(finalMessages);

      // Update or create chat in history
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
          // Update existing chat
          return prev.map(chat => 
            chat.id === currentChatId ? chatData : chat
          );
        } else {
          // Create new chat
          setCurrentChatId(chatId);
          return [chatData, ...prev];
        }
      });
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant',
        content: error.response?.data?.detail || 'Sorry, I encountered an error. Please check if the backend API is running.',
        sources: [],
        timestamp: Date.now(),
      };
      const finalMessages = [...updatedMessages, errorMessage];
      setMessages(finalMessages);

      // Save error message to history as well
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0f] via-[#1a1a24] to-[#0a0a0f] relative overflow-hidden">

      {/* Floating Orb */}
      <div className="fixed top-1/4 right-1/4 w-96 h-96 bg-gradient-to-r from-white/10 to-gray-500/10 rounded-full blur-3xl opacity-20 animate-float-orb pointer-events-none z-0"></div>

      {/* Main Layout */}
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
        />
        {/* Resize Handle */}
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
        {/* Resizing Overlay */}
        {isResizing && (
          <div className="fixed inset-0 bg-black/0 z-[15] cursor-col-resize" />
        )}
        <div 
          className="flex-1 flex flex-col min-h-screen"
          style={{ marginLeft: `${sidebarWidth}px` }}
        >
          <ChatArea
            messages={messages}
            isLoading={isLoading}
          />
          <MessageInput onSendMessage={handleSendMessage} isLoading={isLoading} messages={messages} />
        </div>
      </div>
    </div>
  );
}

export default App;
