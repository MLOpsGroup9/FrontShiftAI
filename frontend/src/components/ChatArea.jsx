import React, { useEffect, useRef } from 'react';

const ChatArea = ({ messages, isLoading }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 18) return 'Good Afternoon';
    return 'Good Evening';
  };

  const pinnedMessage = messages.length > 0 ? messages[0] : null;
  const conversationMessages = pinnedMessage ? messages.slice(1) : [];

  const renderInlineText = (text) => {
    const segments = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
    return segments.map((segment, idx) => {
      if (segment.startsWith('**') && segment.endsWith('**')) {
        return (
          <strong key={idx} className="text-white">
            {segment.slice(2, -2)}
          </strong>
        );
      }
      return <span key={idx}>{segment}</span>;
    });
  };

  const renderMessageContent = (content) => {
    const lines = content.split('\n').map(line => line.trim()).filter(Boolean);
    const elements = [];
    let currentList = [];

    const flushList = () => {
      if (currentList.length === 0) return;
      elements.push(
        <ul key={`list-${elements.length}`} className="list-disc list-inside space-y-1 text-white/80">
          {currentList.map((item, idx) => (
            <li key={idx}>{renderInlineText(item)}</li>
          ))}
        </ul>
      );
      currentList = [];
    };

    lines.forEach((line) => {
      if (line.startsWith('- ')) {
        currentList.push(line.slice(2));
      } else {
        flushList();
        elements.push(
          <p key={`p-${elements.length}`} className="text-white/90">
            {renderInlineText(line)}
          </p>
        );
      }
    });

    flushList();
    return elements;
  };

  const renderMessageBubble = (message, key) => (
    <div
      key={key}
      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`glass-card max-w-2xl px-6 py-4 ${
          message.role === 'user'
            ? 'bg-white/15 border-white/20'
            : 'bg-white/10 border-white/10'
        }`}
      >
        <div className="space-y-2">
          {renderMessageContent(message.content)}
        </div>
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-white/10">
            <p className="text-xs text-white/50 mb-2">Sources:</p>
            <div className="space-y-1">
              {message.sources.map((source, idx) => (
                <p key={idx} className="text-xs text-white/40">
                  • {source.filename}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col h-full relative min-h-0">
      {/* Header - Always visible */}
      <div className="flex items-center justify-end px-6 py-4 border-b border-white/10 bg-black/10 backdrop-blur-xl sticky top-0 z-10">
        <div className="flex items-center space-x-2">
          <button className="px-4 py-2 bg-white/10 hover:bg-white/15 border border-white/10 rounded-lg text-white/80 hover:text-white transition-all text-sm">
            Chat
          </button>
          <button className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-white/60 hover:text-white/80 transition-all text-sm">
            Speech
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 p-8 relative min-h-0 overflow-hidden flex flex-col">
        {/* Floating Orb Background */}
        <div className="absolute top-1/4 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 orb-gradient rounded-full blur-3xl opacity-30 animate-float-orb pointer-events-none z-0"></div>

        {messages.length === 0 ? (
          /* Empty State */
          <div className="relative z-10 flex flex-col items-center pt-16 flex-1">
            {/* Central Orb */}
            <div className="mb-8 relative">
              <div className="w-32 h-32 rounded-full bg-gradient-to-br from-white/20 via-white/10 to-black/20 blur-2xl animate-pulse-glow absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"></div>
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-white/20 to-white/5 backdrop-blur-xl border border-white/10 shadow-[0_0_30px_rgba(255,255,255,0.1)] relative z-10 flex items-center justify-center">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-white/30 to-gray-500/20 blur-xl"></div>
              </div>
            </div>
            <h3 className="text-3xl font-light text-white/90 mb-2 text-center">
              {getGreeting()}. Can I help you with anything?
            </h3>
          </div>
        ) : (
          /* Messages Container with pinned first message */
          <div className="relative z-10 flex flex-col h-full">
            {pinnedMessage && (
              <div className="max-w-4xl mx-auto w-full flex-shrink-0">
                {renderMessageBubble(pinnedMessage, 'pinned')}
              </div>
            )}
            <div className={`${conversationMessages.length > 0 || isLoading ? 'flex-1 overflow-y-auto mt-6' : 'flex-1'}`}>
              <div className="max-w-4xl mx-auto space-y-6">
                {conversationMessages.map((message, index) => renderMessageBubble(message, index))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="glass-card px-6 py-4 bg-white/10">
                      <div className="flex space-x-2">
                        <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatArea;