import { z } from "zod";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:4000";
const AUTH_REFRESH_URL = `${API_BASE_URL}/api/v1/auth/refresh`;

const currentUserSchema = z
  .object({
    user: z.object({
      id: z.string().min(1),
      nickname: z.string().min(1),
      favoriteTeam: z.string().nullable(),
    }),
  })
  .transform((payload) => payload.user);

export type CurrentUser = z.infer<typeof currentUserSchema>;

export type UpdateCurrentUserInput = {
  nickname: string;
  favoriteTeam: string | null;
};

export class AuthApiError extends Error {
  status: number;
  detail: string | null;

  constructor(message: string, options: { status: number; detail: string | null }) {
    super(message);
    this.name = "AuthApiError";
    this.status = options.status;
    this.detail = options.detail;
  }
}

export function startGoogleOAuth() {
  window.location.assign(`${API_BASE_URL}/api/v1/auth/google`);
}

export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const response = await fetchWithAuthRefresh(`${API_BASE_URL}/api/v1/auth/me`, {
    credentials: "include",
  });

  if (response.status === 401) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`사용자 정보를 불러오지 못했습니다. (${response.status})`);
  }

  const payload = (await response.json()) as unknown;
  return currentUserSchema.parse(payload);
}

export async function logoutCurrentUser() {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(`로그아웃에 실패했습니다. (${response.status})`);
  }
}

export async function updateCurrentUser(input: UpdateCurrentUserInput): Promise<CurrentUser> {
  const response = await fetchWithAuthRefresh(`${API_BASE_URL}/api/v1/auth/me`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new AuthApiError(`프로필을 저장하지 못했습니다. (${response.status})`, {
      status: response.status,
      detail,
    });
  }

  const payload = (await response.json()) as unknown;
  return currentUserSchema.parse(payload);
}

let refreshSessionPromise: Promise<boolean> | null = null;

export async function fetchWithAuthRefresh(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const response = await fetch(input, withCredentials(init));

  if (response.status !== 401 || isRefreshRequest(input)) {
    return response;
  }

  const refreshed = await refreshCurrentSessionOnce();
  if (!refreshed) {
    return response;
  }

  return fetch(input, withCredentials(init));
}

async function refreshCurrentSessionOnce(): Promise<boolean> {
  refreshSessionPromise ??= refreshCurrentSession().finally(() => {
    refreshSessionPromise = null;
  });

  return refreshSessionPromise;
}

async function refreshCurrentSession(): Promise<boolean> {
  const response = await fetch(AUTH_REFRESH_URL, {
    method: "POST",
    credentials: "include",
  });

  return response.ok;
}

function withCredentials(init?: RequestInit): RequestInit {
  return {
    ...init,
    credentials: init?.credentials ?? "include",
  };
}

function isRefreshRequest(input: RequestInfo | URL): boolean {
  const url = typeof input === "string" ? input : input.toString();
  return url === AUTH_REFRESH_URL;
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const payload = (await response.json()) as unknown;
    const result = z.object({ detail: z.string() }).safeParse(payload);
    return result.success ? result.data.detail : null;
  } catch {
    return null;
  }
}
