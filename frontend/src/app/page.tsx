'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from '../components/layout/Sidebar';
import { ChatArea } from '../components/chat/ChatArea';
import { DiagnosticsPanel } from '../components/diagnostics/DiagnosticsPanel';
import { Waveform } from '../components/waveform/Waveform';
import { MicButton } from '../components/controls/MicButton';
import { api } from '../services/api';
import { Message, SessionState, Diagnostics, LatencyStats } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';
import { Terminal, Activity } from 'lucide-react';

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionState, setSessionState] = useState<SessionState>('IDLE');
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [latency, setLatency] = useState<LatencyStats>({});
  const [isTelemetryOpen, setIsTelemetryOpen] = useState(true);

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
        
      case 'ResponseGeneratedEvent':
        if (event.text) {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', text: event.text, timestamp: new Date().toISOString() }
          ]);
        }
        fetchTelemetry();
        break;
        
      case 'SpeechSynthesizedEvent':
        setSessionState('SPEAKING');
        break;
        
      case 'SpeechPlaybackCompletedEvent':
        setSessionState('IDLE');
        fetchTelemetry();
        break;
        
      default:
        break;
    }
  }, [fetchTelemetry]);

  // Connect to WebSocket endpoint
  useWebSocket('ws://localhost:8000/ws', handleWsEvent);

  // Initialize and load data on mount
  useEffect(() => {
    fetchTelemetry();
    loadHistory();
  }, [fetchTelemetry, loadHistory]);

  // Start Voice Turn
  const handleMicClick = async () => {
    if (sessionState === 'LISTENING') {
      // Manual interrupt / stop
      try {
        await api.stopConversation();
        setSessionState('IDLE');
      } catch (err) {
        console.error('Error stopping turn:', err);
      }
    } else {
      // Trigger voice turn record in background task
      try {
        await api.recordTurn();
      } catch (err) {
        console.error('Error recording turn:', err);
        setSessionState('ERROR');
      }
    }
  };

  const handleNewSession = async () => {
    try {
      await api.startConversation();
      setMessages([]);
      fetchTelemetry();
    } catch (err) {
      console.error('Failed to reset session:', err);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-background text-primary-text overflow-hidden">
      {/* 1. Left Sidebar */}
      <Sidebar
        onNewChat={handleNewSession}
        onClearHistory={handleNewSession}
        conversationCount={messages.length}
      />

      {/* 2. Middle Panel: Chat + Recording Waveform */}
      <main className="flex-1 flex flex-col h-full bg-background relative border-r border-border-line">
        {/* Top bar status */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-border-line/60 bg-primary-surface/20">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-accent-blue" />
            <span className="text-xs font-mono text-secondary-text">Nate Session Console</span>
          </div>
          {/* Toggle diagnostics sidebar */}
          <button
            onClick={() => setIsTelemetryOpen(!isTelemetryOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary-surface hover:bg-card-bg border border-border-line text-[10px] font-semibold text-secondary-text hover:text-primary-text transition-all cursor-pointer"
          >
            <Activity className="w-3.5 h-3.5" />
            {isTelemetryOpen ? 'Hide Telemetry' : 'Show Telemetry'}
          </button>
        </header>

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
    </div>
  );
}
