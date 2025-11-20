import React, { useState, useEffect } from 'react';
import { healthCheck } from '../services/api';

const ConnectionStatus = () => {
  const [status, setStatus] = useState({ connected: false, checking: true });

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await healthCheck();
        setStatus({ 
          connected: response.status === 'ok', 
          checking: false,
          message: 'Backend connected'
        });
      } catch (error) {
        setStatus({ 
          connected: false, 
          checking: false,
          message: 'Backend not reachable. Please start the backend server.'
        });
      }
    };

    checkConnection();
    // Check connection every 30 seconds
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  if (status.checking) {
    return (
      <div className="fixed bottom-4 right-4 px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-xs text-white/70 backdrop-blur-xl z-50">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
          <span>Checking backend...</span>
        </div>
      </div>
    );
  }

  if (!status.connected) {
    return (
      <div className="fixed bottom-4 right-4 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-300 backdrop-blur-xl z-50 max-w-xs">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-red-400 rounded-full"></div>
          <div>
            <div className="font-semibold">Backend Offline</div>
            <div className="text-red-300/70 mt-1">{status.message}</div>
            <div className="text-red-300/50 mt-1">Run: uvicorn rag_api:app --reload --port 8001</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 px-4 py-2 bg-green-500/10 border border-green-500/30 rounded-lg text-xs text-green-300 backdrop-blur-xl z-50">
      <div className="flex items-center space-x-2">
        <div className="w-2 h-2 bg-green-400 rounded-full"></div>
        <span>{status.message}</span>
      </div>
    </div>
  );
};

export default ConnectionStatus;