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

export type SqlLabContext = {
  database?: { id?: number; name?: string; backend?: string };
  schema?: string;
  table?: string;
  columns?: Array<{ name: string; type: string }>;
  [key: string]: unknown;
};

export type ToolCallAudit = {
  tool: string;
  argument_keys: string[];
  status: "ok" | "error";
  latency_ms: number;
};

export type Attachment = {
  id: string;
  kind: "image" | "document";
  original_filename: string;
  content_type: string;
  size_bytes: number;
};

export type Task = {
  id: string;
  title: string;
  status: string;
  provider?: string;
  model?: string;
  error?: string;
  gtf_task_uuid?: string | null;
  tool_calls?: ToolCallAudit[];
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
  mcp_enabled: boolean;
  is_admin: boolean;
};

export type AdminProvider = Provider & {
  base_url: string;
  has_api_key: boolean;
  effort_param?: string;
  enabled: boolean;
  created_on?: string;
  changed_on?: string;
};

export type AdminProviderInput = {
  label: string;
  base_url: string;
  api_key?: string;
  default_model?: string;
  models?: string[];
  capabilities?: string[];
  effort_levels?: string[];
  effort_param?: string;
  enabled?: boolean;
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

export async function getSqlLabContext(params: {
  databaseId: number;
  schema?: string;
  table?: string;
}): Promise<SqlLabContext> {
  const query = new URLSearchParams({
    database_id: String(params.databaseId),
  });
  if (params.schema) query.set("schema", params.schema);
  if (params.table) query.set("table", params.table);
  const { json } = await SupersetClient.get({
    endpoint: `${BASE}/context/sql_lab?${query.toString()}`,
  });
  return json as SqlLabContext;
}

export async function uploadAttachment(file: File): Promise<Attachment> {
  const formData = new FormData();
  formData.append("file", file);
  const { json } = await SupersetClient.post({
    endpoint: `${BASE}/attachments`,
    body: formData,
    headers: { Accept: "application/json" },
  });
  return json as Attachment;
}

export async function deleteAttachment(id: string): Promise<void> {
  await SupersetClient.delete({ endpoint: `${BASE}/attachments/${id}` });
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

export async function getAdminProviders(): Promise<AdminProvider[]> {
  const { json } = await SupersetClient.get({
    endpoint: `${BASE}/admin/providers`,
  });
  return (json as { result?: AdminProvider[] }).result ?? [];
}

export async function createAdminProvider(
  payload: AdminProviderInput,
): Promise<AdminProvider> {
  const { json } = await SupersetClient.post({
    endpoint: `${BASE}/admin/providers`,
    jsonPayload: payload,
  });
  return json as AdminProvider;
}

export async function updateAdminProvider(
  id: string,
  payload: Partial<AdminProviderInput>,
): Promise<AdminProvider> {
  const { json } = await SupersetClient.put({
    endpoint: `${BASE}/admin/providers/${id}`,
    jsonPayload: payload,
  });
  return json as AdminProvider;
}

export async function deleteAdminProvider(id: string): Promise<void> {
  await SupersetClient.delete({
    endpoint: `${BASE}/admin/providers/${id}`,
  });
}

export async function errorMessage(
  error: unknown,
  fallback: string,
): Promise<string> {
  if (error instanceof Response) {
    const payload = (await error
      .clone()
      .json()
      .catch(() => undefined)) as { message?: unknown } | undefined;
    if (typeof payload?.message === "string") return payload.message;
  }
  return error instanceof Error ? error.message : fallback;
}

export type ChatSubmission = { task_id: string; gtf_task_uuid: string };

// Chat runs as a Global Task Framework (GTF) task rather than blocking this
// request on the provider call (see superset/ai_studio/tasks.py) -- submit
// returns immediately with a pollable GTF task uuid, not the chat result.
export async function submitChat(payload: {
  provider: string;
  model?: string;
  dashboard_id?: number;
  sql_context?: {
    database_id: number;
    schema?: string;
    table?: string;
    sql?: string;
  };
  attachment_ids?: string[];
  messages: ChatMessage[];
  effort?: string;
}): Promise<ChatSubmission> {
  const { json } = await SupersetClient.post({
    endpoint: `${BASE}/chat`,
    jsonPayload: payload,
  });
  return json as ChatSubmission;
}

export type GtfTaskStatus =
  | "pending"
  | "in_progress"
  | "success"
  | "failure"
  | "aborting"
  | "aborted"
  | "timed_out";

export type GtfChatPayload = { content?: string; usage?: unknown; error?: string };

export type GtfTask = {
  uuid: string;
  status: GtfTaskStatus;
  payload: GtfChatPayload | null;
};

// Mirrors superset_core.tasks.types.TaskStatus's TERMINAL_STATES.
const GTF_TERMINAL_STATUSES = new Set<GtfTaskStatus>([
  "success",
  "failure",
  "aborted",
  "timed_out",
]);

export function isGtfTaskTerminal(status: GtfTaskStatus): boolean {
  return GTF_TERMINAL_STATUSES.has(status);
}

export async function getGtfTask(uuid: string): Promise<GtfTask> {
  const { json } = await SupersetClient.get({
    endpoint: `/api/v1/task/${uuid}`,
  });
  return (json as { result: GtfTask }).result;
}

export async function cancelGtfTask(uuid: string): Promise<void> {
  await SupersetClient.post({
    endpoint: `/api/v1/task/${uuid}/cancel`,
    jsonPayload: {},
  });
}

/**
 * Poll a single GTF task until it reaches a terminal state, or `shouldStop()`
 * returns true (e.g. the caller cancelled or the drawer closed). One task at
 * a time is all AI Studio's chat pane ever needs, so this is a plain
 * fixed-interval loop rather than the dashboard's shared multi-task/websocket
 * subscription machinery (src/middleware/asyncEvent.ts), which is built for
 * many concurrent chart-data tasks and a Redux store this component doesn't
 * have.
 */
export async function pollGtfTaskUntilTerminal(
  uuid: string,
  options: { intervalMs?: number; shouldStop?: () => boolean } = {},
): Promise<GtfTask> {
  const { intervalMs = 1000, shouldStop = () => false } = options;
  for (;;) {
    const current = await getGtfTask(uuid);
    if (isGtfTaskTerminal(current.status) || shouldStop()) return current;
    // eslint-disable-next-line no-await-in-loop
    await new Promise((resolve) => {
      window.setTimeout(resolve, intervalMs);
    });
  }
}
