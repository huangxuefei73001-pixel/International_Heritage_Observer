export type SourceCard = {
  title: string;
  url: string;
  published_at: string;
  category: string;
  evidence_type: string;
};

export type AskResponse = {
  conversation_id: number;
  answer: string;
  sources: SourceCard[];
  messages_saved: number;
};

export type LoginCodeResponse = {
  email: string;
  status: string;
};

export type VerifyCodeResponse = {
  email: string;
  role: "user" | "admin";
  verified: boolean;
};

export type AdminConversation = {
  conversation_id: number;
  title: string;
  user_email: string;
  created_at: string;
  updated_at: string;
};

export type RefreshLibraryResponse = {
  article_count: number;
  total_article_count: number;
  log_path: string;
  [key: string]: unknown;
};

export class ApiRequestError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail;
  }
}

type RequestOptions = RequestInit & {
  debugUserEmail?: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

async function readJsonError(
  response: Response,
): Promise<{ message: string; detail: unknown }> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return { message: payload.detail, detail: payload.detail };
    }
    if (payload.detail && typeof payload.detail === "object") {
      const nestedDetail =
        "detail" in payload.detail && typeof payload.detail.detail === "string"
          ? payload.detail.detail
          : JSON.stringify(payload.detail);
      return { message: nestedDetail, detail: payload.detail };
    }
  } catch {
    // Ignore JSON parse errors and fall back below.
  }

  return {
    message: `Request failed with status ${response.status}`,
    detail: null,
  };
}

async function requestJson<T>(path: string, init: RequestOptions = {}): Promise<T> {
  const { debugUserEmail, headers, ...rest } = init;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(debugUserEmail ? { "X-Debug-User": debugUserEmail } : {}),
      ...(headers ?? {}),
    },
  });

  if (!response.ok) {
    const errorPayload = await readJsonError(response);
    throw new ApiRequestError(
      errorPayload.message,
      response.status,
      errorPayload.detail,
    );
  }

  return (await response.json()) as T;
}

export function sendLoginCode(email: string): Promise<LoginCodeResponse> {
  return requestJson<LoginCodeResponse>("/auth/send-code", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function verifyLoginCode(email: string, code: string): Promise<VerifyCodeResponse> {
  return requestJson<VerifyCodeResponse>("/auth/verify-code", {
    method: "POST",
    body: JSON.stringify({ email, code }),
  });
}

export function fetchAdminConversations(debugUserEmail: string): Promise<AdminConversation[]> {
  return requestJson<AdminConversation[]>("/admin/conversations", {
    method: "GET",
    debugUserEmail,
  });
}

export function refreshKnowledgeBase(debugUserEmail: string): Promise<RefreshLibraryResponse> {
  return requestJson<RefreshLibraryResponse>("/admin/refresh-library", {
    method: "POST",
    debugUserEmail,
  });
}

export function askQuestion(options: {
  question: string;
  conversationId?: number | null;
  debugUserEmail?: string;
}): Promise<AskResponse> {
  return requestJson<AskResponse>("/chat/ask", {
    method: "POST",
    debugUserEmail: options.debugUserEmail,
    body: JSON.stringify({
      question: options.question,
      conversation_id: options.conversationId ?? null,
    }),
  });
}
