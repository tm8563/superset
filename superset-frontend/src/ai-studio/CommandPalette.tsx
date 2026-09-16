import { css } from "@apache-superset/core/theme";
import { useEffect, useMemo, useRef, useState } from "react";
import type { AIStudioSection } from "./index";

export type PaletteCommand = {
  id: AIStudioSection;
  icon: string;
  label: string;
  detail: string;
};

type Props = {
  open: boolean;
  commands: PaletteCommand[];
  onClose: () => void;
  onSelect: (id: AIStudioSection) => void;
};

export default function CommandPalette({
  open,
  commands,
  onClose,
  onSelect,
}: Props) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter(
      (command) =>
        command.label.toLowerCase().includes(q) ||
        command.detail.toLowerCase().includes(q),
    );
  }, [commands, query]);

  useEffect(() => {
    if (!open) return undefined;
    setQuery("");
    setActiveIndex(0);
    const focusTimer = window.setTimeout(() => inputRef.current?.focus(), 30);
    return () => window.clearTimeout(focusTimer);
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  if (!open) return null;

  const choose = (command: PaletteCommand | undefined) => {
    if (!command) return;
    onSelect(command.id);
    onClose();
  };

  return (
    <div
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      css={css`
        position: fixed;
        inset: 0;
        z-index: 1200;
        display: flex;
        justify-content: center;
        padding-top: 90px;
        background: rgba(3, 8, 16, 0.6);
        backdrop-filter: blur(10px);
      `}
    >
      <dialog
        open
        aria-label="AI Studio command palette"
        css={css`
          width: 620px;
          max-width: 92vw;
          height: fit-content;
          margin: 0;
          padding: 0;
          overflow: hidden;
          border: 1px solid rgba(110, 168, 255, 0.22);
          border-radius: 16px;
          background: #0c1728;
          color: inherit;
          box-shadow: 0 28px 80px rgba(0, 0, 0, 0.38);
        `}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              onClose();
            } else if (event.key === "ArrowDown") {
              event.preventDefault();
              setActiveIndex((index) =>
                filtered.length ? (index + 1) % filtered.length : 0,
              );
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              setActiveIndex((index) =>
                filtered.length
                  ? (index - 1 + filtered.length) % filtered.length
                  : 0,
              );
            } else if (event.key === "Enter") {
              event.preventDefault();
              choose(filtered[activeIndex]);
            }
          }}
          placeholder="Type a command, page, or action…"
          aria-label="Search AI Studio commands"
          css={css`
            width: 100%;
            height: 50px;
            border: 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            background: transparent;
            color: #eef4ff;
            font: inherit;
            font-size: 13px;
            outline: none;
            padding: 0 15px;
          `}
        />
        <div
          css={css`
            max-height: 320px;
            overflow: auto;
            padding: 8px;
          `}
        >
          {filtered.length === 0 && (
            <div
              css={css`
                padding: 14px 10px;
                color: #8fa2bd;
                font-size: 11px;
              `}
            >
              No matching commands.
            </div>
          )}
          {filtered.map((command, index) => (
            <button
              key={command.id}
              type="button"
              onClick={() => choose(command)}
              onMouseEnter={() => setActiveIndex(index)}
              css={css`
                display: flex;
                width: 100%;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                border: 0;
                border-radius: 10px;
                background: ${index === activeIndex
                  ? "rgba(110, 168, 255, 0.09)"
                  : "transparent"};
                color: #eaf3ff;
                cursor: pointer;
                font-size: 11px;
                padding: 10px;
                text-align: left;
              `}
            >
              <span
                css={css`
                  display: flex;
                  align-items: center;
                  gap: 9px;
                `}
              >
                <span
                  css={css`
                    display: grid;
                    width: 22px;
                    place-items: center;
                    color: #8fa2bd;
                  `}
                >
                  {command.icon}
                </span>
                <span>
                  {command.label}
                  <span
                    css={css`
                      display: block;
                      margin-top: 2px;
                      color: #7f93af;
                      font-size: 9px;
                    `}
                  >
                    {command.detail}
                  </span>
                </span>
              </span>
              {index === activeIndex && (
                <span
                  css={css`
                    color: #7f93af;
                    font-size: 9px;
                  `}
                >
                  Enter
                </span>
              )}
            </button>
          ))}
        </div>
      </dialog>
    </div>
  );
}
