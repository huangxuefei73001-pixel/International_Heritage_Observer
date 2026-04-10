"use client";

import type { RefreshLibraryResponse } from "@/lib/api";

type SyncPanelProps = {
  adminEmail: string;
  isRefreshing: boolean;
  status: string;
  error: string;
  summary: RefreshLibraryResponse | null;
  onRefresh: () => void;
};

export function SyncPanel({
  adminEmail,
  isRefreshing,
  status,
  error,
  summary,
  onRefresh,
}: SyncPanelProps) {
  return (
    <section className="admin-card admin-card--sync" aria-label="更新知识库">
      <div className="admin-card__header">
        <div>
          <span className="badge">更新知识库</span>
          <h2 className="admin-card__title">手动把新增文章补进库</h2>
        </div>
        <p className="admin-card__lede">当前管理员：{adminEmail}</p>
      </div>

      <p className="admin-card__copy">
        这一步会沿用现有同步流程，把“本次新增”里的文章分类后写回本地库。
      </p>

      <button className="button-primary admin-card__button" type="button" onClick={onRefresh} disabled={isRefreshing}>
        {isRefreshing ? "正在更新…" : "分类并更新入库"}
      </button>

      <div className="admin-card__feedback" aria-live="polite">
        {status ? <p className="admin-card__status">{status}</p> : null}
        {error ? <p className="admin-card__error">{error}</p> : null}
      </div>

      {summary ? (
        <dl className="sync-panel__summary">
          <div>
            <dt>本次新增</dt>
            <dd>{summary.article_count}</dd>
          </div>
          <div>
            <dt>当前总量</dt>
            <dd>{summary.total_article_count}</dd>
          </div>
          <div>
            <dt>日志路径</dt>
            <dd>{summary.log_path}</dd>
          </div>
        </dl>
      ) : null}
    </section>
  );
}
