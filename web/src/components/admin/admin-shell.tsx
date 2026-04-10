"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  fetchAdminConversations,
  refreshKnowledgeBase,
  type AdminConversation,
  type RefreshLibraryResponse,
} from "@/lib/api";

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
    const role = window.localStorage.getItem("heritage-user-role");
    const email = window.localStorage.getItem("heritage-user-email");

    if (role !== "admin" || !email) {
      router.replace("/chat");
      return;
    }

    setAdminEmail(email);
    setIsCheckingAccess(false);

    void loadConversations(email);
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
          <span className="badge">Admin console</span>
          <p className="admin-shell__loading-text">正在进入管理员后台…</p>
        </div>
      </section>
    );
  }

  return (
    <section className="admin-shell">
      <header className="admin-shell__intro">
        <span className="badge">Admin console</span>
        <h1 className="admin-shell__title">安静的后台，只处理两件事。</h1>
        <p className="admin-shell__lede">
          管理员可以查看全部对话，并在需要时手动更新知识库。界面沿用深蓝山野方向，但更克制、更留白。
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
