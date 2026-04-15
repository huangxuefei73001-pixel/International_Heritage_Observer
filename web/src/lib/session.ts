"use client";

export type StoredSession = {
  email: string;
  role: "user" | "admin";
};

const EMAIL_KEY = "heritage-user-email";
const ROLE_KEY = "heritage-user-role";

function buildGuestEmail(): string {
  const randomPart =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

  return `guest-${randomPart}@guest.local`;
}

export function getStoredSession(): StoredSession | null {
  if (typeof window === "undefined") {
    return null;
  }

  const email = window.localStorage.getItem(EMAIL_KEY);
  const role = window.localStorage.getItem(ROLE_KEY);
  if (!email || (role !== "user" && role !== "admin")) {
    return null;
  }

  return { email, role };
}

export function setStoredSession(session: StoredSession): StoredSession {
  window.localStorage.setItem(EMAIL_KEY, session.email);
  window.localStorage.setItem(ROLE_KEY, session.role);
  return session;
}

export function ensureGuestSession(): StoredSession {
  const stored = getStoredSession();
  if (stored) {
    return stored;
  }

  return setStoredSession({
    email: buildGuestEmail(),
    role: "user",
  });
}

export function clearStoredSession(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(EMAIL_KEY);
  window.localStorage.removeItem(ROLE_KEY);
}
