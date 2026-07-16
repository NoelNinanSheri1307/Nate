import axios from 'axios';
import { Message, Diagnostics, LatencyStats } from '../types';

const API_BASE_URL = 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  async startConversation(): Promise<{ status: string; state: string }> {
    const res = await client.post('/conversation/start');
    return res.data;
  },

  async stopConversation(): Promise<{ status: string; state: string }> {
    const res = await client.post('/conversation/stop');
    return res.data;
  },

  async recordTurn(): Promise<{ status: string; message?: string }> {
    const res = await client.post('/conversation/record');
    return res.data;
  },

  async sendMessage(message: string): Promise<{
    status: string;
    reply: string;
    latency_ms: number;
    prompt_tokens: number;
    response_tokens: number;
  }> {
    const res = await client.post('/conversation/message', { message });
    return res.data;
  },

  async getHistory(): Promise<{ history: Message[] }> {
    const res = await client.get('/conversation/history');
    return res.data;
  },

  async getDiagnostics(): Promise<Diagnostics> {
    const res = await client.get('/diagnostics');
    return res.data;
  },

  async getLatency(): Promise<{ latency: LatencyStats }> {
    const res = await client.get('/latency');
    return res.data;
  },
};
