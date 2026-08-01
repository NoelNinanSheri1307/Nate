import { Message, Diagnostics, LatencyStats, SessionInfo } from '../types';

// In-memory mock database for Demo Mode (zero network dependency)
let sessions: SessionInfo[] = [
  { id: 'default', name: 'General Discussion', turns: 4 },
  { id: 'chat_1720000000', name: 'System Info Queries', turns: 2 }
];

let activeSessionId = 'default';

let messageHistory: Record<string, Message[]> = {
  default: [
    { role: 'user', text: 'Hello Nate, introduce yourself.', timestamp: new Date(Date.now() - 60000 * 5).toISOString() },
    { role: 'assistant', text: 'Hello! I am Nate, a local-first voice assistant designed for low latency. I process audio inputs via Faster-Whisper and synthesize speech using Piper.', timestamp: new Date(Date.now() - 60000 * 4).toISOString() },
    { role: 'user', text: 'What is your stack?', timestamp: new Date(Date.now() - 60000 * 2).toISOString() },
    { role: 'assistant', text: 'I am built with a Python FastAPI backend, Next.js frontend, and local ONNX runtime engines for speech synthesis and VAD.', timestamp: new Date(Date.now() - 60000 * 1).toISOString() }
  ],
  chat_1720000000: [
    { role: 'user', text: 'How do you achieve low latency?', timestamp: new Date(Date.now() - 60000 * 10).toISOString() },
    { role: 'assistant', text: 'By streaming Gemini responses chunk-by-chunk and splitting them into sentences to compile local vocal audio progressively.', timestamp: new Date(Date.now() - 60000 * 9).toISOString() }
  ]
};

const mockDiagnostics: Diagnostics = {
  session_state: 'IDLE',
  whisper_model: 'small',
  cuda_status: 'CUDA Available (RTX 4060)',
  gemini_model: 'gemini-3.1-flash-lite',
  piper_voice: 'en_US-joe-medium.onnx',
  memory_size: 4,
  wake_word: 'Available',
  streaming: true
};

const mockLatency: LatencyStats = {
  'stt_transcription_ms': 342.12,
  'llm_first_chunk_ms': 420.55,
  'tts_synthesis_ms': 185.34,
  'total_roundtrip_ms': 948.01
};

export const api = {
  async startConversation(): Promise<{ status: string; state: string }> {
    return { status: 'success', state: 'IDLE' };
  },

  async stopConversation(): Promise<{ status: string; state: string }> {
    return { status: 'success', state: 'IDLE' };
  },

  async recordTurn(): Promise<{ status: string; message?: string }> {
    return { status: 'success' };
  },

  async sendMessage(message: string): Promise<{
    status: string;
    reply: string;
    latency_ms: number;
    prompt_tokens: number;
    response_tokens: number;
  }> {
    const timestamp = new Date().toISOString();
    if (!messageHistory[activeSessionId]) {
      messageHistory[activeSessionId] = [];
    }
    messageHistory[activeSessionId].push({ role: 'user', text: message, timestamp });
    
    const reply = "I am running in interactive demo mode. To chat with my live model, please follow the 'Run Locally' guide!";
    messageHistory[activeSessionId].push({ role: 'assistant', text: reply, timestamp });
    
    const sess = sessions.find(s => s.id === activeSessionId);
    if (sess) {
      sess.turns = messageHistory[activeSessionId].length;
      if (sess.name === 'New Chat') {
        sess.name = message.substring(0, 30) + (message.length > 30 ? '...' : '');
      }
    }

    return {
      status: 'success',
      reply,
      latency_ms: 450,
      prompt_tokens: 12,
      response_tokens: 24
    };
  },

  async getHistory(): Promise<{ history: Message[] }> {
    return { history: messageHistory[activeSessionId] || [] };
  },

  async getDiagnostics(): Promise<Diagnostics> {
    const activeHistory = messageHistory[activeSessionId] || [];
    return {
      ...mockDiagnostics,
      memory_size: activeHistory.length
    };
  },

  async getLatency(): Promise<{ latency: LatencyStats }> {
    return { latency: mockLatency };
  },

  async startWakeWord(): Promise<{ status: string }> {
    return { status: 'success' };
  },

  async stopWakeWord(): Promise<{ status: string }> {
    return { status: 'success' };
  },

  async getSessions(): Promise<{ sessions: SessionInfo[]; active_id: string }> {
    return { sessions, active_id: activeSessionId };
  },

  async createSession(): Promise<{ status: string; session_id: string; name: string }> {
    const session_id = `chat_${Date.now()}`;
    const name = 'New Chat';
    sessions.push({ id: session_id, name, turns: 0 });
    messageHistory[session_id] = [];
    activeSessionId = session_id;
    return { status: 'created', session_id, name };
  },

  async activateSession(sessionId: string): Promise<{ status: string; session_id: string }> {
    if (sessions.some(s => s.id === sessionId)) {
      activeSessionId = sessionId;
    }
    return { status: 'activated', session_id: activeSessionId };
  },

  async deleteSession(sessionId: string): Promise<{ status: string }> {
    if (sessionId === 'default') {
      messageHistory['default'] = [];
      const sess = sessions.find(s => s.id === 'default');
      if (sess) {
        sess.name = 'General Discussion';
        sess.turns = 0;
      }
      return { status: 'cleared' };
    }
    
    sessions = sessions.filter(s => s.id !== sessionId);
    delete messageHistory[sessionId];
    if (activeSessionId === sessionId) {
      activeSessionId = 'default';
    }
    return { status: 'deleted' };
  }
};
