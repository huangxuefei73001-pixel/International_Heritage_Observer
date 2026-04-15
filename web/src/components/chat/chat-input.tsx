"use client";

import { useState } from "react";
import type { FormEvent } from "react";

type ChatInputProps = {
  onSend?: (question: string) => void | Promise<void>;
  hint?: string;
  disabled?: boolean;
};

export function ChatInput({ onSend, hint = "", disabled = false }: ChatInputProps) {
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
      <textarea
        className="composer__textarea"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        disabled={disabled || isSending}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void handleSubmit(event as unknown as FormEvent<HTMLFormElement>);
          }
        }}
        placeholder="直接提问。例如：近三年国际上的世界遗产数字化有哪些发展？"
        rows={2}
      />
      <div className="composer__footer">
        <div className="composer__status">
          {hint ? <span className="composer__hint">{hint}</span> : null}
        </div>
        <button
          className="button-primary"
          type="submit"
          disabled={disabled || isSending || value.trim().length === 0}
        >
          {isSending ? "处理中..." : "发送"}
        </button>
      </div>
    </form>
  );
}
