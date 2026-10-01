// REST + SSE client for the Head of Social Media Agent API.

export interface VisualStyle {
  palette: string[];
  style_keywords: string[];
  image_tone: string;
  typography_hint: string;
  avoid: string[];
  render_style: string;
  logo_overlay?: { position: string; opacity: number; margin: number } | null;
}

export interface Brand {
  id: number;
  name: string;
  type: string;
  description: string | null;
  industry: string | null;
  website: string | null;
  language: string;
  positioning_statement: string | null;
  target_audience: unknown[];
  differentiators: unknown[];
  voice_tone: string | null;
  content_pillars: { name?: string; angle?: string }[];
  visual_style: VisualStyle | null;
}

export type BrandAssetKind =
  | "face_photo"
  | "logo"
  | "logo_dark"
  | "product_photo"
  | "reference_style";

export interface BrandAsset {
  id: number;
  brand_id: number;
  kind: BrandAssetKind;
  file_path: string;
  label: string | null;
  is_primary: boolean;
  url: string;
}

export interface Channel {
  id: number;
  brand_id: number;
  platform: string;
  handle: string;
  language: string | null;
}

export interface Plan {
  id: number;
  brand_id: number;
  period: string;
  status: string;
  theme: string | null;
  cadence: Record<string, number>;
}

export interface Media {
  filename: string;
  url: string;
}

export interface Post {
  id: number;
  brand_id: number;
  channel_id: number;
  channel: string | null;
  handle: string | null;
  scheduled_at: string | null;
  status: string;
  pillar: string | null;
  depth_hint: string | null;
  body: string | null;
  headline: string;
  media: Media[];
  published_at: string | null;
}

export interface Asset {
  id: number;
  brand_id: number;
  type: string;
  status: string;
  depth: string | null;
  body: string | null;
  media_spec: { media_type: string; creative_brief: string; position: number }[];
  media: Media[];
}

export interface Conversation {
  id: number;
  title: string;
  status: "idle" | "processing" | "error";
  updated_at: string | null;
  message_count: number;
}

export interface ChatMsg {
  id: number;
  role: "user" | "assistant";
  text: string;
  created_at: string | null;
}

export type MentionType = "brand" | "channel" | "post";
export interface Mention {
  type: MentionType;
  id: number;
}

export interface MentionCandidates {
  brands: { id: number; label: string; type: string }[];
  channels: { id: number; label: string; platform: string }[];
  posts: { id: number; label: string; status: string }[];
}

export interface Insights {
  top_posts: { post_id: number; channel: string; depth: string; pillar: string; headline: string; engagement_rate: number }[];
  bottom_posts: { post_id: number; channel: string; headline: string; engagement_rate: number }[];
  best_times: { day: string; avg_engagement_rate: number }[];
  format_performance: { depth: string; avg_engagement_rate: number }[];
  channel_notes: { channel: string; avg_engagement_rate: number }[];
}

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// Multipart upload (no JSON Content-Type header) for brand assets.
async function uploadBrandAsset(brandId: number, form: FormData): Promise<BrandAsset> {
  const res = await fetch(`${BASE}/brands/${brandId}/assets`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<BrandAsset>;
}

export const api = {
  health: () => req<{ status: string; db: boolean }>("/healthz"),

  listBrands: () => req<Brand[]>("/dashboard/brands"),
  createBrand: (body: Partial<Brand> & { name: string; type_: string }) =>
    req<Brand>("/dashboard/brands", { method: "POST", body: JSON.stringify(body) }),
  getBrand: (id: number) => req<Brand>(`/dashboard/brands/${id}`),

  listBrandAssets: (brandId: number) => req<BrandAsset[]>(`/brands/${brandId}/assets`),
  uploadBrandAsset,

  listChannels: (brandId: number) => req<Channel[]>(`/dashboard/brands/${brandId}/channels`),
  createChannel: (brandId: number, body: { platform: string; handle: string; language?: string }) =>
    req<Channel>(`/dashboard/brands/${brandId}/channels`, { method: "POST", body: JSON.stringify(body) }),

  listPlans: (brandId: number) => req<Plan[]>(`/dashboard/brands/${brandId}/plans`),
  createPlan: (brandId: number, body: Record<string, unknown>) =>
    req<Plan>(`/dashboard/brands/${brandId}/plans`, { method: "POST", body: JSON.stringify(body) }),
  fanoutPlan: (planId: number) => req<Post[]>(`/dashboard/plans/${planId}/fanout`, { method: "POST" }),

  listPosts: (brandId: number) => req<Post[]>(`/dashboard/brands/${brandId}/posts`),
  approvePost: (postId: number) => req<Post>(`/dashboard/posts/${postId}/approve`, { method: "POST" }),
  publishPost: (postId: number) => req<Post>(`/dashboard/posts/${postId}/publish`, { method: "POST" }),

  listAssets: (brandId: number) => req<Asset[]>(`/dashboard/brands/${brandId}/assets`),
  createAsset: (body: { brand_id: number; body: string; depth: string; media_spec: unknown[] }) =>
    req<Asset>("/dashboard/assets", { method: "POST", body: JSON.stringify(body) }),
  generateAsset: (assetId: number) =>
    req<{ ok: boolean; asset_id: number; media: Media[] }>(`/dashboard/assets/${assetId}/generate`, {
      method: "POST",
    }),

  insights: (brandId: number) => req<Insights>(`/dashboard/brands/${brandId}/insights`),
  history: (brandId: number) =>
    req<{ count: number; history: { period: string; channel: string; pillar: string; depth: string; headline: string; engagement_rate: number }[] }>(
      `/dashboard/brands/${brandId}/history`
    ),

  // --- Chat conversations ---
  listConversations: () => req<Conversation[]>("/chat/conversations"),
  createConversation: () => req<{ id: number; title: string; status: string }>("/chat/conversations", {
    method: "POST",
  }),
  deleteConversation: (id: number) => req<{ ok: boolean }>(`/chat/conversations/${id}`, { method: "DELETE" }),
  getMessages: (id: number) => req<ChatMsg[]>(`/chat/conversations/${id}/messages`),
  searchMentions: (q: string) => req<MentionCandidates>(`/chat/mentions?q=${encodeURIComponent(q)}`),
  stopConversation: (id: number) =>
    req<{ ok: boolean; stopped: boolean }>(`/chat/conversations/${id}/stop`, { method: "POST" }),
};

// One event from the chat SSE stream (see services/chat_service.py `stream`).
export type ChatEventType = "status" | "agent" | "tool" | "token" | "error" | "done" | "message";
export interface ChatEvent {
  type: ChatEventType;
  text?: string;
  state?: "thinking" | "idle";
  name?: string;
  status?: "start" | "done";
  summary?: string;
  message?: string;
  retryable?: boolean;
  message_id?: number | null;
  stopped?: boolean;
  has_error?: boolean;
}

// POST an SSE chat stream (send or retry) and invoke onEvent per frame; resolves at stream end.
export async function streamChat(
  path: string,
  body: unknown,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`chat stream failed: ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const eventLine = frame.split("\n").find((l) => l.startsWith("event:"));
      const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
      const type = (eventLine ? eventLine.slice(6).trim() : "message") as ChatEventType;
      let payload: Record<string, unknown> = {};
      if (dataLine) {
        try {
          payload = JSON.parse(dataLine.slice(5).trim());
        } catch {
          /* ignore malformed frame */
        }
      }
      onEvent({ type, ...payload } as ChatEvent);
    }
  }
}