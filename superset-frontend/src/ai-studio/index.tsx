import { type PaletteCommand } from "./CommandPalette";

export type AIStudioSection =
  "chat" | "tasks" | "changes" | "tools" | "providers" | "context" | "settings";

export const paletteCommands: PaletteCommand[] = [
  { id: "chat", icon: "✦", label: "Open AI Chat", detail: "Ask, edit, analyze, or build" },
  { id: "tasks", icon: "☑", label: "View agent tasks", detail: "Running work and history" },
  { id: "changes", icon: "⇄", label: "Review pending changes", detail: "Approve or reject staged diffs" },
  { id: "tools", icon: "⌘", label: "Browse MCP tools", detail: "Live, permission-aware tool registry" },
  { id: "providers", icon: "◉", label: "Switch AI provider", detail: "Server-configured models" },
  { id: "context", icon: "⌁", label: "Inspect dashboard context", detail: "Structured metadata attached to this session" },
  { id: "settings", icon: "⚙", label: "Open AI Studio settings", detail: "Execution and privacy posture" },
];

/** AI Studio only ever appears inline, via the separate AIStudioScoped mount
 * on Dashboard (DashboardBuilder.tsx) and SQL Lab (SqlLab/components/
 * AppLayout/index.tsx) pages. There is no floating fallback on any other
 * route -- it showed up on Superset's own list/management views (dashboard
 * list, chart list, dataset list, saved query list, etc.), which was never
 * wanted. This component stays only so views/App.tsx's existing mount point
 * doesn't need to change. */
export default function AIStudio() {
  return null;
}
