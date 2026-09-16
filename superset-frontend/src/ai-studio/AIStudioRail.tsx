import { css } from "@apache-superset/core/theme";
import type { AIStudioSection } from "./index";

export const railItems: Array<{
  id: AIStudioSection;
  icon: string;
  label: string;
}> = [
  { id: "chat", icon: "✦", label: "Chat" },
  { id: "tasks", icon: "☑", label: "Tasks" },
  { id: "changes", icon: "⇄", label: "Changes" },
  { id: "tools", icon: "⌘", label: "MCP" },
  { id: "providers", icon: "◉", label: "Models" },
  { id: "settings", icon: "⚙", label: "Settings" },
];

type Props = {
  open: boolean;
  section: AIStudioSection;
  onNavigate: (section: AIStudioSection) => void;
};

/** Just the buttons — the caller supplies the positioned/sized wrapper
 * (fixed overlay rail vs. an inline flex column). */
export default function AIStudioRail({ open, section, onNavigate }: Props) {
  return (
    <>
      {railItems.map((item) => {
        const active = open && item.id === section;
        return (
          <button
            key={item.id}
            type="button"
            aria-label={item.id === "chat" ? "Open AI Studio" : item.label}
            aria-current={active ? "page" : undefined}
            onClick={() => onNavigate(item.id)}
            css={css`
              display: grid;
              width: 48px;
              height: 49px;
              place-items: center;
              gap: 1px;
              border: 1px solid
                ${active ? "rgba(110, 168, 255, 0.16)" : "transparent"};
              border-radius: 12px;
              background: ${active
                ? "linear-gradient(180deg, rgba(110, 168, 255, 0.2), rgba(155, 135, 245, 0.1))"
                : "transparent"};
              box-shadow: ${active
                ? "inset 0 0 0 1px rgba(110, 168, 255, 0.08)"
                : "none"};
              color: ${active ? "#ddebff" : "#8597b1"};
              cursor: pointer;
              font-size: 9px;
              transition: 160ms ease;

              &:hover {
                background: linear-gradient(
                  180deg,
                  rgba(110, 168, 255, 0.18),
                  rgba(155, 135, 245, 0.08)
                );
                color: #ddebff;
              }
              &:focus-visible {
                outline: 2px solid #6ea8ff;
                outline-offset: 2px;
              }
            `}
          >
            <b
              css={css`
                font-size: 17px;
                font-weight: 500;
              `}
            >
              {item.icon}
            </b>
            {item.label}
          </button>
        );
      })}
    </>
  );
}
