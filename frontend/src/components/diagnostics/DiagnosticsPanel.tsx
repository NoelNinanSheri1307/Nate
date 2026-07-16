'use client';

import React from 'react';
import { Diagnostics, LatencyStats } from '../../types';
import { Cpu, Database, Brain, Volume2, Clock, Activity } from 'lucide-react';

interface DiagnosticsPanelProps {
  diagnostics: Diagnostics | null;
  latency: LatencyStats;
}

export const DiagnosticsPanel: React.FC<DiagnosticsPanelProps> = ({ diagnostics, latency }) => {
  const getLatencyPercentage = (val: number) => {
    // Max value estimated at 5000ms for safety bounds in rendering
    return Math.min(100, (val / 3000) * 100);
  };

  const getLatencyColor = (key: string) => {
    if (key.includes('STT') || key.includes('transcribe')) return 'bg-cyan-500';
    if (key.includes('LLM') || key.includes('Total LLM')) return 'bg-accent-blue';
    if (key.includes('TTS') || key.includes('synthesis')) return 'bg-purple-500';
    if (key.includes('playback')) return 'bg-emerald-500';
    return 'bg-accent-glow';
  };

  return (
    <aside className="w-80 h-full bg-primary-surface border-l border-border-line flex flex-col p-6 overflow-y-auto select-none">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border-line pb-4 mb-6">
        <Activity className="w-5 h-5 text-accent-blue" />
        <h2 className="text-sm font-semibold tracking-wider uppercase text-primary-text">Telemetry & Logs</h2>
      </div>

      {/* Diagnostics Fields */}
      <div className="space-y-5 mb-8">
        <h3 className="text-xs uppercase tracking-widest text-secondary-text font-bold">System Status</h3>
        
        <div className="space-y-4">
          {/* Session State */}
          <div className="flex items-start gap-3 bg-secondary-surface/50 p-3 rounded-lg border border-border-line/40">
            <Cpu className="w-4 h-4 text-accent-glow mt-0.5" />
            <div className="flex-1">
              <div className="text-[10px] text-secondary-text uppercase tracking-wider">Engine State</div>
              <div className="text-xs font-semibold text-primary-text mt-0.5">
                {diagnostics?.session_state || 'OFFLINE'}
              </div>
            </div>
          </div>

          {/* Whisper STT Model */}
          <div className="flex items-start gap-3 bg-secondary-surface/50 p-3 rounded-lg border border-border-line/40">
            <Database className="w-4 h-4 text-cyan-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-[10px] text-secondary-text uppercase tracking-wider">Whisper STT</div>
              <div className="text-xs font-semibold text-primary-text mt-0.5">
                {diagnostics?.whisper_model ? `${diagnostics.whisper_model} (${diagnostics.cuda_status || 'CPU'})` : 'Offline'}
              </div>
            </div>
          </div>

          {/* Gemini LLM Model */}
          <div className="flex items-start gap-3 bg-secondary-surface/50 p-3 rounded-lg border border-border-line/40">
            <Brain className="w-4 h-4 text-accent-blue mt-0.5" />
            <div className="flex-1">
              <div className="text-[10px] text-secondary-text uppercase tracking-wider">Gemini LLM</div>
              <div className="text-xs font-semibold text-primary-text mt-0.5">
                {diagnostics?.gemini_model || 'Offline'}
              </div>
            </div>
          </div>

          {/* Piper TTS Voice */}
          <div className="flex items-start gap-3 bg-secondary-surface/50 p-3 rounded-lg border border-border-line/40">
            <Volume2 className="w-4 h-4 text-purple-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-[10px] text-secondary-text uppercase tracking-wider">Piper TTS</div>
              <div className="text-xs font-semibold text-primary-text mt-0.5">
                {diagnostics?.piper_voice ? diagnostics.piper_voice.split('/').pop() : 'Offline'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Latency Section */}
      <div className="flex-1 flex flex-col min-h-[300px]">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs uppercase tracking-widest text-secondary-text font-bold">Latency Profile</h3>
          <Clock className="w-4 h-4 text-secondary-text" />
        </div>

        {Object.keys(latency).length === 0 ? (
          <div className="flex-1 border border-dashed border-border-line/40 rounded-lg flex items-center justify-center text-xs text-secondary-text text-center p-4">
            No transaction records.<br />Initiate chat to compute latency.
          </div>
        ) : (
          <div className="space-y-4 bg-secondary-surface/30 border border-border-line/30 p-4 rounded-lg">
            {Object.entries(latency).map(([key, value]) => {
              if (value === 0) return null;
              return (
                <div key={key} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-secondary-text text-[11px] font-medium tracking-wide">{key}</span>
                    <span className="text-primary-text font-mono font-semibold">
                      {value >= 1000 ? `${(value / 1000).toFixed(2)}s` : `${value.toFixed(0)}ms`}
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-border-line/40 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${getLatencyColor(key)}`}
                      style={{ width: `${getLatencyPercentage(value)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
};
