"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { ChatInput } from "@/components/chat/chat-input";
import type { ChatMessage } from "@/components/chat/message-list";
import { MessageList } from "@/components/chat/message-list";
import {
  askQuestion,
  fetchConversationDetail,
  fetchUserConversations,
  type ConversationSummary,
} from "@/lib/api";
import { ensureGuestSession } from "@/lib/session";

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

function formatStoredTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "刚刚";
  }
  return formatClock(date);
}

export function ChatShell() {
  const router = useRouter();
  const [userEmail, setUserEmail] = useState("");
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>(introMessages);
  const [status, setStatus] = useState("库内优先");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [isBooting, setIsBooting] = useState(true);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    const session = ensureGuestSession();
    if (session.role === "admin") {
      router.replace("/admin");
      return;
    }

    setUserEmail(session.email);

    void loadConversations(session.email).finally(() => {
      setIsBooting(false);
    });
  }, [router]);

  async function loadConversations(identity: string) {
    setHistoryError("");
    try {
      const result = await fetchUserConversations(identity);
      setConversations(result);
    } catch (error) {
      setConversations([]);
      setHistoryError(error instanceof Error ? error.message : "历史记录加载失败");
    }
  }

  async function handleOpenConversation(targetConversationId: number) {
    if (!userEmail) {
      return;
    }

    setIsLoadingHistory(true);
    setHistoryError("");
    setStatus("正在载入历史对话...");

    try {
      const detail = await fetchConversationDetail(targetConversationId, userEmail);
      setConversationId(detail.conversation_id);
      setMessages(
        detail.messages.length > 0
          ? detail.messages.map((message) => ({
              id: `history-${message.id}`,
              role: message.role,
              timestamp: formatStoredTime(message.created_at),
              content: message.content,
              sources: message.sources,
            }))
          : introMessages,
      );
      setHistoryOpen(false);
      setStatus("库内优先");
    } catch (error) {
      setHistoryError(error instanceof Error ? error.message : "历史记录打开失败");
      setStatus("库内优先");
    } finally {
      setIsLoadingHistory(false);
    }
  }

  async function handleSend(question: string) {
    if (!userEmail) {
      setStatus("访客身份尚未就绪，请稍后重试。");
      return;
    }

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
          debugUserEmail: userEmail,
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
        await loadConversations(userEmail);
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
    setHistoryOpen(false);
  }

  return (
    <section className="chat-shell">
      <header className="chat-toolbar">
        <div className="chat-toolbar__brand">国际遗产观察</div>
        <div className="chat-toolbar__actions">
          <button
            className="button-ghost button-ghost--compact"
            type="button"
            onClick={() => setHistoryOpen((open) => !open)}
          >
            我的历史
          </button>
          <span className="chat-toolbar__status">{isPending ? "处理中" : status}</span>
          <button className="button-ghost button-ghost--compact" type="button" onClick={handleReset}>
            新对话
          </button>
        </div>
      </header>

      {historyOpen ? (
        <aside className="history-sheet" aria-label="History preview">
          <div className="history-sheet__header">
            <span className="history-sheet__eyebrow">仅自己可见</span>
            <button
              className="history-sheet__close"
              type="button"
              onClick={() => setHistoryOpen(false)}
              aria-label="关闭历史面板"
            >
              关闭
            </button>
          </div>

          {historyError ? <p className="history-sheet__empty">{historyError}</p> : null}

          {isLoadingHistory ? <p className="history-sheet__empty">正在载入历史对话…</p> : null}

          {!isLoadingHistory && conversations.length === 0 ? (
            <p className="history-sheet__empty">你还没有历史提问，直接开始第一轮对话即可。</p>
          ) : null}

          {!isLoadingHistory && conversations.length > 0 ? (
            <div className="history-sheet__section">
              <div className="history-sheet__label">最近对话</div>
              {conversations.map((conversation) => (
                <button
                  key={conversation.conversation_id}
                  className={`history-sheet__item ${
                    conversation.conversation_id === conversationId ? "history-sheet__item--active" : ""
                  }`}
                  type="button"
                  onClick={() => void handleOpenConversation(conversation.conversation_id)}
                >
                  <strong>{conversation.title}</strong>
                  <span>{formatStoredTime(conversation.updated_at)}</span>
                </button>
              ))}
            </div>
          ) : null}
        </aside>
      ) : null}

      <div className="chat-window">
        <MessageList messages={messages} />
      </div>

      <div className="chat-composer">
        <ChatInput
          onSend={handleSend}
          hint={
            isBooting
              ? "正在准备你的访客会话..."
              : isPending
                ? "正在生成回答..."
                : "Shift + Enter 换行"
          }
          disabled={isBooting}
        />
      </div>
    </section>
  );
}
