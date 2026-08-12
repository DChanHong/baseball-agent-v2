import { z } from "zod";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:4000";

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
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
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
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
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

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const payload = (await response.json()) as unknown;
    const result = z.object({ detail: z.string() }).safeParse(payload);
    return result.success ? result.data.detail : null;
  } catch {
    return null;
  }
}
