'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Sidebar } from '../components/layout/Sidebar';
import { ChatArea } from '../components/chat/ChatArea';
import { DiagnosticsPanel } from '../components/diagnostics/DiagnosticsPanel';
import { Waveform } from '../components/waveform/Waveform';
import { MicButton } from '../components/controls/MicButton';
import { api } from '../services/api';
import { Message, SessionState, Diagnostics, LatencyStats } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';
import { Terminal, Activity, Ear } from 'lucide-react';
import Link from 'next/link';

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionState, setSessionState] = useState<SessionState>('IDLE');
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [latency, setLatency] = useState<LatencyStats>({});
  const [isTelemetryOpen, setIsTelemetryOpen] = useState(true);
  const [wakeWordEnabled, setWakeWordEnabled] = useState(false);
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>('default');
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);
  const streamingRef = useRef(false);

  // Fetch metrics and history from REST API
  const fetchTelemetry = useCallback(async () => {
    try {
      const diagData = await api.getDiagnostics();
      setDiagnostics(diagData);
      
      const latData = await api.getLatency();
      setLatency(latData.latency);
    } catch (err) {
      console.error('Failed to fetch system telemetry:', err);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const histData = await api.getHistory();
      setMessages(histData.history);
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      const sessData = await api.getSessions();
      setSessions(sessData.sessions);
      setActiveSessionId(sessData.active_id);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }, []);

  // Set up WebSocket to listen to real-time events
  const handleWsEvent = useCallback((event: any) => {
    console.log('Received Event:', event);
    
    switch (event.event) {
      case 'StateChangedEvent':
        if (event.new_state) {
          setSessionState(event.new_state);
        }
        break;
        
      case 'RecordingStartedEvent':
        setSessionState('LISTENING');
        break;
        
      case 'RecordingStoppedEvent':
        setSessionState('THINKING');
        break;
        
      case 'TranscriptionCompletedEvent':
        if (event.text) {
          setMessages((prev) => [
            ...prev,
            { role: 'user', text: event.text, timestamp: new Date().toISOString() }
          ]);
        }
        break;
        
      case 'ThinkingStartedEvent':
        setSessionState('THINKING');
        break;

      case 'ResponseChunkEvent':
        // Streaming: progressively update the last assistant message
        if (event.accumulated) {
          setSessionState('STREAMING');
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant' && last.isStreaming) {
              // Update existing streaming message
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...last,
                text: event.accumulated,
              };
              return updated;
            } else {
              // Create new streaming message
              return [
                ...prev,
                {
                  role: 'assistant',
                  text: event.accumulated,
                  timestamp: new Date().toISOString(),
                  isStreaming: true,
                }
              ];
            }
          });
          streamingRef.current = true;
        }
        break;
        
      case 'ResponseGeneratedEvent':
        // Finalize the streaming message
        if (event.text) {
          if (streamingRef.current) {
            // Mark the streaming message as complete
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === 'assistant' && updated[lastIdx].isStreaming) {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  text: event.text,
                  isStreaming: false,
                };
              }
              return updated;
            });
            streamingRef.current = false;
          } else {
            // Non-streaming fallback: add complete message
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', text: event.text, timestamp: new Date().toISOString() }
            ]);
          }
        }
        fetchTelemetry();
        loadSessions();
        break;
        
      case 'SpeechSynthesizedEvent':
        setSessionState('SPEAKING');
        break;
        
      case 'SpeechPlaybackCompletedEvent':
        setSessionState('IDLE');
        fetchTelemetry();
        break;

      case 'WakeWordDetectedEvent':
        // Visual notification: wake word triggered
        console.log('Wake word detected:', event.keyword);
        break;
        
      default:
        break;
    }
  }, [fetchTelemetry]);

  // Connect to WebSocket endpoint
  // useWebSocket('ws://localhost:8000/ws', handleWsEvent);

  // Initialize and load data on mount
  useEffect(() => {
    fetchTelemetry();
    loadHistory();
    loadSessions();
  }, [fetchTelemetry, loadHistory, loadSessions]);

  // Start Voice Turn
  const handleMicClick = async () => {
    setIsDemoModalOpen(true);
  };

  const handleNewSession = async () => {
    try {
      await api.createSession();
      await loadSessions();
      await loadHistory();
      streamingRef.current = false;
      fetchTelemetry();
    } catch (err) {
      console.error('Failed to reset session:', err);
    }
  };

  const handleSelectSession = async (id: string) => {
    try {
      await api.activateSession(id);
      await loadSessions();
      await loadHistory();
      fetchTelemetry();
    } catch (err) {
      console.error('Failed to select session:', err);
    }
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await api.deleteSession(id);
      await loadSessions();
      await loadHistory();
      fetchTelemetry();
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleClearConversation = async () => {
    try {
      await api.deleteSession(activeSessionId);
      await loadSessions();
      await loadHistory();
      fetchTelemetry();
    } catch (err) {
      console.error('Failed to clear conversation:', err);
    }
  };

  const toggleWakeWord = async () => {
    setIsDemoModalOpen(true);
  };

  return (
    <div className="flex h-screen w-screen bg-background text-primary-text overflow-hidden">
      {/* 1. Left Sidebar */}
      <Sidebar
        onNewChat={handleNewSession}
        onClearHistory={handleClearConversation}
        conversationCount={messages.length}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
      />

      {/* 2. Middle Panel: Chat + Recording Waveform */}
      <main className="flex-1 flex flex-col h-full bg-background relative border-r border-border-line">
        {/* Top bar status */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-border-line/60 bg-primary-surface/20">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-accent-blue" />
            <span className="text-xs font-mono text-secondary-text">Nate Session Console</span>
          </div>
          <div className="flex items-center gap-2">
            {/* Wake word toggle */}
            <button
              onClick={toggleWakeWord}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-[10px] font-semibold transition-all cursor-pointer ${
                wakeWordEnabled
                  ? 'bg-accent-blue/20 border-accent-blue/50 text-accent-glow'
                  : 'bg-secondary-surface hover:bg-card-bg border-border-line text-secondary-text hover:text-primary-text'
              }`}
            >
              <Ear className="w-3.5 h-3.5" />
              {wakeWordEnabled ? '"Hey Jarvis/Mycroft" Active' : 'Wake Word'}
            </button>
            {/* Toggle diagnostics sidebar */}
            <button
              onClick={() => setIsTelemetryOpen(!isTelemetryOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary-surface hover:bg-card-bg border border-border-line text-[10px] font-semibold text-secondary-text hover:text-primary-text transition-all cursor-pointer"
            >
              <Activity className="w-3.5 h-3.5" />
              {isTelemetryOpen ? 'Hide Telemetry' : 'Show Telemetry'}
            </button>
          </div>
        </header>

        {/* Interactive Demo Banner */}
        <div className="mx-6 mt-4 p-4 bg-[#3B82F6]/10 border border-[#3B82F6]/30 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 font-mono">
          <div className="space-y-1">
            <h4 className="text-xs font-bold text-[#60A5FA] uppercase tracking-wider">Interactive Demo</h4>
            <p className="text-[11px] text-[#9EA6B2] leading-relaxed max-w-2xl font-sans">
              This deployment showcases Nate&apos;s interface, architecture, and user experience.
              The complete desktop assistant—including wake-word detection, local speech recognition, and low-latency voice synthesis—runs locally to leverage direct access to microphone and speaker hardware.
              See the setup guide to run the full experience.
            </p>
          </div>
          <Link
            href="/setup"
            className="flex-shrink-0 text-center px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-xs font-semibold rounded-lg transition-all active:scale-95 cursor-pointer whitespace-nowrap"
          >
            Run Locally
          </Link>
        </div>

        {/* Dynamic Chat messages */}
        <ChatArea messages={messages} state={sessionState} />

        {/* Bottom controls panel */}
        <footer className="border-t border-border-line bg-primary-surface/40 p-6 flex flex-col items-center gap-5">
          {/* Waveform Visualization */}
          <div className="w-full max-w-lg">
            <Waveform state={sessionState} />
          </div>

          {/* Large circular Mic Button */}
          <MicButton state={sessionState} onClick={handleMicClick} />
        </footer>
      </main>

      {/* 3. Right Sidebar: Telemetry & Logs */}
      {isTelemetryOpen && (
        <DiagnosticsPanel diagnostics={diagnostics} latency={latency} />
      )}

      {/* Demo Mode Modal Overlay */}
      {isDemoModalOpen && (
        <div className="fixed inset-0 bg-black/85 flex items-center justify-center z-50 p-4">
          <div className="bg-primary-surface border border-border-line rounded-xl max-w-md w-full overflow-hidden shadow-2xl p-6 relative font-mono">
            <button
              onClick={() => setIsDemoModalOpen(false)}
              className="absolute top-4 right-4 text-secondary-text hover:text-primary-text text-xl cursor-pointer bg-transparent border-0 font-bold"
            >
              &times;
            </button>
            <div className="space-y-6 text-left">
              <div className="space-y-2">
                <h3 className="text-sm font-bold text-[#60A5FA] uppercase tracking-wider">Voice Assistant Standby</h3>
                <p className="text-xs text-[#9EA6B2] leading-relaxed font-sans">
                  The voice assistant runs as a local desktop service to access your microphone and synthesize audio directly. Because this is a hosted showcase, voice interactions are disabled.
                </p>
              </div>
              
              <div className="grid grid-cols-1 gap-2 pt-2">
                <a
                  href="https://github.com/NoelNinanSheri1307/Nate"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full text-center py-2.5 px-4 rounded-lg bg-[#3B82F6] hover:bg-[#2563EB] text-white text-xs font-semibold transition-all cursor-pointer"
                >
                  View GitHub
                </a>
                <Link
                  href="/setup"
                  onClick={() => setIsDemoModalOpen(false)}
                  className="w-full text-center py-2.5 px-4 rounded-lg bg-secondary-surface hover:bg-card-bg border border-border-line text-xs font-semibold text-primary-text hover:text-[#60A5FA] transition-all cursor-pointer"
                >
                  Run Locally
                </Link>
                <a
                  href="https://github.com/NoelNinanSheri1307/Nate/blob/main/README.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full text-center py-2.5 px-4 rounded-lg bg-[#181A1F] hover:bg-[#20242C] text-xs font-semibold text-secondary-text hover:text-primary-text transition-all cursor-pointer"
                >
                  Documentation
                </a>
                <a
                  href="https://github.com/NoelNinanSheri1307/Nate/releases/tag/v1.0.0"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full text-center py-2.5 px-4 rounded-lg bg-[#181A1F] hover:bg-[#20242C] text-xs font-semibold text-secondary-text hover:text-primary-text transition-all cursor-pointer"
                >
                  Latest Release
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
