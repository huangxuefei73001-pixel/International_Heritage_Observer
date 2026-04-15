import { AdminLoginForm } from "@/components/auth/admin-login-form";

export default function AdminLoginPage() {
  return (
    <main className="page-shell page-shell--admin-login">
      <section className="admin-login">
        <div className="admin-login__intro">
          <div className="admin-login__eyebrow">管理员入口</div>
          <h1 className="admin-login__title">查看全部提问与知识库状态</h1>
          <p className="admin-login__lede">
            普通使用者仍然只看到自己的历史和上下文。管理员登录后，进入统一后台查看全部对话。
          </p>
        </div>
        <AdminLoginForm />
      </section>
    </main>
  );
}
