import { lazy, Suspense, useEffect, useState } from "react";
import { matchPath, useLocation } from "react-router-dom";
import { css } from "@apache-superset/core/theme";
import { RoutePaths } from "src/views/routePaths";
import AIStudioRail from "./AIStudioRail";
import CommandPalette, { type PaletteCommand } from "./CommandPalette";
import Toast from "./Toast";

const Drawer = lazy(
  () => import(/* webpackChunkName: "AIStudio" */ "./AIStudioDrawer"),
);

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

/** Routes that mount their own scoped AIStudioScoped inline (see
 * dashboard/components/DashboardBuilder and SqlLab/components/AppLayout) —
 * this fixed-overlay entry point stays out of the way there entirely so its
 * Cmd/Ctrl+K listener and Toast don't double up with the scoped copies. */
function hasScopedMount(pathname: string) {
  // RoutePaths.DASHBOARD ('/dashboard/:idOrSlug/') matches ANY single path
  // segment there, including the literal "list" — matchPath has no notion
  // of the more specific DASHBOARD_LIST route winning first the way a
  // <Switch> would, so it must be excluded explicitly.
  if (matchPath(pathname, { path: RoutePaths.DASHBOARD_LIST, exact: true })) {
    return false;
  }
  return (
    !!matchPath(pathname, { path: RoutePaths.DASHBOARD, exact: false }) ||
    !!matchPath(pathname, { path: RoutePaths.SQLLAB, exact: false })
  );
}

export default function AIStudio() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<AIStudioSection>("chat");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [toast, setToast] = useState<{ id: number; message: string }>();

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(undefined), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const navigate = (next: AIStudioSection) => {
    setSection(next);
    setOpen(true);
  };
  const notify = (message: string) => setToast({ id: Date.now(), message });

  if (hasScopedMount(location.pathname)) return null;

  return (
    <>
      <CommandPalette
        open={paletteOpen}
        commands={paletteCommands}
        onClose={() => setPaletteOpen(false)}
        onSelect={navigate}
      />
      {toast && <Toast key={toast.id} message={toast.message} />}
      <aside
        aria-label="AI Studio navigation"
        css={css`
          position: fixed;
          z-index: 1190;
          top: 0;
          right: 0;
          display: flex;
          width: 64px;
          height: 100dvh;
          flex-direction: column;
          align-items: center;
          gap: 7px;
          padding: 10px 8px;
          border-left: 1px solid rgba(255, 255, 255, 0.08);
          background: rgba(9, 18, 32, 0.96);
          box-shadow: -12px 0 32px rgba(0, 0, 0, 0.14);
          backdrop-filter: blur(18px);
        `}
      >
        <AIStudioRail open={open} section={section} onNavigate={navigate} />
      </aside>
      {open && (
        <Suspense fallback={null}>
          <Drawer
            open={open}
            section={section}
            onSectionChange={setSection}
            onClose={() => setOpen(false)}
            onOpenPalette={() => setPaletteOpen(true)}
            onNotify={notify}
          />
        </Suspense>
      )}
    </>
  );
}
