"use client";

import { useState } from "react";
import type { FormEvent } from "react";

type ChatInputProps = {
  onSend?: (question: string) => void | Promise<void>;
  hint?: string;
};

export function ChatInput({ onSend, hint = "" }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isSending, setIsSending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = value.trim();
    if (!question) {
      return;
    }

    setIsSending(true);

    try {
      await onSend?.(question);
      setValue("");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <div className="composer__topline">
        <span className="composer__label">输入问题</span>
        {hint ? <span className="composer__hint">{hint}</span> : null}
      </div>
      <textarea
        className="composer__textarea"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="例如：最近韩国有什么世界遗产动态？"
        rows={3}
      />
      <div className="composer__footer">
        <div className="composer__status" />
        <button className="button-primary" type="submit" disabled={isSending || value.trim().length === 0}>
          {isSending ? "处理中..." : "发送"}
        </button>
      </div>
    </form>
  );
}
