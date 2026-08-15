import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../types";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`message ${isUser ? "message--user" : "message--assistant"}`}>
      <div className="message__bubble">
        {isUser ? (
          <p className="message__text">{message.content}</p>
        ) : (
          <div className="message__markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {!isUser && message.tools_called && message.tools_called.length > 0 && (
        <div className="message__meta">
          <span className="message__tools">
            Tools used: {message.tools_called.join(", ")}
          </span>
        </div>
      )}

      {!isUser && message.assumptions && message.assumptions.length > 0 && (
        <details className="message__assumptions">
          <summary>Assumptions ({message.assumptions.length})</summary>
          <ul>
            {message.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
