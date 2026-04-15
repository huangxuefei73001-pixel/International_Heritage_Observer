"use client";

import type { ReactNode } from "react";

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

const markdownLinkPattern = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
const rawUrlPattern = /https?:\/\/[^\s]+/g;

function normalizeUrl(url: string): { href: string; trailing: string } {
  let href = url;
  let trailing = "";

  while (/[),.;|]+$/.test(href)) {
    trailing = href.slice(-1) + trailing;
    href = href.slice(0, -1);
  }

  return { href, trailing };
}

function renderInlineContent(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let keyIndex = 0;

  const pushPlainText = (value: string) => {
    if (!value) {
      return;
    }
    nodes.push(value);
  };

  while (cursor < text.length) {
    markdownLinkPattern.lastIndex = cursor;
    rawUrlPattern.lastIndex = cursor;

    const markdownMatch = markdownLinkPattern.exec(text);
    const rawUrlMatch = rawUrlPattern.exec(text);

    const markdownIndex = markdownMatch?.index ?? Number.POSITIVE_INFINITY;
    const rawUrlIndex = rawUrlMatch?.index ?? Number.POSITIVE_INFINITY;

    const nextIndex = Math.min(markdownIndex, rawUrlIndex);
    if (!Number.isFinite(nextIndex)) {
      pushPlainText(text.slice(cursor));
      break;
    }

    pushPlainText(text.slice(cursor, nextIndex));

    if (markdownIndex <= rawUrlIndex && markdownMatch) {
      nodes.push(
        <a
          key={`inline-link-${keyIndex}`}
          className="message__inline-link"
          href={markdownMatch[2]}
          target="_blank"
          rel="noreferrer"
        >
          {markdownMatch[1]}
        </a>,
      );
      keyIndex += 1;
      cursor = markdownMatch.index + markdownMatch[0].length;
      continue;
    }

    if (rawUrlMatch) {
      const { href, trailing } = normalizeUrl(rawUrlMatch[0]);
      nodes.push(
        <a
          key={`inline-link-${keyIndex}`}
          className="message__inline-link"
          href={href}
          target="_blank"
          rel="noreferrer"
        >
          {href}
        </a>,
      );
      keyIndex += 1;
      pushPlainText(trailing);
      cursor = rawUrlMatch.index + rawUrlMatch[0].length;
    }
  }

  return nodes;
}

function renderParagraphs(content: string) {
  const lines = content
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const nodes: ReactNode[] = [];
  let pendingList: string[] = [];

  function flushList() {
    if (pendingList.length === 0) {
      return;
    }

    nodes.push(
      <ul key={`list-${nodes.length}`} className="message__list">
        {pendingList.map((item, index) => (
          <li key={`${item}-${index}`}>{renderInlineContent(item)}</li>
        ))}
      </ul>,
    );
    pendingList = [];
  }

  lines.forEach((line) => {
    const isListItem = /^[-•]\s+/.test(line);
    if (isListItem) {
      pendingList.push(line.replace(/^[-•]\s+/, ""));
      return;
    }

    flushList();

    if (/^[\u4e00-\u9fa5A-Za-z0-9]+[:：]$/.test(line)) {
      nodes.push(
        <h3 key={`heading-${nodes.length}`} className="message__heading">
          {renderInlineContent(line)}
        </h3>,
      );
      return;
    }

    nodes.push(
      <p key={`paragraph-${nodes.length}`} className="message__paragraph">
        {renderInlineContent(line)}
      </p>,
    );
  });

  flushList();
  return nodes;
}

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
            {renderParagraphs(message.content)}
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
