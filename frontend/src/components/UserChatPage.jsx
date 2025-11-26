import React, { useState } from 'react';
import ChatArea from './ChatArea';
import PTORequestsTab from './PTORequestsTab';
import HRTicketsTab from './HRTicketsTab';
import MessageInput from './MessageInput';

const UserChatPage = ({ 
  messages, 
  isLoading, 
  onSendMessage,
  userInfo 
}) => {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div className="flex-1 flex flex-col h-full relative min-h-0">
      {/* Tab Navigation */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-black/10 backdrop-blur-xl sticky top-0 z-10">
        {/* Left side - Navigation tabs */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-4 py-2 rounded-lg text-sm transition-all ${
              activeTab === 'chat'
                ? 'bg-white/10 border border-white/10 text-white'
                : 'bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 hover:text-white/80'
            }`}
          >
            Chat
          </button>
          <button
            onClick={() => setActiveTab('pto')}
            className={`px-4 py-2 rounded-lg text-sm transition-all ${
              activeTab === 'pto'
                ? 'bg-white/10 border border-white/10 text-white'
                : 'bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 hover:text-white/80'
            }`}
          >
            PTO Requests
          </button>
          <button
            onClick={() => setActiveTab('hr')}
            className={`px-4 py-2 rounded-lg text-sm transition-all ${
              activeTab === 'hr'
                ? 'bg-white/10 border border-white/10 text-white'
                : 'bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 hover:text-white/80'
            }`}
          >
            HR Tickets
          </button>
        </div>
        
        {/* Right side - Chat/Speech mode buttons */}
        <div className="flex items-center space-x-2">
          <button className="px-4 py-2 bg-white/10 hover:bg-white/15 border border-white/10 rounded-lg text-white/80 hover:text-white transition-all text-sm">
            Chat
          </button>
          <button className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-white/60 hover:text-white/80 transition-all text-sm">
            Speech
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 flex flex-col min-h-0">
        {activeTab === 'chat' && (
          <>
            <ChatArea messages={messages} isLoading={isLoading} />
            <MessageInput 
              onSendMessage={onSendMessage} 
              isLoading={isLoading} 
              messages={messages}
              placeholder="Ask about PTO, HR policies, benefits, or schedule a meeting..."
            />
          </>
        )}
        
        {activeTab === 'pto' && <PTORequestsTab userInfo={userInfo} />}
        
        {activeTab === 'hr' && <HRTicketsTab userInfo={userInfo} />}
      </div>
    </div>
  );
};

export default UserChatPage;