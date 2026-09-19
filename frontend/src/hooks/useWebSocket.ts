import { useEffect, useState } from 'react';
import { useValidationStore } from '../stores/validationStore';

export function useWebSocket(runId: string | null) {
  const [messages, setMessages] = useState<any[]>([]);
  const { setScanProgress, setValidationProgress } = useValidationStore();

  useEffect(() => {
    if (!runId) return;

    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`ws://localhost:8005/ws/${runId}`);

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          setMessages((prev) => [...prev, payload]);

          if (payload.type === 'scan_progress' || payload.type === 'scan_completed') {
            setScanProgress(payload.data);
          } else if (payload.type === 'validation_progress' || payload.type === 'validation_completed') {
            setValidationProgress(payload.data);
          }
        } catch (e) {
          console.error('Failed to parse WS message', e);
        }
      };

      ws.onerror = (e) => {
        console.warn('WebSocket connection error:', e);
      };
    } catch (err) {
      console.warn('Could not establish WebSocket:', err);
    }

    return () => {
      if (ws) ws.close();
    };
  }, [runId]);

  return messages;
}
