import { css } from "@apache-superset/core/theme";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Provider } from "./api";

type Category = "all" | "code" | "image" | "search";

const categories: Array<{ id: Category; label: string }> = [
  { id: "all", label: "All" },
  { id: "code", label: "Code" },
  { id: "image", label: "Image" },
  { id: "search", label: "Search" },
];

const categoryCapability: Record<Exclude<Category, "all">, string> = {
  code: "code",
  image: "vision",
  search: "search",
};

type ModelRow = {
  providerId: string;
  providerLabel: string;
  model: string;
  isDefault: boolean;
  capabilities: string[];
  configured: boolean;
  effortCapable: boolean;
};

function flattenModels(providers: Provider[]): ModelRow[] {
  return providers.flatMap((provider) => {
    const models = provider.models.length
      ? provider.models
      : provider.default_model
        ? [provider.default_model]
        : [];
    return models.map((model) => ({
      providerId: provider.id,
      providerLabel: provider.label,
      model,
      isDefault: model === provider.default_model,
      capabilities: provider.capabilities,
      configured: provider.configured,
      // Defensive: effort_levels is a newer field a not-yet-rebuilt backend
      // may not send yet, even though the type declares it required.
      effortCapable: (provider.effort_levels ?? []).length > 0,
    }));
  });
}

// Ollama's own naming convention for a locally-referenced pointer to a
// model actually served through Ollama Cloud (via the local daemon's
// stored cloud login) -- 0 MB local footprint, network-dependent, distinct
// enough from a fully local model that a "local" provider showing one is
// worth calling out rather than leaving it looking like a labeling mistake.
// The "cloud" tag shows up two ways depending on whether the model also
// carries a size variant: a bare tag (`glm-5.1:cloud`) or a size-suffixed
// one (`gpt-oss:120b-cloud`) -- both end in "cloud" preceded by either
// separator, never as part of an unrelated word, so a single suffix check
// covers both without over-matching.
function isOllamaCloudModel(model: string): boolean {
  return model.endsWith(":cloud") || model.endsWith("-cloud");
}

function providerIcon(providerLabel: string): string {
  const key = providerLabel.toLowerCase();
  if (key.includes("openai")) return "◉";
  if (key.includes("anthropic") || key.includes("claude")) return "✦";
  if (key.includes("gemini") || key.includes("google")) return "◆";
  if (key.includes("ollama")) return "○";
  if (key.includes("openrouter")) return "↗";
  return "◉";
}

function capabilityIcon(capability: string): string | undefined {
  if (capability === "vision") return "🖼";
  if (capability === "code") return "⌨";
  if (capability === "search") return "🔎";
  return undefined;
}

const rowCss = css`
  display: flex;
  width: 100%;
  align-items: center;
  gap: 10px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  padding: 9px 10px;
  text-align: left;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.035);
  }
  &:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }
`;

function ModelPickerBody({
  providers,
  selectedProviderId,
  selectedModel,
  onSelect,
}: {
  providers: Provider[];
  selectedProviderId: string;
  selectedModel?: string;
  onSelect: (providerId: string, model: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category>("all");
  const rows = useMemo(() => flattenModels(providers), [providers]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((row) => {
      if (
        category !== "all" &&
        !row.capabilities.includes(categoryCapability[category])
      )
        return false;
      if (!q) return true;
      return (
        row.model.toLowerCase().includes(q) ||
        row.providerLabel.toLowerCase().includes(q)
      );
    });
  }, [rows, query, category]);

  return (
    <>
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search models…"
        aria-label="Search models"
        css={css`
          width: 100%;
          height: 38px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 10px;
          background: rgba(255, 255, 255, 0.03);
          color: #eef4ff;
          font: inherit;
          font-size: 12px;
          outline: none;
          padding: 0 12px;
          margin-bottom: 10px;

          &:focus {
            border-color: rgba(110, 168, 255, 0.4);
          }
        `}
      />
      <div
        css={css`
          display: flex;
          gap: 6px;
          overflow-x: auto;
          margin-bottom: 10px;
        `}
      >
        {categories.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setCategory(item.id)}
            css={css`
              flex: 0 0 auto;
              border: 1px solid
                ${category === item.id
                  ? "rgba(110, 168, 255, 0.4)"
                  : "rgba(255, 255, 255, 0.08)"};
              border-radius: 8px;
              background: ${category === item.id
                ? "rgba(110, 168, 255, 0.14)"
                : "rgba(255, 255, 255, 0.025)"};
              color: ${category === item.id ? "#dceaff" : "#9db0c9"};
              cursor: pointer;
              font-size: 10px;
              padding: 6px 10px;
            `}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div
        css={css`
          display: flex;
          flex-direction: column;
          gap: 2px;
          max-height: 320px;
          overflow-y: auto;
          scrollbar-width: thin;
          scrollbar-color: rgba(255, 255, 255, 0.18) transparent;

          &::-webkit-scrollbar {
            width: 8px;
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
        `}
      >
        {filtered.length === 0 && (
          <div
            css={css`
              padding: 16px 8px;
              color: #7f93af;
              font-size: 11px;
              text-align: center;
            `}
          >
            No models match.
          </div>
        )}
        {filtered.map((row) => {
          const active =
            row.providerId === selectedProviderId && row.model === selectedModel;
          return (
            <button
              key={`${row.providerId}/${row.model}`}
              type="button"
              onClick={() => onSelect(row.providerId, row.model)}
              css={css`
                ${rowCss};
                ${active
                  ? "border-color: rgba(110, 168, 255, 0.35); background: rgba(110, 168, 255, 0.08);"
                  : ""}
              `}
            >
              <span
                css={css`
                  display: grid;
                  width: 26px;
                  height: 26px;
                  flex: 0 0 auto;
                  place-items: center;
                  border-radius: 8px;
                  background: rgba(255, 255, 255, 0.05);
                  color: #a9c8ff;
                  font-size: 12px;
                `}
              >
                {providerIcon(row.providerLabel)}
              </span>
              <span
                css={css`
                  flex: 1;
                  min-width: 0;
                `}
              >
                <span
                  css={css`
                    display: flex;
                    align-items: center;
                    gap: 5px;
                    overflow: hidden;
                  `}
                >
                  <span
                    css={css`
                      overflow: hidden;
                      color: #eaf3ff;
                      font-size: 11px;
                      text-overflow: ellipsis;
                      white-space: nowrap;
                    `}
                  >
                    {row.model}
                  </span>
                  {isOllamaCloudModel(row.model) && (
                    <span
                      title="Referenced locally, but this model actually runs on Ollama Cloud via the server's own Ollama login -- not fully local inference."
                      css={css`
                        flex: 0 0 auto;
                        border: 1px solid rgba(255, 200, 87, 0.25);
                        border-radius: 999px;
                        background: rgba(255, 200, 87, 0.1);
                        color: #ffd479;
                        font-size: 8px;
                        letter-spacing: 0.03em;
                        padding: 1px 6px;
                        white-space: nowrap;
                      `}
                    >
                      ☁ CLOUD
                    </span>
                  )}
                </span>
                <span
                  css={css`
                    display: block;
                    color: #7f93af;
                    font-size: 9px;
                  `}
                >
                  {row.providerLabel}
                </span>
              </span>
              <span
                css={css`
                  display: flex;
                  flex: 0 0 auto;
                  align-items: center;
                  gap: 4px;
                `}
              >
                {row.capabilities.map((capability) => {
                  const icon = capabilityIcon(capability);
                  return icon ? <span key={capability}>{icon}</span> : null;
                })}
                {row.effortCapable && (
                  <span
                    title="Supports reasoning effort"
                    css={css`
                      font-size: 9px;
                    `}
                  >
                    ⚙
                  </span>
                )}
                <span
                  title={row.configured ? "API key set" : "No API key set"}
                  css={css`
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    background: ${row.configured ? "#43d89e" : "#5b6b82"};
                  `}
                />
              </span>
            </button>
          );
        })}
      </div>
    </>
  );
}

type ModelPickerProps = {
  providers: Provider[];
  selectedProviderId: string;
  selectedModel?: string;
  onSelect: (providerId: string, model: string) => void;
  variant: "embedded" | "overlay";
  onCloseOverlay?: () => void;
};

export default function ModelPicker({
  providers,
  selectedProviderId,
  selectedModel,
  onSelect,
  variant,
  onCloseOverlay,
}: ModelPickerProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (variant !== "overlay") return undefined;
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCloseOverlay?.();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [variant, onCloseOverlay]);

  const body = (
    <ModelPickerBody
      providers={providers}
      selectedProviderId={selectedProviderId}
      selectedModel={selectedModel}
      onSelect={(providerId, model) => {
        onSelect(providerId, model);
        onCloseOverlay?.();
      }}
    />
  );

  if (variant === "embedded") {
    return <div>{body}</div>;
  }

  return (
    <div
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) onCloseOverlay?.();
      }}
      css={css`
        position: absolute;
        z-index: 40;
        inset: 0;
        display: flex;
        align-items: flex-end;
        justify-content: center;
        background: rgba(3, 8, 16, 0.55);
        backdrop-filter: blur(6px);
        padding: 0 14px 84px;
      `}
    >
      <div
        ref={overlayRef}
        aria-label="Select a model"
        css={css`
          width: 100%;
          max-width: 420px;
          max-height: 70%;
          overflow: hidden;
          border: 1px solid rgba(110, 168, 255, 0.22);
          border-radius: 16px;
          background: #0c1728;
          box-shadow: 0 28px 80px rgba(0, 0, 0, 0.38);
          padding: 12px;
        `}
      >
        {body}
      </div>
    </div>
  );
}
