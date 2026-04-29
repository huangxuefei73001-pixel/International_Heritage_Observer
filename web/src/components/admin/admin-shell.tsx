"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  fetchAdminConversations,
  fetchAdminMessages,
  type AdminConversation,
  type AdminMessage,
} from "@/lib/api";
import { getStoredSession } from "@/lib/session";

import { ConversationTable } from "./conversation-table";
import { RecentQuestionTable } from "./recent-question-table";
import { SyncPanel } from "./sync-panel";

export function AdminShell() {
  const router = useRouter();
  const [adminEmail, setAdminEmail] = useState("");
  const [isCheckingAccess, setIsCheckingAccess] = useState(true);
  const [isLoadingConversations, setIsLoadingConversations] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(true);
  const [conversations, setConversations] = useState<AdminConversation[]>([]);
  const [messages, setMessages] = useState<AdminMessage[]>([]);
  const [tableError, setTableError] = useState("");
  const [messageError, setMessageError] = useState("");

  useEffect(() => {
    const session = getStoredSession();
    if (!session || session.role !== "admin") {
      router.replace("/admin/login");
      return;
    }

    setAdminEmail(session.email);
    setIsCheckingAccess(false);

    void loadConversations(session.email);
    void loadMessages(session.email);
  }, [router]);

  async function loadConversations(debugUserEmail: string) {
    setIsLoadingConversations(true);
    setTableError("");

    try {
      const result = await fetchAdminConversations(debugUserEmail);
      setConversations(result);
    } catch (exception) {
      setTableError(exception instanceof Error ? exception.message : "加载全部对话失败");
      setConversations([]);
    } finally {
      setIsLoadingConversations(false);
    }
  }

  async function loadMessages(debugUserEmail: string) {
    setIsLoadingMessages(true);
    setMessageError("");

    try {
      const result = await fetchAdminMessages(debugUserEmail);
      setMessages(result);
    } catch (exception) {
      setMessageError(exception instanceof Error ? exception.message : "加载最近提问失败");
      setMessages([]);
    } finally {
      setIsLoadingMessages(false);
    }
  }

  if (isCheckingAccess) {
    return (
      <section className="admin-shell admin-shell--loading" aria-live="polite">
        <div className="admin-shell__loading-card">
          <p className="admin-shell__loading-text">正在进入管理员后台…</p>
        </div>
      </section>
    );
  }

  return (
    <section className="admin-shell">
      <header className="admin-shell__intro">
        <span className="admin-shell__eyebrow">管理员视图</span>
        <h1 className="admin-shell__title">查看全部提问，必要时手动更新知识库。</h1>
        <p className="admin-shell__lede">
          普通使用者只看到自己的上下文和历史；管理员在这里看到全部对话，并掌握当前库的更新入口。
        </p>
      </header>

      <div className="admin-shell__grid">
        <RecentQuestionTable
          messages={messages}
          isLoading={isLoadingMessages}
          error={messageError}
        />
        <ConversationTable
          conversations={conversations}
          isLoading={isLoadingConversations}
          error={tableError}
        />
        <SyncPanel adminEmail={adminEmail} />
      </div>
    </section>
  );
}
