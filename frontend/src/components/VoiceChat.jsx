import React, { useState, useEffect, useRef } from 'react';
import { Room, RoomEvent } from 'livekit-client';
import { createVoiceSession, endVoiceSession } from '../services/api';

const VoiceChat = ({ isOpen, onClose }) => {
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [transcript, setTranscript] = useState([]);

  const roomRef = useRef(null);
  const audioElementRef = useRef(null);

  const connectToVoice = async () => {
    try {
      setIsConnecting(true);
      setError(null);

      console.log('🎙️ Creating voice session...');

      // Create voice session via backend API
      const session = await createVoiceSession();

      console.log('✅ Voice session created:', session);
      setSessionId(session.session_id);

      // Create LiveKit room
      const room = new Room();
      roomRef.current = room;

      // Set up event listeners
      room.on(RoomEvent.Connected, () => {
        console.log('✅ Connected to voice agent');
        setIsConnected(true);
        setIsConnecting(false);
      });

      room.on(RoomEvent.Disconnected, () => {
        console.log('👋 Disconnected from voice agent');
        setIsConnected(false);
        cleanup();
      });

      room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        console.log('🎵 Track subscribed:', track.kind, 'from', participant.identity);

        if (track.kind === 'audio') {
          // Attach agent's audio track to audio element
          const element = track.attach();
          element.autoplay = true;
          audioElementRef.current = element;

          // Add to DOM
          document.body.appendChild(element);

          console.log('🔊 Agent audio track attached');
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach();
      });

      room.on(RoomEvent.DataReceived, (payload, participant) => {
        // Handle any data messages from the agent
        const message = new TextDecoder().decode(payload);
        console.log('📩 Data received:', message);

        try {
          const data = JSON.parse(message);
          if (data.type === 'transcript') {
            setTranscript(prev => [...prev, data]);
          }
        } catch (e) {
          // Not JSON, ignore
        }
      });

      // Connect to LiveKit room
      console.log('🔌 Connecting to LiveKit room:', session.room_name);
      await room.connect(session.livekit_url, session.token, {
        audio: true,
        video: false,
        publishDefaults: {
          audioBitrate: 48000,
        },
      });

      console.log('✅ LiveKit room connected');

    } catch (err) {
      console.error('❌ Voice connection error:', err);
      setError(err.message || 'Failed to connect to voice agent');
      setIsConnecting(false);
      cleanup();
    }
  };

  const disconnectFromVoice = async () => {
    try {
      if (roomRef.current) {
        roomRef.current.disconnect();
        roomRef.current = null;
      }

      if (sessionId) {
        await endVoiceSession(sessionId);
        setSessionId(null);
      }

      cleanup();
      onClose();
    } catch (err) {
      console.error('❌ Disconnect error:', err);
      cleanup();
      onClose();
    }
  };

  const cleanup = () => {
    setIsConnected(false);
    setIsConnecting(false);
    setIsSpeaking(false);

    // Clean up audio element
    if (audioElementRef.current && audioElementRef.current.parentNode) {
      audioElementRef.current.parentNode.removeChild(audioElementRef.current);
      audioElementRef.current = null;
    }
  };

  // Auto-connect when modal opens
  useEffect(() => {
    if (isOpen && !isConnected && !isConnecting) {
      connectToVoice();
    }
  }, [isOpen]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (roomRef.current) {
        roomRef.current.disconnect();
      }
      cleanup();
    };
  }, []);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-gradient-to-br from-gray-900 to-black border border-white/10 rounded-3xl p-8 max-w-md w-full mx-4 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-semibold text-white">Voice Agent</h2>
          <button
            onClick={disconnectFromVoice}
            className="text-white/60 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Status */}
        <div className="mb-8">
          {isConnecting && (
            <div className="flex items-center gap-3 text-blue-400">
              <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
              <span>Connecting to voice agent...</span>
            </div>
          )}

          {isConnected && (
            <div className="flex items-center gap-3 text-green-400">
              <div className="w-5 h-5 bg-green-400 rounded-full animate-pulse"></div>
              <span>Connected - Speak naturally</span>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-3 text-red-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Voice Visualizer */}
        {isConnected && (
          <div className="mb-8 flex justify-center">
            <div className="relative">
              <div className={`w-32 h-32 rounded-full border-4 ${isSpeaking ? 'border-blue-400 animate-pulse' : 'border-white/20'} flex items-center justify-center transition-all`}>
                <svg className="w-16 h-16 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
              {isSpeaking && (
                <div className="absolute inset-0 w-32 h-32 rounded-full border-4 border-blue-400/50 animate-ping"></div>
              )}
            </div>
          </div>
        )}

        {/* Transcript */}
        {transcript.length > 0 && (
          <div className="bg-white/5 rounded-2xl p-4 max-h-48 overflow-y-auto mb-6">
            <div className="space-y-2">
              {transcript.map((item, idx) => (
                <div key={idx} className="text-sm">
                  <span className="text-white/60">{item.speaker}:</span>{' '}
                  <span className="text-white/90">{item.text}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Instructions */}
        {isConnected && (
          <div className="bg-white/5 rounded-2xl p-4 mb-6">
            <p className="text-sm text-white/70 mb-3">
              💬 The voice agent can help you with:
            </p>
            <ul className="text-sm text-white/60 space-y-1 list-disc list-inside">
              <li>Checking your PTO balance</li>
              <li>Requesting time off</li>
              <li>Asking about company policies</li>
              <li>Getting information about benefits</li>
            </ul>
          </div>
        )}

        {/* Controls */}
        <div className="flex gap-3">
          {!isConnected && !isConnecting && error && (
            <button
              onClick={connectToVoice}
              className="flex-1 py-3 px-6 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors"
            >
              Retry Connection
            </button>
          )}
          <button
            onClick={disconnectFromVoice}
            className="flex-1 py-3 px-6 rounded-2xl border border-white/10 hover:bg-white/5 text-white/80 hover:text-white font-medium transition-colors"
          >
            {isConnected ? 'End Call' : 'Close'}
          </button>
        </div>

        {/* Session Info */}
        {sessionId && (
          <div className="mt-4 text-xs text-white/40 text-center">
            Session: {sessionId.substring(0, 8)}...
          </div>
        )}
      </div>
    </div>
  );
};

export default VoiceChat;
