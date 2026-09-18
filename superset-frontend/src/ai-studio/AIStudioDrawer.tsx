import { css } from "@apache-superset/core/theme";
import AIStudioContent from "./AIStudioContent";
import type { AIStudioSection } from "./index";

type Props = {
  open: boolean;
  section: AIStudioSection;
  onSectionChange: (section: AIStudioSection) => void;
  onClose: () => void;
  onOpenPalette: () => void;
  onNotify: (message: string) => void;
  variant?: "dashboard" | "sqllab";
};

export default function AIStudioDrawer({
  open,
  variant = "dashboard",
  ...contentProps
}: Props) {
  if (!open) return null;
  return (
    <aside
      aria-label="AI Studio"
      css={css`
        position: fixed;
        z-index: 1180;
        top: 0;
        right: 64px;
        width: min(560px, calc(100vw - 64px));
        height: 100dvh;
        overflow: hidden;
        border-left: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(9, 18, 32, 0.97);
        box-shadow: -30px 0 80px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(26px);
        animation: ai-studio-enter 0.28s cubic-bezier(0.2, 0.8, 0.2, 1);
        @keyframes ai-studio-enter {
          from {
            opacity: 0;
            transform: translateX(28px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}
    >
      <AIStudioContent variant={variant} {...contentProps} />
    </aside>
  );
}
