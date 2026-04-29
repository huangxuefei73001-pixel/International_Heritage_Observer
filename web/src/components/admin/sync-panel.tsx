type SyncPanelProps = {
  adminEmail: string;
};

export function SyncPanel({ adminEmail }: SyncPanelProps) {
  return (
    <section className="admin-card admin-card--sync" aria-label="更新知识库">
      <div className="admin-card__header">
        <div>
          <span className="badge">更新知识库</span>
          <h2 className="admin-card__title">当前通过 Codex 同步新增文章</h2>
        </div>
        <p className="admin-card__lede">当前管理员：{adminEmail}</p>
      </div>

      <p className="admin-card__copy">
        你现在的实际工作流，是把文章放进“本次新增”文件夹后，在 Codex 里直接告诉我“请把本次新增同步进库”。
      </p>
      <p className="admin-card__copy">
        网页后台目前不直接执行入库操作，这样可以避免和你在 Codex 里的同步流程打架或产生误解。
      </p>
    </section>
  );
}
