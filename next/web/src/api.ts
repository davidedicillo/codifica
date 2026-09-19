export type User = { id: string; name: string; email: string };
export type Channel = {
  id: string;
  name: string;
  ownerId: string;
  role: "owner" | "member";
  archived: boolean;
};
export type Participant = {
  id: string;
  name: string;
  kind: "human" | "agent";
  provider: string | null;
  invitedBy: string | null;
  userId: string | null;
  presence: "waiting" | "recent" | "offline";
};
export type ImageMeta = {
  kind?: "image";
  filename?: string;
  mediaType?: string;
  size?: number;
};
export type DocRef = ImageMeta & {
  docId: string;
  revision: number;
  title?: string;
  startLine?: number;
  endLine?: number;
};
export type Message = {
  id: string;
  rootMessageId: string | null;
  sequence: number;
  senderId: string;
  senderName: string;
  body: string;
  mentions: string[];
  createdAt: string;
  docRefs: DocRef[];
};
export type Doc = ImageMeta & {
  id: string;
  channelId: string;
  title: string;
  body: string;
  revision: number;
  authorId: string;
  updatedAt: string;
  startLine?: number;
  endLine?: number;
};
export type DocMeta = ImageMeta & Pick<Doc, "id" | "title" | "revision" | "updatedAt">;
export function imageUrl(channelId: string, docId: string, revision: number, download = false) {
  return `/api/v1/channels/${encodeURIComponent(channelId)}/docs/${encodeURIComponent(docId)}/content?revision=${revision}${download ? "&download=true" : ""}`;
}
export type Invite = {
  id: string;
  kind: string;
  email?: string;
  expiresAt: string;
  used: boolean;
  revoked: boolean;
};
let csrf = "";
export function setCsrf(value: string) {
  csrf = value;
}
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public currentRevision?: number,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (options.method && !["GET", "HEAD"].includes(options.method))
    headers.set("X-CSRF-Token", csrf);
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      data.message || data.detail || `Request failed (${response.status})`,
      data.currentRevision,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export const post = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const uid = () => crypto.randomUUID();
export function errorText(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}
