"use client";

import type { AdminConversation } from "@/lib/api";

type ConversationTableProps = {
  conversations: AdminConversation[];
  isLoading: boolean;
  error: string;
};

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-Hans-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ConversationTable({
  conversations,
  isLoading,
  error,
}: ConversationTableProps) {
  return (
    <section className="admin-card admin-card--table" aria-label="全部对话">
      <div className="admin-card__header">
        <div>
          <span className="badge">全部对话</span>
          <h2 className="admin-card__title">查看最近的会话轨迹</h2>
        </div>
        <p className="admin-card__lede">只保留最关键的后台视图，方便快速扫一眼用户在问什么。</p>
      </div>

      {error ? <p className="admin-card__error">{error}</p> : null}

      {isLoading ? (
        <p className="admin-card__empty">正在加载全部对话…</p>
      ) : conversations.length === 0 ? (
        <p className="admin-card__empty">当前还没有会话记录。</p>
      ) : (
        <div className="conversation-table__wrap">
          <table className="conversation-table">
            <thead>
              <tr>
                <th>标题</th>
                <th>用户邮箱</th>
                <th>更新时间</th>
              </tr>
            </thead>
            <tbody>
              {conversations.map((conversation) => (
                <tr key={conversation.conversation_id}>
                  <td>
                    <strong>{conversation.title}</strong>
                    <span>#{conversation.conversation_id}</span>
                  </td>
                  <td>{conversation.user_email}</td>
                  <td>{formatDateTime(conversation.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
