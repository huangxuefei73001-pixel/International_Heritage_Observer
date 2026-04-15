"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  fetchAdminConversations,
  refreshKnowledgeBase,
  type AdminConversation,
  type RefreshLibraryResponse,
} from "@/lib/api";
import { getStoredSession } from "@/lib/session";

import { ConversationTable } from "./conversation-table";
import { SyncPanel } from "./sync-panel";

export function AdminShell() {
  const router = useRouter();
  const [adminEmail, setAdminEmail] = useState("");
  const [isCheckingAccess, setIsCheckingAccess] = useState(true);
  const [isLoadingConversations, setIsLoadingConversations] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [conversations, setConversations] = useState<AdminConversation[]>([]);
  const [tableError, setTableError] = useState("");
  const [syncStatus, setSyncStatus] = useState("点击按钮即可手动更新知识库。");
  const [syncError, setSyncError] = useState("");
  const [syncSummary, setSyncSummary] = useState<RefreshLibraryResponse | null>(null);

  useEffect(() => {
    const session = getStoredSession();
    if (!session || session.role !== "admin") {
      router.replace("/admin/login");
      return;
    }

    setAdminEmail(session.email);
    setIsCheckingAccess(false);

    void loadConversations(session.email);
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

  async function handleRefreshLibrary() {
    if (!adminEmail) {
      setSyncError("管理员身份未就绪，请重新登录。");
      return;
    }

    setIsRefreshing(true);
    setSyncError("");
    setSyncStatus("正在同步新增文章…");

    try {
      const result = await refreshKnowledgeBase(adminEmail);
      setSyncSummary(result);
      setSyncStatus("知识库已更新完成。");
      await loadConversations(adminEmail);
    } catch (exception) {
      setSyncStatus("");
      setSyncError(exception instanceof Error ? exception.message : "更新知识库失败");
    } finally {
      setIsRefreshing(false);
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
        <ConversationTable
          conversations={conversations}
          isLoading={isLoadingConversations}
          error={tableError}
        />
        <SyncPanel
          adminEmail={adminEmail}
          isRefreshing={isRefreshing}
          status={syncStatus}
          error={syncError}
          summary={syncSummary}
          onRefresh={handleRefreshLibrary}
        />
      </div>
    </section>
  );
}
