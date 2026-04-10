"use client";

import { useState, useTransition } from "react";

import { ChatInput } from "@/components/chat/chat-input";
import type { ChatMessage } from "@/components/chat/message-list";
import { MessageList } from "@/components/chat/message-list";
import { askQuestion } from "@/lib/api";

const DEBUG_USER_EMAIL = "web@local";

const introMessages: ChatMessage[] = [
  {
    id: "intro-assistant",
    role: "assistant",
    timestamp: "现在",
    content: "直接提问即可。我会优先基于库内文章作答，并附上可点击的来源。",
  },
];

function formatClock(date: Date): string {
  return date.toLocaleTimeString("zh-Hans-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ChatShell() {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>(introMessages);
  const [status, setStatus] = useState("库内优先");
  const [isPending, startTransition] = useTransition();

  async function handleSend(question: string) {
    const askedAt = new Date();
    const askedAtLabel = formatClock(askedAt);

    setMessages((current) => [
      ...current,
      {
        id: `user-${askedAt.getTime()}`,
        role: "user",
        timestamp: askedAtLabel,
        content: question,
      },
    ]);
    setStatus("正在检索库内文章...");

    startTransition(async () => {
      try {
        const result = await askQuestion({
          question,
          conversationId,
          debugUserEmail: DEBUG_USER_EMAIL,
        });

        setConversationId(result.conversation_id);
        setMessages((current) => [
          ...current,
          {
            id: `assistant-${result.conversation_id}-${Date.now()}`,
            role: "assistant",
            timestamp: formatClock(new Date()),
            content: result.answer,
            sources: result.sources,
          },
        ]);
        setStatus("库内优先");
      } catch (error) {
        const message = error instanceof Error ? error.message : "提问失败，请稍后重试。";
        setMessages((current) => [
          ...current,
          {
            id: `assistant-error-${Date.now()}`,
            role: "assistant",
            timestamp: formatClock(new Date()),
            content: `这次没有成功生成回答：${message}`,
          },
        ]);
        setStatus(message);
      }
    });
  }

  function handleReset() {
    setConversationId(null);
    setMessages(introMessages);
    setStatus("库内优先");
  }

  return (
    <section className="chat-shell">
      <header className="chat-toolbar">
        <div className="chat-toolbar__brand">国际遗产观察</div>
        <div className="chat-toolbar__actions">
          <span className="chat-toolbar__status">{isPending ? "处理中" : status}</span>
          <button className="button-ghost button-ghost--compact" type="button" onClick={handleReset}>
            新对话
          </button>
        </div>
      </header>

      <div className="chat-window">
        <MessageList messages={messages} />
      </div>

      <div className="chat-composer">
        <ChatInput onSend={handleSend} hint={isPending ? "正在生成回答..." : ""} />
      </div>
    </section>
  );
}
