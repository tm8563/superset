import { lazy, Suspense, useEffect, useState } from "react";
import { css } from "@apache-superset/core/theme";
import AIStudioRail from "./AIStudioRail";
import CommandPalette from "./CommandPalette";
import Toast from "./Toast";
import { paletteCommands, type AIStudioSection } from "./index";

const InlinePanel = lazy(
  () => import(/* webpackChunkName: "AIStudio" */ "./AIStudioInlinePanel"),
);

const DASHBOARD_PANEL_WIDTH = 420;

type Props = {
  variant: "dashboard" | "sqllab";
};

/** Rail + panel mounted directly inside a page's own layout (Dashboard,
 * SQL Lab), as real flex/Splitter siblings rather than a fixed overlay —
 * so the page's own content visibly resizes around it. Owns its own
 * open/section/palette/toast state, independent per mount (not shared
 * across pages). See ./index for the fixed-overlay fallback used
 * everywhere else. */
export default function AIStudioScoped({ variant }: Props) {
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

  return (
    <>
      <CommandPalette
        open={paletteOpen}
        commands={paletteCommands}
        onClose={() => setPaletteOpen(false)}
        onSelect={navigate}
      />
      {toast && <Toast key={toast.id} message={toast.message} />}
      <div
        css={css`
          display: flex;
          flex-direction: row;
          height: 100%;
          flex: ${variant === "sqllab" ? "1" : "0 0 auto"};
        `}
      >
        <div
          aria-label="AI Studio navigation"
          css={css`
            display: flex;
            flex: 0 0 64px;
            flex-direction: column;
            align-items: center;
            gap: 7px;
            height: 100%;
            padding: 10px 8px;
            border-left: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(9, 18, 32, 0.96);
          `}
        >
          <AIStudioRail open={open} section={section} onNavigate={navigate} />
        </div>
        {open && (
          <Suspense fallback={null}>
            <InlinePanel
              section={section}
              onSectionChange={setSection}
              onClose={() => setOpen(false)}
              onOpenPalette={() => setPaletteOpen(true)}
              onNotify={notify}
              width={variant === "dashboard" ? DASHBOARD_PANEL_WIDTH : undefined}
              variant={variant}
            />
          </Suspense>
        )}
      </div>
    </>
  );
}
