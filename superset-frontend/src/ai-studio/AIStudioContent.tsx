import { css } from "@apache-superset/core/theme";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { store } from "src/views/store";
import type { AIStudioSection } from "./index";
import ModelPicker from "./ModelPicker";
import {
  applyChange,
  type Change,
  type ChatMessage,
  type DashboardContext,
  getChanges,
  getDashboardContext,
  getStudioBootstrap,
  getTasks,
  type MCPTool,
  rejectChange,
  sendChat,
  type StudioBootstrap,
  type Task,
} from "./api";

type Props = {
  section: AIStudioSection;
  onSectionChange: (section: AIStudioSection) => void;
  onClose: () => void;
  onOpenPalette: () => void;
  onNotify: (message: string) => void;
};

const tabs: Array<{ id: AIStudioSection; label: string }> = [
  { id: "chat", label: "Chat" },
  { id: "tasks", label: "Agent Tasks" },
  { id: "changes", label: "Changes" },
  { id: "tools", label: "MCP Tools" },
  { id: "providers", label: "Providers" },
  { id: "context", label: "Context" },
  { id: "settings", label: "Settings" },
];

const panelCss = css`
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 13px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.035),
    rgba(255, 255, 255, 0.018)
  );
`;

const primaryButtonCss = css`
  height: 31px;
  border: 1px solid #639cf2;
  border-radius: 8px;
  background: linear-gradient(180deg, #4f8df0, #356fd0);
  color: #fff;
  cursor: pointer;
  font-size: 10px;
  padding: 0 10px;
`;

const secondaryButtonCss = css`
  height: 31px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: #d6e2f2;
  cursor: pointer;
  font-size: 10px;
  padding: 0 10px;
`;

const iconButtonCss = css`
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.035);
  color: #dceaff;
  cursor: pointer;
`;

const avatarCss = css`
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 10px;
  background: linear-gradient(135deg, #6ea8ff, #8476ff);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
`;

const chipCss = css`
  flex: 0 0 auto;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.035);
  color: #9db0c9;
  font-size: 9px;
  padding: 5px 8px;
  white-space: nowrap;
`;

function dashboardIdFromPath() {
  const { pathname } = window.location;
  if (!/\/dashboard\//.test(pathname)) return undefined;
  // Numeric URLs carry the id directly; slug URLs (the common case in this
  // deployment, e.g. /dashboard/hsc-manhours-overview/) don't, so fall back
  // to the id Superset's own dashboard page already resolved into the
  // shared app store rather than re-resolving the slug ourselves.
  const numericMatch = pathname.match(/\/dashboard\/(\d+)/);
  if (numericMatch) return Number(numericMatch[1]);
  const id = store.getState().dashboardInfo?.id;
  return typeof id === "number" ? id : undefined;
}

async function errorMessage(error: unknown, fallback: string) {
  if (error instanceof Response) {
    const payload = (await error
      .clone()
      .json()
      .catch(() => undefined)) as { message?: unknown } | undefined;
    if (typeof payload?.message === "string") return payload.message;
  }
  return error instanceof Error ? error.message : fallback;
}

type DiffRow = { key: string; before?: string; after?: string };

function formatDiffValue(value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > 160 ? `${text.slice(0, 160)}…` : text;
}

function diffRows(
  before: Record<string, unknown>,
  after: Record<string, unknown>,
): DiffRow[] {
  const keys = [
    ...new Set([...Object.keys(before), ...Object.keys(after)]),
  ].sort();
  return keys
    .filter((key) => JSON.stringify(before[key]) !== JSON.stringify(after[key]))
    .map((key) => ({
      key,
      before: key in before ? formatDiffValue(before[key]) : undefined,
      after: key in after ? formatDiffValue(after[key]) : undefined,
    }));
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div
      css={css`
        padding: 26px 8px;
        color: #8fa2bd;
        text-align: center;
      `}
    >
      <strong
        css={css`
          display: block;
          margin-bottom: 6px;
          color: #eaf3ff;
        `}
      >
        {title}
      </strong>
      <span
        css={css`
          font-size: 11px;
          line-height: 1.55;
        `}
      >
        {detail}
      </span>
    </div>
  );
}

function SectionHero({ title, detail }: { title: string; detail: string }) {
  return (
    <div
      css={css`
        margin-bottom: 12px;
        padding: 14px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        background: linear-gradient(
          135deg,
          rgba(110, 168, 255, 0.12),
          rgba(155, 135, 245, 0.05)
        );
      `}
    >
      <h2
        css={css`
          margin: 0 0 5px;
          color: #eef4ff;
          font-size: 16px;
        `}
      >
        {title}
      </h2>
      <p
        css={css`
          margin: 0;
          color: #8fa2bd;
          font-size: 11px;
          line-height: 1.5;
        `}
      >
        {detail}
      </p>
    </div>
  );
}

function StatusBadge({
  children,
  tone = "green",
}: {
  children: ReactNode;
  tone?: "green" | "amber" | "red";
}) {
  const colors = {
    green: ["rgba(67, 216, 158, 0.1)", "rgba(67, 216, 158, 0.22)", "#71e3b0"],
    amber: ["rgba(255, 200, 87, 0.1)", "rgba(255, 200, 87, 0.22)", "#ffd479"],
    red: ["rgba(255, 113, 136, 0.1)", "rgba(255, 113, 136, 0.22)", "#ff9dad"],
  } as const;
  const [background, border, color] = colors[tone];
  return (
    <span
      css={css`
        border: 1px solid ${border};
        border-radius: 999px;
        background: ${background};
        color: ${color};
        font-size: 8px;
        letter-spacing: 0.04em;
        padding: 3px 6px;
        white-space: nowrap;
      `}
    >
      {children}
    </span>
  );
}

function TaskMetrics({ tasks }: { tasks: Task[] }) {
  const running = tasks.filter(
    (task) => task.status === "queued" || task.status === "running",
  ).length;
  const completed = tasks.filter((task) => task.status === "completed").length;
  const failed = tasks.filter((task) => task.status === "failed").length;
  return (
    <div
      css={css`
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-bottom: 12px;
      `}
    >
      {(
        [
          ["Running", running],
          ["Completed", completed],
          ["Failed", failed],
        ] as const
      ).map(([label, value]) => (
        <div
          key={label}
          css={css`
            ${panelCss};
            padding: 10px;
          `}
        >
          <b
            css={css`
              display: block;
              color: #eef4ff;
              font-size: 18px;
            `}
          >
            {value}
          </b>
          <span
            css={css`
              display: block;
              margin-top: 3px;
              color: #8194ae;
              font-size: 9px;
            `}
          >
            {label}
          </span>
        </div>
      ))}
    </div>
  );
}

function TaskProgress({ status }: { status: string }) {
  const inProgress = status === "queued" || status === "running";
  const fill =
    status === "failed"
      ? "linear-gradient(90deg, #ff7188, #d94f68)"
      : status === "completed"
        ? "linear-gradient(90deg, #43d89e, #2fae7c)"
        : "linear-gradient(90deg, #6ea8ff, #9b87f5)";
  return (
    <div
      css={css`
        height: 4px;
        margin-top: 9px;
        overflow: hidden;
        border-radius: 999px;
        background: #1a2840;
      `}
    >
      <i
        css={css`
          display: block;
          width: ${inProgress ? "40%" : "100%"};
          height: 100%;
          background: ${fill};
          animation: ${inProgress
            ? "ai-studio-task-progress 1.3s ease-in-out infinite"
            : "none"};
          @keyframes ai-studio-task-progress {
            0% {
              margin-left: 0%;
            }
            50% {
              margin-left: 58%;
            }
            100% {
              margin-left: 0%;
            }
          }
        `}
      />
    </div>
  );
}

function TaskList({ tasks }: { tasks: Task[] }) {
  if (!tasks.length)
    return (
      <EmptyState
        title="No agent tasks yet"
        detail="Requests and staged work appear here as they run."
      />
    );
  return (
    <div>
      <TaskMetrics tasks={tasks} />
      {tasks.map((task) => {
        const tone =
          task.status === "failed"
            ? "red"
            : task.status === "completed"
              ? "green"
              : "amber";
        return (
          <article
            key={task.id}
            css={css`
              ${panelCss};
              margin-bottom: 8px;
              padding: 11px;
            `}
          >
            <div
              css={css`
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 10px;
              `}
            >
              <div>
                <div
                  css={css`
                    color: #eaf3ff;
                    font-size: 11px;
                    font-weight: 700;
                  `}
                >
                  {task.title}
                </div>
                <div
                  css={css`
                    margin-top: 4px;
                    color: #8295ae;
                    font-size: 9px;
                  `}
                >
                  {task.provider || "No provider"}
                  {task.model ? ` · ${task.model}` : ""}
                </div>
              </div>
              <StatusBadge tone={tone}>{task.status.toUpperCase()}</StatusBadge>
            </div>
            {task.error && (
              <p
                css={css`
                  margin: 8px 0 0;
                  color: #ff9dad;
                  font-size: 10px;
                `}
              >
                {task.error}
              </p>
            )}
            <TaskProgress status={task.status} />
          </article>
        );
      })}
    </div>
  );
}

function ChangeList({
  changes,
  onApply,
  onReject,
}: {
  changes: Change[];
  onApply: (id: string) => void;
  onReject: (id: string) => void;
}) {
  if (!changes.length)
    return (
      <EmptyState
        title="No staged changes"
        detail="AI proposals remain here for review before anything is applied."
      />
    );
  return (
    <div>
      {changes.map((change) => {
        const rows = diffRows(change.before, change.after);
        return (
          <article
            key={change.id}
            css={css`
              ${panelCss};
              margin-bottom: 9px;
              overflow: hidden;
            `}
          >
            <div
              css={css`
                display: flex;
                justify-content: space-between;
                gap: 10px;
                padding: 10px;
                background: rgba(255, 255, 255, 0.025);
                color: #dceaff;
                font-size: 10px;
              `}
            >
              <strong>{change.title}</strong>
              <span
                css={css`
                  color: #8295ae;
                  white-space: nowrap;
                `}
              >
                {change.resource_type} #{change.resource_id}
              </span>
            </div>
            <div
              css={css`
                max-height: 220px;
                overflow: auto;
                background: #08111e;
                font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
                font-size: 9px;
                line-height: 1.7;
              `}
            >
              {rows.length === 0 && (
                <div
                  css={css`
                    padding: 10px;
                    color: #6c7f9b;
                  `}
                >
                  No field-level differences.
                </div>
              )}
              {rows.map((row) => (
                <div key={row.key}>
                  {row.before !== undefined && (
                    <div
                      css={css`
                        padding: 2px 10px;
                        color: #ff8c9d;
                        white-space: pre-wrap;
                        word-break: break-word;
                      `}
                    >
                      - {row.key}: {row.before}
                    </div>
                  )}
                  {row.after !== undefined && (
                    <div
                      css={css`
                        padding: 2px 10px;
                        color: #7ce3ac;
                        white-space: pre-wrap;
                        word-break: break-word;
                      `}
                    >
                      + {row.key}: {row.after}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div
              css={css`
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
                padding: 10px;
              `}
            >
              <StatusBadge tone={change.status === "pending" ? "amber" : "green"}>
                {change.status.toUpperCase()}
              </StatusBadge>
              {change.status === "pending" && (
                <div
                  css={css`
                    display: flex;
                    gap: 6px;
                  `}
                >
                  <button
                    type="button"
                    onClick={() => onReject(change.id)}
                    css={secondaryButtonCss}
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() => onApply(change.id)}
                    css={primaryButtonCss}
                  >
                    Approve & apply
                  </button>
                </div>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}

function toolGroupIcon(group: string): string {
  const key = group.toLowerCase();
  if (key.includes("dashboard")) return "📊";
  if (key.includes("chart") || key.includes("slice")) return "📈";
  if (key.includes("dataset") || key.includes("table") || key.includes("database"))
    return "🗃";
  if (key.includes("sql") || key.includes("query")) return "⌨";
  if (
    key.includes("security") ||
    key.includes("role") ||
    key.includes("user") ||
    key.includes("permission")
  )
    return "🔐";
  return "⌘";
}

function ToolRegistry({ tools }: { tools: MCPTool[] }) {
  if (!tools.length)
    return (
      <EmptyState
        title="No MCP tools registered"
        detail="The server has not exposed any tools to this workspace."
      />
    );
  const groups = [...new Set(tools.map((tool) => tool.group || "Superset"))];
  return (
    <div
      css={css`
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
      `}
    >
      {groups.map((group) => {
        const groupTools = tools.filter(
          (tool) => (tool.group || "Superset") === group,
        );
        const allowed = groupTools.filter((tool) => tool.can_use).length;
        return (
          <article
            key={group}
            css={css`
              ${panelCss};
              min-height: 118px;
              padding: 11px;
            `}
          >
            <div
              css={css`
                display: grid;
                width: 34px;
                height: 34px;
                place-items: center;
                margin-bottom: 8px;
                border-radius: 10px;
                background: rgba(110, 168, 255, 0.12);
                color: #a9c8ff;
              `}
            >
              {toolGroupIcon(group)}
            </div>
            <strong
              css={css`
                display: block;
                color: #eaf3ff;
                font-size: 11px;
              `}
            >
              {group}
            </strong>
            <p
              css={css`
                margin: 5px 0 9px;
                color: #8295ae;
                font-size: 9px;
                line-height: 1.45;
              `}
            >
              {allowed} of {groupTools.length} tools available under your role.
            </p>
            <StatusBadge>{groupTools.length} TOOLS</StatusBadge>
          </article>
        );
      })}
    </div>
  );
}

function ContextPanel({ context }: { context?: DashboardContext }) {
  if (!context)
    return (
      <EmptyState
        title="No dashboard context"
        detail="Open a dashboard to attach its metadata, charts, and filters."
      />
    );
  return (
    <pre
      css={css`
        ${panelCss};
        margin: 0;
        max-height: 100%;
        overflow: auto;
        padding: 12px;
        color: #b8c9dd;
        font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
        font-size: 10px;
        line-height: 1.55;
        white-space: pre-wrap;
      `}
    >
      {JSON.stringify(context, null, 2)}
    </pre>
  );
}

function SettingsPanel({ safeMode }: { safeMode?: boolean }) {
  const rows = [
    [
      "Require approval before writes",
      "Never let the agent mutate Superset silently",
      true,
    ],
    [
      "Auto-run read-only tools",
      "Allow dashboard inspection without confirmation",
      true,
    ],
    [
      "Dashboard-aware context",
      "Attach the active dashboard to this session",
      true,
    ],
    [
      "Show tool-call telemetry",
      "Expose provider and task status in the UI",
      false,
    ],
  ] as const;
  return (
    <>
      <SectionHero
        title="AI Studio settings"
        detail="Safety and context are enforced by the server; these controls describe the active session."
      />
      <div
        css={css`
          ${panelCss};
          overflow: hidden;
        `}
      >
        <div
          css={css`
            padding: 10px 11px;
            background: rgba(255, 255, 255, 0.025);
            color: #dceaff;
            font-size: 10px;
            font-weight: 700;
          `}
        >
          Execution {safeMode ? "· safe mode" : ""}
        </div>
        {rows.map(([title, detail, enabled]) => (
          <div
            key={title}
            css={css`
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 10px;
              padding: 10px 11px;
              border-top: 1px solid rgba(255, 255, 255, 0.05);
            `}
          >
            <div>
              <div
                css={css`
                  color: #dceaff;
                  font-size: 10px;
                `}
              >
                {title}
              </div>
              <small
                css={css`
                  display: block;
                  margin-top: 2px;
                  color: #8194ad;
                  font-size: 9px;
                `}
              >
                {detail}
              </small>
            </div>
            <span
              css={css`
                width: 34px;
                height: 19px;
                flex: 0 0 auto;
                padding: 2px;
                border-radius: 999px;
                background: ${enabled ? "#427bd6" : "#24354e"};
              `}
            >
              <i
                css={css`
                  display: block;
                  width: 15px;
                  height: 15px;
                  border-radius: 50%;
                  background: #fff;
                  transform: translateX(${enabled ? "15px" : "0"});
                `}
              />
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

function EffortSelector({
  levels,
  value,
  onChange,
}: {
  levels: string[];
  value?: string;
  onChange: (value: string | undefined) => void;
}) {
  return (
    <div
      css={css`
        display: flex;
        gap: 4px;
      `}
    >
      {levels.map((level) => (
        <button
          key={level}
          type="button"
          onClick={() => onChange(value === level ? undefined : level)}
          css={css`
            border: 1px solid
              ${value === level
                ? "rgba(110, 168, 255, 0.45)"
                : "rgba(255, 255, 255, 0.08)"};
            border-radius: 7px;
            background: ${value === level
              ? "rgba(110, 168, 255, 0.14)"
              : "rgba(255, 255, 255, 0.025)"};
            color: ${value === level ? "#dceaff" : "#9db0c9"};
            cursor: pointer;
            font-size: 9px;
            padding: 5px 8px;
            text-transform: capitalize;
          `}
        >
          {level}
        </button>
      ))}
    </div>
  );
}

export default function AIStudioContent({
  section,
  onSectionChange,
  onClose,
  onOpenPalette,
  onNotify,
}: Props) {
  const [bootstrap, setBootstrap] = useState<StudioBootstrap>();
  const [context, setContext] = useState<DashboardContext>();
  const [changes, setChanges] = useState<Change[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState<string>();
  const [effort, setEffort] = useState<string>();
  const [pickerOpen, setPickerOpen] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const dashboardId = dashboardIdFromPath();
  const refreshChanges = async () => setChanges(await getChanges());

  useEffect(() => {
    getStudioBootstrap()
      .then((value) => {
        setBootstrap(value);
        const chosen =
          value.providers.find((item) => item.configured) ?? value.providers[0];
        setProvider(chosen?.id ?? "");
        setModel(chosen?.default_model ?? chosen?.models[0]);
      })
      .catch(async (reason) =>
        setError(await errorMessage(reason, "AI Studio is unavailable.")),
      );
    refreshChanges().catch(() => undefined);
    getTasks()
      .then(setTasks)
      .catch(() => undefined);
    if (dashboardId)
      getDashboardContext(dashboardId)
        .then(setContext)
        .catch(() => undefined);
    const focusTimer = window.setTimeout(() => inputRef.current?.focus(), 180);
    return () => window.clearTimeout(focusTimer);
  }, [dashboardId]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const activeProvider = bootstrap?.providers.find((item) => item.id === provider);

  const send = async () => {
    const text = prompt.trim();
    if (!text || busy) return;
    if (!provider) {
      setError("No server-configured model is available.");
      return;
    }
    setBusy(true);
    setError("");
    setPrompt("");
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    try {
      const response = await sendChat({
        provider,
        model,
        dashboard_id: dashboardId,
        messages: next,
        effort: activeProvider?.effort_levels?.length ? effort : undefined,
      });
      setMessages([...next, { role: "assistant", content: response.content }]);
      getTasks()
        .then(setTasks)
        .catch(() => undefined);
    } catch (reason) {
      setError(
        await errorMessage(reason, "The request could not be completed."),
      );
    } finally {
      setBusy(false);
    }
  };

  const onApply = async (id: string) => {
    try {
      await applyChange(id);
      await refreshChanges();
      window.dispatchEvent(new CustomEvent("ai-studio:applied"));
      onNotify("Change applied");
    } catch (reason) {
      setError(await errorMessage(reason, "Could not apply the change."));
    }
  };
  const onReject = async (id: string) => {
    try {
      await rejectChange(id);
      await refreshChanges();
      onNotify("Change rejected");
    } catch (reason) {
      setError(await errorMessage(reason, "Could not reject the change."));
    }
  };
  const selectModel = (providerId: string, modelId: string) => {
    setProvider(providerId);
    setModel(modelId);
    setEffort(undefined);
    const label = bootstrap?.providers.find((item) => item.id === providerId)?.label;
    if (label) onNotify(`Switched to ${label} · ${modelId}`);
  };
  const chips = useMemo(
    () =>
      [
        context?.dashboard?.title,
        context?.charts?.length ? `${context.charts.length} charts` : undefined,
        bootstrap?.safe_mode ? "Approval mode" : undefined,
      ].filter((value): value is string => Boolean(value)),
    [bootstrap, context],
  );

  return (
    <div
      css={css`
        display: flex;
        height: 100%;
        width: 100%;
        flex-direction: column;
        overflow: hidden;
        color: #eef4ff;
      `}
    >
      <header
        css={css`
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 14px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        `}
      >
        <div>
          <strong
            css={css`
              font-size: 14px;
              letter-spacing: -0.02em;
            `}
          >
            AI Studio
          </strong>
          <span
            css={css`
              margin-left: 7px;
              color: ${bootstrap?.safe_mode ? "#71e3b0" : "#ffd479"};
              font-size: 10px;
            `}
          >
            ●{" "}
            {bootstrap?.safe_mode
              ? "Safe mode · staged writes"
              : "Approval mode"}
          </span>
        </div>
        <div
          css={css`
            display: flex;
            gap: 5px;
          `}
        >
          <button
            type="button"
            aria-label="New AI Studio chat"
            onClick={() => {
              setMessages([]);
              onSectionChange("chat");
              onNotify("New AI Studio session started");
            }}
            css={iconButtonCss}
          >
            ＋
          </button>
          <button
            type="button"
            aria-label="Open command palette"
            onClick={onOpenPalette}
            css={iconButtonCss}
          >
            ⌘
          </button>
          <button
            type="button"
            aria-label="Close AI Studio"
            onClick={onClose}
            css={iconButtonCss}
          >
            ×
          </button>
        </div>
      </header>
      <nav
        aria-label="AI Studio sections"
        css={css`
          display: flex;
          gap: 6px;
          overflow-x: auto;
          padding: 9px 12px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        `}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            aria-label={tab.label}
            aria-current={section === tab.id ? "page" : undefined}
            onClick={() => onSectionChange(tab.id)}
            css={css`
              flex: 0 0 auto;
              border: 0;
              border-radius: 8px;
              background: ${section === tab.id ? "rgba(110, 168, 255, 0.14)" : "transparent"};
              color: ${section === tab.id ? "#dceaff" : "#8294ad"};
              cursor: pointer;
              font-size: 11px;
              padding: 7px 9px;
            `}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      {error && (
        <div
          role="alert"
          css={css`
            margin: 10px 12px 0;
            border: 1px solid rgba(255, 113, 136, 0.2);
            border-radius: 10px;
            background: rgba(255, 113, 136, 0.09);
            color: #ffbdc8;
            font-size: 11px;
            padding: 9px 10px;
          `}
        >
          {error}
        </div>
      )}
      {section === "chat" && (
        <section
          css={css`
            position: relative;
            display: flex;
            min-height: 0;
            flex: 1;
            flex-direction: column;
          `}
        >
          <div
            css={css`
              padding: 10px 12px;
              border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            `}
          >
            <button
              type="button"
              onClick={() => setPickerOpen(true)}
              css={css`
                display: flex;
                align-items: center;
                gap: 6px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 9px;
                background: rgba(255, 255, 255, 0.03);
                color: #dceaff;
                cursor: pointer;
                font-size: 10px;
                padding: 7px 10px;
                max-width: 100%;
              `}
            >
              <span>◉</span>
              <span
                css={css`
                  overflow: hidden;
                  text-overflow: ellipsis;
                  white-space: nowrap;
                `}
              >
                {activeProvider
                  ? `${activeProvider.label}${model ? ` · ${model}` : ""}`
                  : "Select a model"}
              </span>
              <span
                css={css`
                  color: #7f93af;
                `}
              >
                ▾
              </span>
            </button>
          </div>
          {pickerOpen && (
            <ModelPicker
              providers={bootstrap?.providers ?? []}
              selectedProviderId={provider}
              selectedModel={model}
              onSelect={selectModel}
              variant="overlay"
              onCloseOverlay={() => setPickerOpen(false)}
            />
          )}
          <div
            aria-live="polite"
            css={css`
              flex: 1;
              overflow: auto;
              padding: 14px;
            `}
          >
            {!messages.length && (
              <>
                <div
                  css={css`
                    display: flex;
                    gap: 10px;
                    margin-bottom: 14px;
                  `}
                >
                  <div css={avatarCss}>AI</div>
                  <div
                    css={css`
                      max-width: calc(100% - 40px);
                      color: #cbd7e7;
                      font-size: 12px;
                      line-height: 1.55;
                    `}
                  >
                    I’m ready to analyze this dashboard, inspect live Superset
                    context, and stage changes for your approval. Nothing is
                    written without review.
                  </div>
                </div>
                <div
                  css={css`
                    ${panelCss};
                    margin-left: 40px;
                    overflow: hidden;
                  `}
                >
                  <div
                    css={css`
                      display: flex;
                      justify-content: space-between;
                      padding: 10px 12px;
                      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                      color: #dceaff;
                      font-size: 11px;
                    `}
                  >
                    <span>Workspace context</span>
                    <StatusBadge>
                      {bootstrap?.safe_mode ? "SAFE MODE" : "REVIEW"}
                    </StatusBadge>
                  </div>
                  <div
                    css={css`
                      padding: 7px;
                    `}
                  >
                    {[
                      "Inspect dashboard layout and chart metadata",
                      "Use only role-permitted MCP tools",
                      "Stage a diff for every write",
                    ].map((step, index) => (
                      <div
                        key={step}
                        css={css`
                          display: flex;
                          justify-content: space-between;
                          gap: 10px;
                          padding: 8px 9px;
                          color: #aebed3;
                          font-size: 10px;
                        `}
                      >
                        <span>{step}</span>
                        <span
                          css={css`
                            color: ${index < 2 ? "#71e3b0" : "#ffd479"};
                          `}
                        >
                          {index < 2 ? "✓ ready" : "review"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                css={css`
                  display: flex;
                  gap: 10px;
                  justify-content: ${message.role === "user" ? "flex-end" : "flex-start"};
                  margin-bottom: 15px;
                `}
              >
                {message.role === "assistant" && <div css={avatarCss}>AI</div>}
                <div
                  css={css`
                    max-width: calc(100% - 40px);
                    border: ${message.role === "user" ? "1px solid rgba(110, 168, 255, 0.16)" : "0"};
                    border-radius: ${message.role === "user" ? "12px" : "0"};
                    background: ${message.role === "user" ? "rgba(110, 168, 255, 0.1)" : "transparent"};
                    color: ${message.role === "user" ? "#e8f1ff" : "#cbd7e7"};
                    font-size: 12px;
                    line-height: 1.55;
                    padding: ${message.role === "user" ? "9px 11px" : "2px 0"};
                    white-space: pre-wrap;
                  `}
                >
                  {message.content}
                </div>
              </div>
            ))}
            {busy && (
              <div
                css={css`
                  color: #8fa2bd;
                  font-size: 11px;
                `}
              >
                AI Studio is thinking…
              </div>
            )}
          </div>
          <div
            css={css`
              border-top: 1px solid rgba(255, 255, 255, 0.08);
              padding: 10px 12px;
            `}
          >
            <div
              css={css`
                display: flex;
                gap: 6px;
                overflow-x: auto;
                margin-bottom: 7px;
              `}
            >
              {chips.length ? (
                chips.map((chip) => (
                  <span key={chip} css={chipCss}>
                    ⌁ {chip}
                  </span>
                ))
              ) : (
                <span css={chipCss}>No dashboard context</span>
              )}
            </div>
            {activeProvider && (activeProvider.effort_levels?.length ?? 0) > 0 && (
              <div
                css={css`
                  display: flex;
                  align-items: center;
                  gap: 6px;
                  margin-bottom: 7px;
                `}
              >
                <span
                  css={css`
                    color: #7f93af;
                    font-size: 9px;
                  `}
                >
                  Effort
                </span>
                <EffortSelector
                  levels={activeProvider.effort_levels ?? []}
                  value={effort}
                  onChange={setEffort}
                />
              </div>
            )}
            <div
              css={css`
                border: 1px solid rgba(110, 168, 255, 0.2);
                border-radius: 13px;
                background: rgba(255, 255, 255, 0.025);
                padding: 8px;
                box-shadow: 0 0 30px rgba(110, 168, 255, 0.06);
              `}
            >
              <textarea
                ref={inputRef}
                aria-label="Message AI Studio"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    send();
                  }
                }}
                placeholder="Ask, edit, analyze, or build anything on this dashboard…"
                css={css`
                  width: 100%;
                  min-height: 58px;
                  resize: none;
                  border: 0;
                  outline: none;
                  background: transparent;
                  color: #eaf3ff;
                  font: inherit;
                  font-size: 12px;
                `}
              />
              <div
                css={css`
                  display: flex;
                  align-items: center;
                  justify-content: space-between;
                `}
              >
                <span
                  css={css`
                    color: #8295ae;
                    font-size: 9px;
                  `}
                >
                  Enter to send · Shift+Enter for newline
                </span>
                <button
                  type="button"
                  onClick={send}
                  disabled={!prompt.trim() || busy}
                  css={css`
                    ${primaryButtonCss};
                    opacity: ${!prompt.trim() || busy ? 0.5 : 1};
                  `}
                >
                  Send ↵
                </button>
              </div>
            </div>
          </div>
        </section>
      )}
      {section !== "chat" && (
        <section
          css={css`
            flex: 1;
            overflow: auto;
            padding: 14px;
          `}
        >
          {section === "tasks" && (
            <>
              <SectionHero
                title="Agent tasks"
                detail="Long-running work, tool calls, retries, and task history."
              />
              <TaskList tasks={tasks} />
            </>
          )}
          {section === "changes" && (
            <>
              <SectionHero
                title="Change review"
                detail="Inspect exactly what the AI proposes before Superset is modified."
              />
              <ChangeList
                changes={changes}
                onApply={onApply}
                onReject={onReject}
              />
            </>
          )}
          {section === "tools" && (
            <>
              <SectionHero
                title="MCP tool registry"
                detail="Live, permission-aware tools available to this session."
              />
              <ToolRegistry tools={bootstrap?.tools ?? []} />
            </>
          )}
          {section === "providers" && (
            <>
              <SectionHero
                title="Provider hub"
                detail="Models are configured server-side; credentials never reach the browser."
              />
              <ModelPicker
                providers={bootstrap?.providers ?? []}
                selectedProviderId={provider}
                selectedModel={model}
                onSelect={selectModel}
                variant="embedded"
              />
            </>
          )}
          {section === "context" && (
            <>
              <SectionHero
                title="Context inspector"
                detail="Structured dashboard metadata attached to the current AI session."
              />
              <ContextPanel context={context} />
            </>
          )}
          {section === "settings" && (
            <SettingsPanel safeMode={bootstrap?.safe_mode} />
          )}
        </section>
      )}
    </div>
  );
}
