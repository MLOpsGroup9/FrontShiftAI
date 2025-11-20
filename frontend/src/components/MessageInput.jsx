import React, { useState } from 'react';

const MessageInput = ({ onSendMessage, isLoading, messages = [] }) => {
  const [message, setMessage] = useState('');
  const hasMessages = messages.length > 0;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const containerClasses = hasMessages
    ? 'px-4 sm:px-8 pt-2 pb-6'
    : 'px-4 sm:px-8 pt-6 pb-6'; // Changed pb-10 to pb-6

  const formClasses = hasMessages
    ? 'w-full max-w-4xl mx-auto flex flex-col gap-4'
    : 'w-full max-w-4xl mx-auto flex flex-col gap-6';

  const composerClasses = hasMessages
    ? 'relative rounded-[22px] border border-white/10 bg-[rgba(8,10,20,0.85)] backdrop-blur-2xl p-4 sm:p-5'
    : 'relative rounded-[28px] border border-white/10 bg-[rgba(8,10,20,0.9)] backdrop-blur-2xl p-6 sm:p-7';

  const textAreaClasses = hasMessages
    ? 'w-full bg-transparent text-white/90 placeholder-white/40 text-base leading-relaxed min-h-[72px] resize-none border-none outline-none pr-48 disabled:opacity-50 disabled:cursor-not-allowed'
    : 'w-full bg-transparent text-white/90 placeholder-white/40 text-lg leading-relaxed min-h-[110px] resize-none border-none outline-none pr-48 disabled:opacity-50 disabled:cursor-not-allowed';

  const agentButtonClasses = hasMessages
    ? 'flex items-center gap-2 h-11 px-4 rounded-2xl border border-white/10 text-white/70 text-sm bg-transparent hover:bg-white/10 hover:text-white hover:border-white/20 transition-all active:scale-95'
    : 'flex items-center gap-2 h-11 px-5 rounded-2xl border border-white/10 text-white/80 text-sm bg-transparent hover:bg-white/10 hover:text-white hover:border-white/20 transition-all active:scale-95';

  return (
    <div className={`${containerClasses} transition-all duration-500`}>
      <form onSubmit={handleSubmit} className={`${formClasses} transition-all duration-500`}>
        <div className={`${composerClasses} transition-all duration-500`}>
          <textarea
            rows={3}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message AI Chat..."
            disabled={isLoading}
            className={`${textAreaClasses} transition-all duration-500`}
          />

          <div className="absolute bottom-4 right-4 flex items-center gap-2 flex-wrap justify-end">
            <button type="button" className={agentButtonClasses} title="Open agent tools">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
              <span>Agent</span>
            </button>
            <button
              type="button"
              className="w-11 h-11 flex items-center justify-center rounded-2xl border border-white/10 text-white/60 bg-white/5 hover:text-white hover:border-white/25 hover:bg-white/10 transition-all active:scale-95"
              title="Voice input"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 18a4 4 0 004-4V7a4 4 0 10-8 0v7a4 4 0 004 4zm0 0v3m-4 0h8" />
              </svg>
            </button>
            <button
              type="submit"
              disabled={!message.trim() || isLoading}
              className="w-11 h-11 flex items-center justify-center rounded-2xl bg-gradient-to-br from-white/90 to-white/60 text-black/70 shadow-[0_12px_25px_rgba(15,15,20,0.55)] disabled:opacity-40 disabled:cursor-not-allowed hover:shadow-[0_15px_30px_rgba(15,15,20,0.65)] transition-all active:scale-95"
              title="Send message"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12l14-7-7 14-2-5-5-2z" />
              </svg>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default MessageInput;