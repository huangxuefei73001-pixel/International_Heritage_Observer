"use client";

import { useState, useTransition } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { passwordLogin } from "@/lib/api";
import { setStoredSession } from "@/lib/session";

export function AdminLoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("");
    setError("");

    startTransition(async () => {
      try {
        const result = await passwordLogin(username.trim(), password.trim());
        setStoredSession({ email: result.email, role: result.role });
        setStatus("管理员身份已确认，正在进入后台…");
        router.push("/admin");
      } catch (exception) {
        setError(exception instanceof Error ? exception.message : "登录失败");
      }
    });
  }

  return (
    <form className="admin-login__card" onSubmit={handleSubmit}>
      <label className="admin-login__field">
        <span>账号</span>
        <input
          type="text"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          required
        />
      </label>
      <label className="admin-login__field">
        <span>密码</span>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />
      </label>
      <button className="button-primary admin-login__submit" type="submit" disabled={isPending}>
        {isPending ? "进入中..." : "进入后台"}
      </button>
      <p className="admin-login__hint">当前阶段管理员账号固定为 `admin`，密码固定为 `admin`。</p>
      {status ? <p className="admin-login__ok">{status}</p> : null}
      {error ? <p className="admin-login__error">{error}</p> : null}
    </form>
  );
}
