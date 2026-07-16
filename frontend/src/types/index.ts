export type SessionState = 'IDLE' | 'LISTENING' | 'THINKING' | 'STREAMING' | 'SPEAKING' | 'WAKE_LISTENING' | 'ERROR';

export interface Message {
  role: 'user' | 'assistant';
  text: string;
  timestamp: string;
  isStreaming?: boolean;
}

export interface Diagnostics {
  session_state: SessionState;
  whisper_model: string;
  cuda_status: string;
  gemini_model: string;
  piper_voice: string;
  memory_size: number;
  wake_word?: string;
  streaming?: boolean;
}

export interface LatencyStats {
  [key: string]: number;
}

export interface PipelineEvent {
  event: string;
  text?: string;
  chunk?: string;
  accumulated?: string;
  language?: string;
  duration?: number;
  duration_ms?: number;
  latency_ms?: number;
  old_state?: SessionState;
  new_state?: SessionState;
  wav_path?: string;
  keyword?: string;
  confidence?: number;
}
