"use client";

import type { SourceCard } from "@/lib/api";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  sources?: SourceCard[];
};

type MessageListProps = {
  messages: ChatMessage[];
};

export function MessageList({ messages }: MessageListProps) {
  return (
    <div className="message-list" aria-label="Conversation transcript">
      {messages.map((message) => (
        <article
          key={message.id}
          className={`message ${message.role === "assistant" ? "message--assistant" : "message--user"}`}
        >
          <div className="message__meta">
            <span className="message__role">{message.role === "assistant" ? "回答" : "提问"}</span>
            <time className="message__time">{message.timestamp}</time>
          </div>
          <div className="message__bubble">
            <p>{message.content}</p>
            {message.sources && message.sources.length > 0 ? (
              <div className="message__sources">
                {message.sources.map((source) => (
                  <a
                    key={`${message.id}-${source.url}`}
                    className="source-chip"
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span>{source.evidence_type}</span>
                    <strong>{source.title}</strong>
                  </a>
                ))}
              </div>
            ) : null}
          </div>
        </article>
      ))}
    </div>
  );
}
