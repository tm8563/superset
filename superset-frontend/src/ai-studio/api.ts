import { SupersetClient } from "@superset-ui/core";

const BASE = "/api/v1/ai-studio";

export type Provider = {
  id: string;
  label: string;
  models: string[];
  default_model?: string;
  capabilities: string[];
  effort_levels: string[];
  configured: boolean;
};

export type MCPTool = {
  name: string;
  group: string;
  can_use: boolean;
};

export type DashboardContext = {
  dashboard?: { id?: number; title?: string };
  charts?: unknown[];
  [key: string]: unknown;
};

export type Task = {
  id: string;
  title: string;
  status: string;
  provider?: string;
  model?: string;
  error?: string;
};

export type Change = {
  id: string;
  title: string;
  status: string;
  resource_type: string;
  resource_id: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  rationale?: string;
};

export type StudioBootstrap = {
  safe_mode: boolean;
  providers: Provider[];
  tools: MCPTool[];
};

export type ChatMessage = { role: "user" | "assistant"; content: string };

export async function getStudioBootstrap(): Promise<StudioBootstrap> {
  const { json } = await SupersetClient.get({ endpoint: `${BASE}/bootstrap` });
  return json as StudioBootstrap;
}

export async function getDashboardContext(
  id: number,
): Promise<DashboardContext> {
  const { json } = await SupersetClient.get({
    endpoint: `${BASE}/context/dashboard/${id}`,
  });
  return json as DashboardContext;
}

export async function getChanges(): Promise<Change[]> {
  const { json } = await SupersetClient.get({ endpoint: `${BASE}/changes` });
  return (json as { result?: Change[] }).result ?? [];
}

export async function getTasks(): Promise<Task[]> {
  const { json } = await SupersetClient.get({ endpoint: `${BASE}/tasks` });
  return (json as { result?: Task[] }).result ?? [];
}

export async function applyChange(
  id: string,
): Promise<{ checkpoint_id: string }> {
  const { json } = await SupersetClient.post({
    endpoint: `${BASE}/changes/${id}/apply`,
  });
  return json as { checkpoint_id: string };
}

export async function rejectChange(id: string): Promise<Change> {
  const { json } = await SupersetClient.post({
    endpoint: `${BASE}/changes/${id}/reject`,
  });
  return json as Change;
}

export async function sendChat(payload: {
  provider: string;
  model?: string;
  dashboard_id?: number;
  messages: ChatMessage[];
  effort?: string;
}): Promise<{ content: string; usage?: unknown }> {
  const { json } = await SupersetClient.post({
    endpoint: `${BASE}/chat`,
    jsonPayload: payload,
  });
  return json as { content: string; usage?: unknown };
}
