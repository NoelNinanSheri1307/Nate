'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Mic, Square, Loader2, Volume2, AlertCircle, Ear, Radio } from 'lucide-react';
import { SessionState } from '../../types';

interface MicButtonProps {
  state: SessionState;
  onClick: () => void;
}

export const MicButton: React.FC<MicButtonProps> = ({ state, onClick }) => {
  const getIcon = () => {
    switch (state) {
      case 'LISTENING':
        return <Square className="w-8 h-8 text-primary-text fill-primary-text" />;
      case 'THINKING':
        return <Loader2 className="w-8 h-8 text-accent-glow animate-spin" />;
      case 'STREAMING':
        return <Radio className="w-8 h-8 text-accent-glow animate-pulse" />;
      case 'SPEAKING':
        return <Volume2 className="w-8 h-8 text-accent-blue animate-pulse" />;
      case 'WAKE_LISTENING':
        return <Ear className="w-8 h-8 text-accent-glow animate-pulse" />;
      case 'ERROR':
        return <AlertCircle className="w-8 h-8 text-red-500" />;
      case 'IDLE':
      default:
        return <Mic className="w-8 h-8 text-primary-text transition-colors group-hover:text-accent-glow" />;
    }
  };

  const getRingColor = () => {
    switch (state) {
      case 'LISTENING':
        return 'border-accent-blue shadow-[0_0_20px_rgba(59,130,246,0.6)]';
      case 'THINKING':
        return 'border-accent-glow shadow-[0_0_15px_rgba(96,165,250,0.3)]';
      case 'STREAMING':
        return 'border-accent-glow shadow-[0_0_20px_rgba(96,165,250,0.4)]';
      case 'SPEAKING':
        return 'border-accent-blue shadow-[0_0_30px_rgba(59,130,246,0.4)]';
      case 'WAKE_LISTENING':
        return 'border-accent-glow/50 shadow-[0_0_10px_rgba(96,165,250,0.2)]';
      case 'ERROR':
        return 'border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.5)]';
      case 'IDLE':
      default:
        return 'border-border-line hover:border-accent-blue hover:shadow-[0_0_15px_rgba(59,130,246,0.3)]';
    }
  };

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className="relative group">
        {/* Pulsing glow background for active states */}
        {state === 'LISTENING' && (
          <motion.div
            className="absolute inset-0 rounded-full bg-accent-blue/20"
            animate={{
              scale: [1, 1.3, 1],
              opacity: [0.6, 0, 0.6],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}
        {state === 'SPEAKING' && (
          <motion.div
            className="absolute inset-0 rounded-full bg-accent-blue/10"
            animate={{
              scale: [1, 1.4, 1],
              opacity: [0.4, 0, 0.4],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}
        {state === 'STREAMING' && (
          <motion.div
            className="absolute inset-0 rounded-full bg-accent-glow/10"
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.3, 0, 0.3],
            }}
            transition={{
              duration: 1.2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}

        {/* Circular Button */}
        <button
          onClick={onClick}
          className={`relative flex items-center justify-center w-20 h-20 rounded-full border bg-primary-surface transition-all duration-300 active:scale-95 cursor-pointer z-10 ${getRingColor()}`}
        >
          {getIcon()}
        </button>
      </div>

      {/* State Text Label */}
      <span className="text-xs uppercase tracking-widest text-secondary-text select-none">
        {state === 'IDLE' && 'Tap to speak'}
        {state === 'LISTENING' && 'Listening...'}
        {state === 'THINKING' && 'Thinking...'}
        {state === 'STREAMING' && 'Responding...'}
        {state === 'SPEAKING' && 'Speaking...'}
        {state === 'WAKE_LISTENING' && 'Say "Hey Nate"'}
        {state === 'ERROR' && 'Connection Error'}
      </span>
    </div>
  );
};
