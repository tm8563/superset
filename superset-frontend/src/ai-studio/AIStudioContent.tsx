import { css } from "@apache-superset/core/theme";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { useSelector, shallowEqual } from "react-redux";
import type { QueryEditor, Table as SqlLabTable } from "src/SqlLab/types";
import { store, type RootState } from "src/views/store";
import type { AIStudioSection } from "./index";
import ModelPicker from "./ModelPicker";
import {
  applyChange,
  type Attachment,
  cancelGtfTask,
  type Change,
  type ChatMessage,
  type DashboardContext,
  deleteAttachment,
  errorMessage,
  getChanges,
  getDashboardContext,
  getSqlLabContext,
  getStudioBootstrap,
  getTasks,
  type MCPTool,
  pollGtfTaskUntilTerminal,
  type Provider,
  rejectChange,
  type SqlLabContext,
  submitChat,
  type StudioBootstrap,
  type Task,
  type ToolCallAudit,
  uploadAttachment,
} from "./api";
import ProviderAdmin from "./ProviderAdmin";

type Props = {
  section: AIStudioSection;
  onSectionChange: (section: AIStudioSection) => void;
  onClose: () => void;
  onOpenPalette: () => void;
  onNotify: (message: string) => void;
  variant: "dashboard" | "sqllab";
};

type DisplayMessage = ChatMessage & { toolCalls?: ToolCallAudit[] };

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
  transition:
    transform 120ms ease,
    filter 120ms ease;

  &:hover:not(:disabled) {
    filter: brightness(1.08);
  }
  &:active:not(:disabled) {
    transform: scale(0.97);
  }
  &:focus-visible {
    outline: 2px solid #6ea8ff;
    outline-offset: 2px;
  }
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
  transition:
    background 120ms ease,
    border-color 120ms ease;

  &:hover {
    border-color: rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.08);
  }
  &:focus-visible {
    outline: 2px solid #6ea8ff;
    outline-offset: 2px;
  }
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
  transition:
    background 120ms ease,
    border-color 120ms ease,
    transform 120ms ease;

  &:hover {
    border-color: rgba(110, 168, 255, 0.35);
    background: rgba(110, 168, 255, 0.12);
  }
  &:active {
    transform: scale(0.94);
  }
  &:focus-visible {
    outline: 2px solid #6ea8ff;
    outline-offset: 2px;
  }
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

/** A slim, dark-panel-appropriate scrollbar -- the OS default is a light,
 * boxy control that clashes with this panel wherever content actually
 * overflows (the message list, the JSON context viewer, long tab/tool
 * lists). Firefox honors `scrollbar-*`; the pseudo-elements cover
 * Chromium/WebKit (Superset's supported browser set). */
const scrollAreaCss = css`
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.18) transparent;

  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.14);
  }
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.26);
  }
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

function pickDefaultProvider(providers: Provider[]) {
  return providers.find((item) => item.configured) ?? providers[0];
}

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

type ActiveSqlContext = {
  databaseId: number;
  schema?: string;
  table?: string;
  sql: string;
};

/** A useSelector-shaped reader of SQL Lab's own Redux slice for whichever
 * query editor tab is currently focused -- the same tabHistory-last-entry
 * convention SQL Lab's own components use (see e.g. SqlEditorTabs) --
 * merging in `unsavedQueryEditor` the way `getUpToDateQuery` does, so an
 * in-progress edit (a schema switch, new SQL text) is reflected even before
 * it's persisted. Selector shape (not a plain store.getState() read) so the
 * panel re-renders as the user switches tabs or types, the same way any
 * other SQL Lab component would. Returns undefined once there's no
 * connected database to report, which is a real, common state (a brand new,
 * empty tab). */
function selectActiveSqlLabContext(state: RootState): ActiveSqlContext | undefined {
  const { sqlLab } = state;
  const activeId = sqlLab.tabHistory[sqlLab.tabHistory.length - 1];
  if (!activeId) return undefined;
  const base = sqlLab.queryEditors.find(
    (editor: QueryEditor) => editor.id === activeId,
  );
  const unsaved =
    sqlLab.unsavedQueryEditor.id === activeId
      ? sqlLab.unsavedQueryEditor
      : undefined;
  const merged = { ...base, ...unsaved };
  if (!merged.dbId) return undefined;
  // A Table's own queryEditorId is written as tabViewId ?? id (see addTable
  // in src/SqlLab/actions/sqlLab.ts) -- tabViewId is assigned asynchronously
  // once the tab is persisted server-side, so matching on the plain local
  // id alone silently stops finding any table opened after that point.
  const tableOwnerId = merged.tabViewId ?? activeId;
  const activeTable = sqlLab.tables.find(
    (item: SqlLabTable) => item.queryEditorId === tableOwnerId && item.expanded,
  );
  return {
    databaseId: merged.dbId,
    schema: merged.schema || activeTable?.schema,
    table: activeTable?.name,
    sql: merged.sql || "",
  };
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

function ToolCallTrail({ calls }: { calls: ToolCallAudit[] }) {
  return (
    <div
      css={css`
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        margin-top: 8px;
      `}
    >
      {calls.map((call, index) => (
        <span
          key={`${call.tool}-${index}`}
          title={
            call.argument_keys.length
              ? `Called with: ${call.argument_keys.join(", ")}`
              : "Called with no arguments"
          }
          css={css`
            display: inline-flex;
            align-items: center;
            gap: 4px;
            border: 1px solid
              ${call.status === "ok"
                ? "rgba(67, 216, 158, 0.22)"
                : "rgba(255, 113, 136, 0.22)"};
            border-radius: 999px;
            background: ${call.status === "ok"
              ? "rgba(67, 216, 158, 0.08)"
              : "rgba(255, 113, 136, 0.08)"};
            color: ${call.status === "ok" ? "#8fe6bc" : "#ff9dad"};
            font-size: 9px;
            padding: 3px 8px;
            white-space: nowrap;
          `}
        >
          <span aria-hidden="true">{call.status === "ok" ? "🔧" : "⚠"}</span>
          {call.tool}
          <span css={css`opacity: 0.65;`}>{call.latency_ms}ms</span>
        </span>
      ))}
    </div>
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
            {!!task.tool_calls?.length && <ToolCallTrail calls={task.tool_calls} />}
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
                ${scrollAreaCss};
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

function ContextPanel({
  variant,
  context,
  sqlContext,
}: {
  variant: "dashboard" | "sqllab";
  context?: DashboardContext;
  sqlContext?: SqlLabContext;
}) {
  const payload = variant === "sqllab" ? sqlContext : context;
  if (!payload)
    return (
      <EmptyState
        title={
          variant === "sqllab" ? "No database selected yet" : "No dashboard context"
        }
        detail={
          variant === "sqllab"
            ? "Pick a database (and optionally a table) in SQL Lab's left panel to attach its metadata."
            : "Open a dashboard to attach its metadata, charts, and filters."
        }
      />
    );
  return (
    <pre
      css={css`
        ${panelCss};
        ${scrollAreaCss};
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
      {JSON.stringify(payload, null, 2)}
    </pre>
  );
}

function SettingsPanel({
  safeMode,
  variant,
}: {
  safeMode?: boolean;
  variant: "dashboard" | "sqllab";
}) {
  const rows = [
    [
      "Require approval before writes",
      "Never let the agent mutate Superset silently",
      true,
    ],
    [
      "Auto-run read-only tools",
      variant === "sqllab"
        ? "Allow database and table inspection without confirmation"
        : "Allow dashboard inspection without confirmation",
      true,
    ],
    [
      variant === "sqllab" ? "SQL Lab-aware context" : "Dashboard-aware context",
      variant === "sqllab"
        ? "Attach the active database, schema, and table to this session"
        : "Attach the active dashboard to this session",
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
  variant,
}: Props) {
  const [bootstrap, setBootstrap] = useState<StudioBootstrap>();
  const [context, setContext] = useState<DashboardContext>();
  const [sqlContext, setSqlContext] = useState<SqlLabContext>();
  const [changes, setChanges] = useState<Change[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  // The in-flight chat's GTF task uuid, so a Cancel click has something to
  // call; the ref alongside it lets the poll loop below notice a cancel
  // without re-subscribing the whole loop to state.
  const [activeGtfTaskUuid, setActiveGtfTaskUuid] = useState<string>();
  const cancelledRef = useRef(false);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState<string>();
  const [effort, setEffort] = useState<string>();
  const [pickerOpen, setPickerOpen] = useState(false);
  // Pending attachments for the *next* message -- upload-on-select, not
  // upload-on-send: each file finishes uploading (and gets a real
  // attachment id) as soon as it's chosen, independent of when/whether the
  // user actually sends. Cleared right after a message is submitted, the
  // same ephemeral, client-side-only lifecycle the rest of compose-box
  // state already has (chat history itself doesn't survive a reload either).
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [attachmentsUploading, setAttachmentsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const dashboardId = dashboardIdFromPath();
  const activeSql = useSelector(
    (state: RootState) =>
      variant === "sqllab" ? selectActiveSqlLabContext(state) : undefined,
    shallowEqual,
  );
  const refreshChanges = async () => setChanges(await getChanges());
  // Not called from the mount effect below (which loads bootstrap inline) —
  // this is only passed down to ProviderAdmin, invoked from its own
  // event-driven save/delete/toggle handlers, never from a useEffect.
  const refreshProviders = async () => {
    const value = await getStudioBootstrap();
    setBootstrap(value);
    const current = value.providers.find((item) => item.id === provider);
    // Re-pick when the provider disappeared, or it's still there but an
    // admin edit (e.g. changing the model list) left the previously
    // selected model no longer valid for it.
    if (!current || (model && !current.models.includes(model))) {
      const chosen = current ?? pickDefaultProvider(value.providers);
      setProvider(chosen?.id ?? "");
      setModel(chosen?.default_model ?? chosen?.models[0]);
    }
  };

  useEffect(() => {
    getStudioBootstrap()
      .then((value) => {
        setBootstrap(value);
        const chosen = pickDefaultProvider(value.providers);
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

  // sqlContext only ever grows more accurate (or gets replaced by a fetch
  // for a different table/schema) -- it's never reset synchronously here on
  // every render where activeSql briefly lacks a database (e.g. a fresh,
  // still-loading tab), so display sites below gate on activeSql directly
  // instead of trusting a stale sqlContext left over from a prior tab.
  useEffect(() => {
    if (!activeSql?.databaseId) return;
    getSqlLabContext({
      databaseId: activeSql.databaseId,
      schema: activeSql.schema,
      table: activeSql.table,
    })
      .then(setSqlContext)
      .catch(() => undefined);
  }, [activeSql?.databaseId, activeSql?.schema, activeSql?.table]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const activeProvider = bootstrap?.providers.find((item) => item.id === provider);
  const supportsImages = Boolean(activeProvider?.capabilities.includes("vision"));
  const acceptedAttachmentExtensions = [
    ".txt",
    ".md",
    ".csv",
    ".pdf",
    ".docx",
    ...(supportsImages ? [".png", ".jpg", ".jpeg", ".gif", ".webp"] : []),
  ].join(",");

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
    const attachmentIds = attachments.map((item) => item.id);
    setAttachments([]);
    cancelledRef.current = false;
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    try {
      const freshSql = variant === "sqllab" ? activeSql : undefined;
      const submission = await submitChat({
        provider,
        model,
        dashboard_id: dashboardId,
        sql_context: freshSql && {
          database_id: freshSql.databaseId,
          schema: freshSql.schema,
          table: freshSql.table,
          sql: freshSql.sql,
        },
        attachment_ids: attachmentIds.length ? attachmentIds : undefined,
        messages: next.map(({ role, content }) => ({ role, content })),
        effort: activeProvider?.effort_levels?.length ? effort : undefined,
      });
      setActiveGtfTaskUuid(submission.gtf_task_uuid);
      getTasks()
        .then(setTasks)
        .catch(() => undefined);
      const finished = await pollGtfTaskUntilTerminal(
        submission.gtf_task_uuid,
        { shouldStop: () => cancelledRef.current },
      );
      const latestTasks = await getTasks().catch(() => tasks);
      setTasks(latestTasks);
      if (cancelledRef.current) {
        setMessages([
          ...next,
          { role: "assistant", content: "Cancelled." },
        ]);
      } else if (finished.status === "success" && finished.payload?.content) {
        const toolCalls = latestTasks.find(
          (item) => item.id === submission.task_id,
        )?.tool_calls;
        setMessages([
          ...next,
          {
            role: "assistant",
            content: finished.payload.content,
            toolCalls: toolCalls?.length ? toolCalls : undefined,
          },
        ]);
      } else if (finished.status === "success") {
        // A genuinely different case from a provider/network failure below --
        // the request completed but the model itself returned nothing
        // (observed with small/free cloud models after a confusing,
        // error-laden tool round trip). Worth its own message rather than
        // the generic failure text, since nothing here actually broke.
        setError(
          "The assistant didn't return a response for that message. Try asking again or rephrasing it.",
        );
      } else {
        setError(
          finished.payload?.error ||
            "The request could not be completed.",
        );
      }
    } catch (reason) {
      setError(
        await errorMessage(reason, "The request could not be completed."),
      );
    } finally {
      setBusy(false);
      setActiveGtfTaskUuid(undefined);
    }
  };

  const onFilesSelected = async (fileList: FileList | null) => {
    if (!fileList?.length) return;
    setAttachmentsUploading(true);
    setError("");
    try {
      for (const file of Array.from(fileList)) {
        // eslint-disable-next-line no-await-in-loop
        const uploaded = await uploadAttachment(file);
        setAttachments((current) => [...current, uploaded]);
      }
    } catch (reason) {
      setError(await errorMessage(reason, "Could not upload that file."));
    } finally {
      setAttachmentsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const onRemoveAttachment = async (id: string) => {
    setAttachments((current) => current.filter((item) => item.id !== id));
    // The chip is already gone client-side either way; a failed cleanup
    // call just means the file is purged later by the retention sweep
    // instead of immediately -- not worth surfacing as a user-facing error.
    await deleteAttachment(id).catch(() => undefined);
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
  // activeSql is the source of truth for "is a database connected right
  // now" -- sqlContext is only ever the last successful fetch, which would
  // otherwise flash stale info from a previous tab while a new one loads.
  const sqlContextForDisplay = activeSql?.databaseId ? sqlContext : undefined;
  const chips = useMemo(
    () =>
      [
        context?.dashboard?.title,
        context?.charts?.length ? `${context.charts.length} charts` : undefined,
        sqlContextForDisplay?.database?.name,
        sqlContextForDisplay?.table
          ? `${sqlContextForDisplay.schema ? `${sqlContextForDisplay.schema}.` : ""}${sqlContextForDisplay.table}`
          : undefined,
        bootstrap?.safe_mode ? "Approval mode" : undefined,
      ].filter((value): value is string => Boolean(value)),
    [bootstrap, context, sqlContextForDisplay],
  );
  const workspaceLabel = variant === "sqllab" ? "this SQL workspace" : "this dashboard";
  const firstChecklistStep =
    variant === "sqllab"
      ? "Inspect the connected database, schema, and table metadata"
      : "Inspect dashboard layout and chart metadata";

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
              transition:
                background 120ms ease,
                color 120ms ease;

              &:hover {
                background: ${section === tab.id
                  ? "rgba(110, 168, 255, 0.14)"
                  : "rgba(255, 255, 255, 0.05)"};
                color: #dceaff;
              }
              &:focus-visible {
                outline: 2px solid #6ea8ff;
                outline-offset: -2px;
              }
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
                transition:
                  background 120ms ease,
                  border-color 120ms ease;

                &:hover {
                  border-color: rgba(110, 168, 255, 0.35);
                  background: rgba(110, 168, 255, 0.08);
                }
                &:focus-visible {
                  outline: 2px solid #6ea8ff;
                  outline-offset: 2px;
                }
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
              ${scrollAreaCss};
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
                    I’m ready to help with {workspaceLabel}, inspect live
                    Superset context, and stage changes for your approval.
                    Nothing is written without review.
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
                      firstChecklistStep,
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
                  animation: ai-studio-message-in 220ms ease both;
                  @keyframes ai-studio-message-in {
                    from {
                      opacity: 0;
                      transform: translateY(4px);
                    }
                    to {
                      opacity: 1;
                      transform: translateY(0);
                    }
                  }
                `}
              >
                {message.role === "assistant" && <div css={avatarCss}>AI</div>}
                <div
                  css={css`
                    display: flex;
                    flex-direction: column;
                    max-width: calc(100% - 40px);
                  `}
                >
                  <div
                    css={css`
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
                  {!!message.toolCalls?.length && (
                    <ToolCallTrail calls={message.toolCalls} />
                  )}
                </div>
              </div>
            ))}
            {busy && (
              <div
                css={css`
                  display: flex;
                  align-items: center;
                  gap: 10px;
                `}
              >
                <div css={avatarCss}>AI</div>
                <div
                  aria-label="AI Studio is thinking"
                  css={css`
                    display: flex;
                    gap: 4px;
                    padding: 8px 0;
                  `}
                >
                  {[0, 1, 2].map((dot) => (
                    <span
                      key={dot}
                      css={css`
                        width: 6px;
                        height: 6px;
                        border-radius: 999px;
                        background: #7fa4e0;
                        animation: ai-studio-typing-dot 1.1s ease-in-out infinite;
                        animation-delay: ${dot * 0.15}s;
                        @keyframes ai-studio-typing-dot {
                          0%,
                          60%,
                          100% {
                            opacity: 0.3;
                            transform: translateY(0);
                          }
                          30% {
                            opacity: 1;
                            transform: translateY(-3px);
                          }
                        }
                      `}
                    />
                  ))}
                </div>
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
                <span css={chipCss}>
                  {variant === "sqllab"
                    ? "No database selected yet"
                    : "No dashboard context"}
                </span>
              )}
            </div>
            {(attachments.length > 0 || attachmentsUploading) && (
              <div
                css={css`
                  display: flex;
                  flex-wrap: wrap;
                  gap: 6px;
                  margin-bottom: 7px;
                `}
              >
                {attachments.map((item) => (
                  <span
                    key={item.id}
                    css={css`
                      ${chipCss};
                      display: inline-flex;
                      align-items: center;
                      gap: 5px;
                    `}
                  >
                    {item.kind === "image" ? "🖼" : "📄"} {item.original_filename}
                    <button
                      type="button"
                      aria-label={`Remove ${item.original_filename}`}
                      onClick={() => onRemoveAttachment(item.id)}
                      css={css`
                        border: 0;
                        background: transparent;
                        color: inherit;
                        cursor: pointer;
                        font-size: 10px;
                        padding: 0;
                      `}
                    >
                      ×
                    </button>
                  </span>
                ))}
                {attachmentsUploading && (
                  <span css={chipCss}>Uploading…</span>
                )}
              </div>
            )}
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
                transition:
                  border-color 160ms ease,
                  box-shadow 160ms ease;

                &:focus-within {
                  border-color: rgba(110, 168, 255, 0.45);
                  box-shadow: 0 0 34px rgba(110, 168, 255, 0.14);
                }
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
                placeholder={
                  variant === "sqllab"
                    ? "Ask about this query, explain a table, or draft new SQL…"
                    : "Ask, edit, analyze, or build anything on this dashboard…"
                }
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
                <div
                  css={css`
                    display: flex;
                    align-items: center;
                    gap: 8px;
                  `}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept={acceptedAttachmentExtensions}
                    onChange={(event) => onFilesSelected(event.target.files)}
                    css={css`
                      display: none;
                    `}
                  />
                  <button
                    type="button"
                    aria-label="Attach a file"
                    title={
                      supportsImages
                        ? "Attach an image or document"
                        : "Attach a document (switch to a vision-capable model to attach images)"
                    }
                    disabled={attachmentsUploading}
                    onClick={() => fileInputRef.current?.click()}
                    css={css`
                      ${iconButtonCss};
                      width: 26px;
                      height: 26px;
                      font-size: 12px;
                      opacity: ${attachmentsUploading ? 0.5 : 1};
                    `}
                  >
                    📎
                  </button>
                  <span
                    css={css`
                      color: #8295ae;
                      font-size: 9px;
                    `}
                  >
                    Enter to send · Shift+Enter for newline
                  </span>
                </div>
                <div
                  css={css`
                    display: flex;
                    gap: 8px;
                  `}
                >
                  {busy && activeGtfTaskUuid && (
                    <button
                      type="button"
                      onClick={() => {
                        cancelledRef.current = true;
                        cancelGtfTask(activeGtfTaskUuid).catch(() => undefined);
                      }}
                      css={secondaryButtonCss}
                    >
                      Cancel
                    </button>
                  )}
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
          </div>
        </section>
      )}
      {section !== "chat" && (
        <section
          css={css`
            ${scrollAreaCss};
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
                detail={
                  bootstrap?.is_admin
                    ? "Add and manage AI providers below. API keys are encrypted and never sent back to the browser."
                    : "Providers are managed by an administrator; credentials never reach the browser."
                }
              />
              {bootstrap?.is_admin && (
                <ProviderAdmin onChanged={refreshProviders} />
              )}
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
                detail={
                  variant === "sqllab"
                    ? "Structured database, schema, and table metadata attached to the current AI session."
                    : "Structured dashboard metadata attached to the current AI session."
                }
              />
              <ContextPanel
                variant={variant}
                context={context}
                sqlContext={sqlContextForDisplay}
              />
            </>
          )}
          {section === "settings" && (
            <SettingsPanel safeMode={bootstrap?.safe_mode} variant={variant} />
          )}
        </section>
      )}
    </div>
  );
}
