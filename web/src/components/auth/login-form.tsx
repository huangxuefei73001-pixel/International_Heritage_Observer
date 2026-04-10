"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { sendLoginCode, verifyLoginCode } from "@/lib/api";

type Stage = "email" | "code";

export function LoginForm() {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    const rememberedEmail = window.localStorage.getItem("heritage-user-email");
    if (rememberedEmail) {
      setEmail(rememberedEmail);
      setStage("code");
    }
  }, []);

  const buttonLabel = useMemo(() => {
    if (isPending) {
      return stage === "email" ? "正在发送..." : "正在验证...";
    }
    return stage === "email" ? "发送验证码" : "验证并进入";
  }, [isPending, stage]);

  function handleSendCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setStatus("");

    startTransition(async () => {
      try {
        await sendLoginCode(email.trim());
        setStatus("验证码已发送，请查看邮箱。");
        setStage("code");
      } catch (exception) {
        setError(exception instanceof Error ? exception.message : "发送失败");
      }
    });
  }

  function handleVerifyCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setStatus("");

    startTransition(async () => {
      try {
        const result = await verifyLoginCode(email.trim(), code.trim());
        if (!result.verified) {
          throw new Error("验证码无效");
        }

        window.localStorage.setItem("heritage-user-email", result.email);
        window.localStorage.setItem("heritage-user-role", result.role);
        setStatus(result.role === "admin" ? "管理员已确认" : "登录成功");
        router.push(result.role === "admin" ? "/admin" : "/chat");
      } catch (exception) {
        setError(exception instanceof Error ? exception.message : "验证失败");
      }
    });
  }

  return (
    <section className="login-panel">
      <div className="login-panel__header">
        <span className="badge">Email login</span>
        <h2 className="login-panel__title">
          用邮箱验证码进入你的
          <br />
          山野式知识库
        </h2>
        <p className="login-panel__lede">
          登录后继续查看库内线索、会话与证据。界面保持安静、克制，像沿着麦理浩径往前走。
        </p>
      </div>

      {stage === "email" ? (
        <form className="login-form" onSubmit={handleSendCode}>
          <label className="field">
            <span className="field__label">邮箱地址</span>
            <input
              className="field__input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@example.com"
              autoComplete="email"
              required
            />
          </label>
          <p className="field__helper">验证码会发送到这个邮箱，后续登录将依赖真实后端。</p>
          <button className="button-primary" type="submit" disabled={isPending}>
            {buttonLabel}
          </button>
        </form>
      ) : (
        <form className="login-form" onSubmit={handleVerifyCode}>
          <label className="field">
            <span className="field__label">邮箱地址</span>
            <input
              className="field__input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label className="field">
            <span className="field__label">6 位验证码</span>
            <input
              className="field__input"
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="123456"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              required
            />
          </label>
          <p className="field__helper">如果邮箱还没收到验证码，可以返回上一栏重新发送。</p>
          <div className="login-form__actions">
            <button className="button-ghost" type="button" onClick={() => setStage("email")}>
              返回修改邮箱
            </button>
            <button className="button-primary" type="submit" disabled={isPending}>
              {buttonLabel}
            </button>
          </div>
        </form>
      )}

      <div className="form-status" aria-live="polite">
        {status ? <p className="form-status__ok">{status}</p> : null}
        {error ? <p className="form-status__error">{error}</p> : null}
      </div>
    </section>
  );
}
