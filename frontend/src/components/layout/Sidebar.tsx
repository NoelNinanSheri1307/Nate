'use client';

import React, { useState } from 'react';
import { Plus, Search, MessageSquare, Info, LogOut } from 'lucide-react';

interface SidebarProps {
  onNewChat: () => void;
  onClearHistory: () => void;
  conversationCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ onNewChat, onClearHistory, conversationCount }) => {
  const [isAboutOpen, setIsAboutOpen] = useState(false);

  return (
    <aside className="w-64 h-full bg-primary-surface border-r border-border-line flex flex-col select-none relative">
      {/* App Header */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-border-line">
        <img
          src="/logo.jpg"
          alt="Nate Mascot"
          className="w-6 h-6 rounded-full border border-border-line object-cover"
        />
        <h1 className="text-sm font-semibold tracking-widest uppercase text-primary-text">Nate Assistant</h1>
      </div>

      {/* New Chat Button */}
      <div className="p-4">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-lg bg-secondary-surface hover:bg-card-bg border border-border-line text-xs font-semibold text-primary-text hover:text-accent-glow transition-all active:scale-98 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          New Session
        </button>
      </div>

      {/* Search Input */}
      <div className="px-4 mb-4 relative">
        <span className="absolute left-7 top-2.5 text-secondary-text">
          <Search className="w-3.5 h-3.5" />
        </span>
        <input
          type="text"
          placeholder="Search conversation..."
          className="w-full pl-9 pr-4 py-2 text-xs rounded-lg bg-secondary-surface/50 border border-border-line/60 text-primary-text placeholder-secondary-text/60 focus:outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/30 transition-all"
        />
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        <div className="px-4 py-2 text-[10px] uppercase tracking-wider text-secondary-text font-bold">
          Active Chat
        </div>
        
        {conversationCount > 0 ? (
          <div className="flex items-center gap-3 px-4 py-2.5 rounded-lg bg-secondary-surface/40 border border-border-line/40 text-xs text-primary-text font-medium mx-2">
            <MessageSquare className="w-4 h-4 text-accent-blue" />
            <span className="truncate">Current Conversation ({conversationCount} turns)</span>
          </div>
        ) : (
          <div className="px-6 py-4 text-xs text-secondary-text/60 italic text-center">
            No messages logged
          </div>
        )}
      </div>

      {/* Bottom Profile / Settings */}
      <div className="p-4 border-t border-border-line space-y-2">
        <button
          onClick={onClearHistory}
          className="w-full flex items-center gap-3 py-2 px-4 rounded-lg hover:bg-red-500/10 text-xs text-secondary-text hover:text-red-400 transition-colors cursor-pointer"
        >
          <LogOut className="w-4 h-4" />
          Clear Conversation
        </button>
        
        <button
          onClick={() => setIsAboutOpen(true)}
          className="w-full flex items-center gap-3 py-2 px-4 rounded-lg hover:bg-secondary-surface/80 border border-border-line/40 bg-secondary-surface/30 text-xs text-primary-text font-semibold cursor-pointer"
        >
          <Info className="w-4 h-4 text-secondary-text" />
          <span>About Creator</span>
        </button>
      </div>

      {/* About Dialog Modal Overlay */}
      {isAboutOpen && (
        <div className="fixed inset-0 bg-black/85 flex items-center justify-center z-50 p-4">
          <div className="bg-primary-surface border border-border-line rounded-xl max-w-lg w-full overflow-hidden shadow-2xl p-6 relative font-sans">
            <button
              onClick={() => setIsAboutOpen(false)}
              className="absolute top-4 right-4 text-secondary-text hover:text-primary-text text-xl cursor-pointer bg-transparent border-0 font-bold"
            >
              &times;
            </button>
            <div className="flex flex-col md:flex-row gap-6 items-center md:items-start mt-2">
              <img
                src="/logo.jpg"
                alt="Nate Mascot"
                className="w-24 h-24 rounded-xl border border-border-line object-cover"
              />
              <div className="flex-1 space-y-4 text-left">
                <div>
                  <h3 className="text-base font-bold text-primary-text">Nate Voice Assistant</h3>
                  <p className="text-xs text-secondary-text mt-2 leading-relaxed">
                    Nate is a real-time, voice-activated AI conversational assistant. It leverages Silero Voice Activity Detection, Faster-Whisper, Gemini 2.5 LLM, and Piper TTS for natural, sub-second latency speech processing.
                  </p>
                </div>
                <div className="border-t border-border-line/50 pt-4 space-y-2">
                  <div className="text-xs text-secondary-text">
                    <span className="font-semibold text-primary-text">Developer:</span> Noel Ninan Sheri
                  </div>
                  <div className="text-xs text-secondary-text">
                    <span className="font-semibold text-primary-text">Email:</span>{' '}
                    <a href="mailto:noelninansheri@gmail.com" className="text-accent-glow hover:underline">
                      noelninansheri@gmail.com
                    </a>
                  </div>
                  <div className="text-xs text-secondary-text">
                    <span className="font-semibold text-primary-text">LinkedIn:</span>{' '}
                    <a
                      href="https://www.linkedin.com/in/noel-ninan-sheri/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-glow hover:underline"
                    >
                      linkedin.com/in/noel-ninan-sheri
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
