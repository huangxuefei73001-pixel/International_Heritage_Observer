"use client";

import type { AdminMessage } from "@/lib/api";

type RecentQuestionTableProps = {
  messages: AdminMessage[];
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

function formatUserLabel(value: string): string {
  if (value === "admin") {
    return "管理员";
  }

  if (value.endsWith("@guest.local")) {
    return `访客 · ${value.slice(6, 14)}`;
  }

  return value;
}

export function RecentQuestionTable({
  messages,
  isLoading,
  error,
}: RecentQuestionTableProps) {
  return (
    <section className="admin-card admin-card--table" aria-label="最近全部提问">
      <div className="admin-card__header">
        <div>
          <span className="badge">最近全部提问</span>
          <h2 className="admin-card__title">查看所有用户最近在问什么</h2>
        </div>
        <p className="admin-card__lede">这里按时间倒序展示每一条用户提问，不再只看会话标题。</p>
      </div>

      {error ? <p className="admin-card__error">{error}</p> : null}

      {isLoading ? (
        <p className="admin-card__empty">正在加载最近提问…</p>
      ) : messages.length === 0 ? (
        <p className="admin-card__empty">当前还没有用户提问记录。</p>
      ) : (
        <div className="conversation-table__wrap">
          <table className="conversation-table">
            <thead>
              <tr>
                <th>提问内容</th>
                <th>所属会话</th>
                <th>用户邮箱</th>
                <th>提问时间</th>
              </tr>
            </thead>
            <tbody>
              {messages.map((message) => (
                <tr key={message.message_id}>
                  <td>
                    <strong>{message.content}</strong>
                  </td>
                  <td>
                    <span>{message.conversation_title}</span>
                    <span>#{message.conversation_id}</span>
                  </td>
                  <td>{formatUserLabel(message.user_email)}</td>
                  <td>{formatDateTime(message.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
