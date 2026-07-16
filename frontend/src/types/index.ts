export type SessionState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING' | 'ERROR';

export interface Message {
  role: 'user' | 'assistant';
  text: string;
  timestamp: string;
}

export interface Diagnostics {
  session_state: SessionState;
  whisper_model: string;
  cuda_status: string;
  gemini_model: string;
  piper_voice: string;
  memory_size: number;
}

export interface LatencyStats {
  [key: string]: number;
}

export interface PipelineEvent {
  event: string;
  text?: string;
  language?: string;
  duration?: number;
  duration_ms?: number;
  latency_ms?: number;
  old_state?: SessionState;
  new_state?: SessionState;
  wav_path?: string;
}
