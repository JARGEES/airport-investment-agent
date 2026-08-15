import { useCallback, useRef, useState } from "react";
import type { ChatResponse, HealthResponse, Message } from "../types";

const API_BASE = "/api";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const conversationIdRef = useRef<string | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        setHealth(await res.json());
      }
    } catch {
      // backend not reachable — ignore
    }
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          conversation_id: conversationIdRef.current,
        }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`Server error ${res.status}: ${detail}`);
      }

      const data: ChatResponse = await res.json();
      conversationIdRef.current = data.conversation_id;

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
        tools_called: data.tools_called,
        assumptions: data.assumptions,
        data_vintage: data.data_vintage,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    conversationIdRef.current = null;
    setError(null);
  }, []);

  const updateSettings = useCallback(
    async (patch: { model?: string; analysis_mode?: string }) => {
      try {
        const res = await fetch(`${API_BASE}/settings`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(patch),
        });
        if (res.ok) {
          await fetchHealth();
        }
      } catch {
        // ignore
      }
    },
    [fetchHealth],
  );

  return {
    messages,
    isLoading,
    error,
    health,
    sendMessage,
    clearChat,
    fetchHealth,
    updateSettings,
  };
}
