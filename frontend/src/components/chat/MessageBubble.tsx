'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Message } from '../../types';
import { Sparkles, User } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  // Lightweight, React 19 safe markdown parser
  const renderContent = (text: string) => {
    if (!text) return null;
    
    // Split into code block zones
    const parts = text.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      if (part.startsWith('```')) {
        // Extract language and code body
        const match = part.match(/```(\w*)\n([\s\S]*?)```/);
        const lang = match ? match[1] : '';
        const code = match ? match[2] : part.slice(3, -3);

        return (
          <div key={index} className="my-3 overflow-hidden rounded-lg border border-border-line bg-background">
            {lang && (
              <div className="flex items-center justify-between border-b border-border-line px-4 py-1.5 text-[10px] uppercase tracking-wider text-secondary-text bg-primary-surface font-mono">
                {lang}
              </div>
            )}
            <pre className="overflow-x-auto p-4 font-mono text-xs text-primary-text leading-relaxed">
              <code>{code}</code>
            </pre>
          </div>
        );
      }

      // Format inline bold/code for normal text paragraphs
      const lines = part.split('\n');
      return lines.map((line, lineIdx) => {
        if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
          return (
            <ul key={`${index}-${lineIdx}`} className="list-disc list-inside ml-4 my-1.5 text-xs md:text-sm text-secondary-text">
              <li>{line.trim().slice(2)}</li>
            </ul>
          );
        }

        // Inline Bold / Code replacement
        const formattedLine = line.split(/(\*\*.*?\*\*|`.*?`)/g).map((word, wordIdx) => {
          if (word.startsWith('**') && word.endsWith('**')) {
            return <strong key={wordIdx} className="font-bold text-primary-text">{word.slice(2, -2)}</strong>;
          }
          if (word.startsWith('`') && word.endsWith('`')) {
            return (
              <code key={wordIdx} className="rounded bg-primary-surface px-1.5 py-0.5 font-mono text-xs text-accent-glow border border-border-line">
                {word.slice(1, -1)}
              </code>
            );
          }
          return word;
        });

        return (
          <p key={`${index}-${lineIdx}`} className="text-xs md:text-sm leading-relaxed mb-2 text-secondary-text">
            {formattedLine}
          </p>
        );
      });
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className={`flex w-full gap-4 py-4 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {/* Icon Avatar on Left for assistant */}
      {!isUser && (
        <img
          src="/logo.jpg"
          alt="Nate Mascot"
          className="flex-shrink-0 w-8 h-8 rounded-full border border-border-line object-cover"
        />
      )}

      {/* Message Box */}
      <div
        className={`max-w-[70%] rounded-2xl px-5 py-3.5 border ${
          isUser
            ? 'bg-secondary-surface border-border-line text-primary-text rounded-tr-none'
            : 'bg-primary-surface border-border-line/60 text-secondary-text rounded-tl-none'
        }`}
      >
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-accent-blue">
            {isUser ? 'You' : 'Nate'}
          </span>
          <span className="text-[9px] text-secondary-text font-mono">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        <div className="mt-1">{renderContent(message.text)}</div>
      </div>

      {/* Icon Avatar on Right for user */}
      {isUser && (
        <div className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-full border border-border-line bg-primary-surface text-secondary-text">
          <User className="w-4 h-4" />
        </div>
      )}
    </motion.div>
  );
};
