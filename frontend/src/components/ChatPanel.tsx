import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import type { Message } from "../types";
import { MessageBubble } from "./MessageBubble";

interface Props {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  onSend: (message: string) => void;
}

const SUGGESTIONS = [
  "Which airports in New England are strong candidates for terminal expansion?",
  "Compare LAX and SNA congestion levels",
  "What is the percentage of long haul flights out of Anchorage?",
  "What is the unmet flight demand in SFO and why?",
];

export function ChatPanel({ messages, isLoading, error, onSend }: Props) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSuggestion = (text: string) => {
    if (isLoading) return;
    onSend(text);
  };

  return (
    <div className="chat">
      <div className="chat__messages">
        {messages.length === 0 && (
          <div className="chat__welcome">
            <h2>Airport Investment Intelligence</h2>
            <p>
              Ask me about US airport investment opportunities. I analyze
              passenger data, congestion, growth trends, and capacity
              constraints to identify the best modernization targets.
            </p>
            <div className="chat__suggestions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="chat__suggestion"
                  onClick={() => handleSuggestion(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="message message--assistant">
            <div className="message__bubble message__bubble--loading">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="chat__error">
            <strong>Error:</strong> {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="chat__input-area" onSubmit={handleSubmit}>
        <textarea
          ref={inputRef}
          className="chat__input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about airport investment opportunities..."
          rows={1}
          disabled={isLoading}
        />
        <button
          className="chat__send"
          type="submit"
          disabled={!input.trim() || isLoading}
        >
          Send
        </button>
      </form>
    </div>
  );
}
