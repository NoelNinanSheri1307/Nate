import { useEffect, useRef, useState, useCallback } from 'react';
import { PipelineEvent } from '../types';

export const useWebSocket = (
  url: string = 'ws://localhost:8000/ws',
  onMessageReceived?: (event: PipelineEvent) => void
) => {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) return;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected to backend.');
      };

      ws.onmessage = (event) => {
        try {
          const parsed: PipelineEvent = JSON.parse(event.data);
          if (onMessageReceived) {
            onMessageReceived(parsed);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket connection closed. Retrying...');
        // Attempt reconnection
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      };

      ws.onerror = (err) => {
        console.error('WebSocket connection error:', err);
        ws.close();
      };
    } catch (err) {
      console.error('WebSocket startup error:', err);
    }
  }, [url, onMessageReceived]);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const send = useCallback((message: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    } else {
      console.warn('WebSocket is not open. Message not sent:', message);
    }
  }, []);

  return { isConnected, send };
};
