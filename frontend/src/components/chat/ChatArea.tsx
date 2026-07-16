'use client';

import React, { useEffect, useRef } from 'react';
import { Message, SessionState } from '../../types';
import { MessageBubble } from './MessageBubble';
import { Sparkles, ArrowDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ChatAreaProps {
  messages: Message[];
  state: SessionState;
}

export const ChatArea: React.FC<ChatAreaProps> = ({ messages, state }) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, state]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col space-y-2">
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-8 select-none">
          <motion.img
            src="/logo.jpg"
            alt="Nate Mascot"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
            className="w-16 h-16 rounded-full border border-border-line animate-pulse object-cover mb-4"
          />
          <h2 className="text-lg font-semibold text-primary-text tracking-wide mb-1">Meet Nate</h2>
          <p className="text-xs text-secondary-text max-w-sm">
            A real-time voice-activated assistant. Say hello, ask questions, or chat naturally.
          </p>
          {state === 'WAKE_LISTENING' && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-xs text-accent-glow mt-4 font-mono"
            >
              Listening for &quot;Hey Nate&quot;...
            </motion.p>
          )}
        </div>
      ) : (
        <div className="flex-1 flex flex-col">
          {messages.map((msg, index) => (
            <MessageBubble key={`${msg.timestamp}-${index}`} message={msg} />
          ))}

          {/* Thinking indicator */}
          <AnimatePresence>
            {state === 'THINKING' && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-3 py-4 text-xs text-accent-blue font-mono"
              >
                <img
                  src="/logo.jpg"
                  alt="Nate Mascot"
                  className="flex-shrink-0 w-8 h-8 rounded-full border border-border-line object-cover animate-pulse"
                />
                <div className="flex gap-1.5 items-center">
                  <span className="text-secondary-text">Nate is thinking</span>
                  <span className="flex gap-0.5 mt-0.5">
                    <span className="w-1.5 h-1.5 bg-accent-blue rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                    <span className="w-1.5 h-1.5 bg-accent-blue rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                    <span className="w-1.5 h-1.5 bg-accent-blue rounded-full animate-bounce"></span>
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Streaming indicator (blinking cursor) */}
          <AnimatePresence>
            {state === 'STREAMING' && messages.length > 0 && messages[messages.length - 1]?.isStreaming && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2 pl-12 py-1 text-xs text-accent-glow font-mono"
              >
                <span className="inline-block w-2 h-4 bg-accent-blue animate-pulse rounded-sm"></span>
              </motion.div>
            )}
          </AnimatePresence>
          
          <div ref={scrollRef} />
        </div>
      )}
    </div>
  );
};
