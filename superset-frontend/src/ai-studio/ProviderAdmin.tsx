import { css } from "@apache-superset/core/theme";
import { useEffect, useState } from "react";
import {
  type AdminProvider,
  type AdminProviderInput,
  createAdminProvider,
  deleteAdminProvider,
  errorMessage,
  getAdminProviders,
  updateAdminProvider,
} from "./api";

const EXTRA_CAPABILITIES = [
  { id: "vision", label: "Vision" },
  { id: "code", label: "Code" },
  { id: "search", label: "Search" },
  { id: "structured_output", label: "Structured output" },
] as const;

const EFFORT_TIERS = ["low", "medium", "high", "max"] as const;

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
  height: 30px;
  border: 1px solid #639cf2;
  border-radius: 8px;
  background: linear-gradient(180deg, #4f8df0, #356fd0);
  color: #fff;
  cursor: pointer;
  font-size: 10px;
  padding: 0 12px;
  transition:
    filter 120ms ease,
    transform 120ms ease;

  &:hover:not(:disabled) {
    filter: brightness(1.08);
  }
  &:active:not(:disabled) {
    transform: scale(0.97);
  }
  &:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
  &:focus-visible {
    outline: 2px solid #6ea8ff;
    outline-offset: 2px;
  }
`;

const secondaryButtonCss = css`
  height: 28px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.04);
  color: #d6e2f2;
  cursor: pointer;
  font-size: 9px;
  padding: 0 9px;
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

const dangerButtonCss = css`
  height: 28px;
  border: 1px solid rgba(255, 113, 136, 0.25);
  border-radius: 7px;
  background: rgba(255, 113, 136, 0.06);
  color: #ff9dad;
  cursor: pointer;
  font-size: 9px;
  padding: 0 9px;
  transition:
    background 120ms ease,
    border-color 120ms ease;

  &:hover {
    border-color: rgba(255, 113, 136, 0.45);
    background: rgba(255, 113, 136, 0.14);
  }
  &:focus-visible {
    outline: 2px solid #ff9dad;
    outline-offset: 2px;
  }
`;

const fieldCss = css`
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.03);
  color: #eef4ff;
  font: inherit;
  font-size: 11px;
  outline: none;
  padding: 8px 10px;

  &:focus {
    border-color: rgba(110, 168, 255, 0.4);
  }
`;

const labelCss = css`
  display: block;
  margin-bottom: 4px;
  color: #9db0c9;
  font-size: 9px;
  letter-spacing: 0.03em;
  text-transform: uppercase;
`;

function toggleChipCss(active: boolean) {
  return css`
    border: 1px solid
      ${active ? "rgba(110, 168, 255, 0.45)" : "rgba(255, 255, 255, 0.08)"};
    border-radius: 999px;
    background: ${active
      ? "rgba(110, 168, 255, 0.16)"
      : "rgba(255, 255, 255, 0.025)"};
    color: ${active ? "#dceaff" : "#9db0c9"};
    cursor: pointer;
    font-size: 9px;
    padding: 5px 9px;
  `;
}

function Switch({
  checked,
  onChange,
  disabled,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={onChange}
      css={css`
        width: 34px;
        height: 19px;
        flex: 0 0 auto;
        padding: 2px;
        border: none;
        border-radius: 999px;
        background: ${checked ? "#427bd6" : "#24354e"};
        cursor: pointer;

        &:disabled {
          cursor: not-allowed;
          opacity: 0.6;
        }
      `}
    >
      <i
        css={css`
          display: block;
          width: 15px;
          height: 15px;
          border-radius: 50%;
          background: #fff;
          transform: translateX(${checked ? "15px" : "0"});
          transition: transform 0.12s ease;
        `}
      />
    </button>
  );
}

type FormState = {
  label: string;
  baseUrl: string;
  apiKey: string;
  defaultModel: string;
  modelsText: string;
  capabilities: string[];
  effortLevels: string[];
  effortParam: string;
  enabled: boolean;
};

const emptyForm: FormState = {
  label: "",
  baseUrl: "https://api.openai.com/v1",
  apiKey: "",
  defaultModel: "",
  modelsText: "",
  capabilities: [],
  effortLevels: [],
  effortParam: "",
  enabled: true,
};

function formFromProvider(provider: AdminProvider): FormState {
  return {
    label: provider.label,
    baseUrl: provider.base_url,
    apiKey: "",
    defaultModel: provider.default_model ?? "",
    modelsText: provider.models.join(", "),
    capabilities: provider.capabilities.filter((item) => item !== "chat"),
    effortLevels: provider.effort_levels ?? [],
    effortParam: provider.effort_param ?? "",
    enabled: provider.enabled,
  };
}

function toPayload(form: FormState): AdminProviderInput {
  return {
    label: form.label.trim(),
    base_url: form.baseUrl.trim(),
    api_key: form.apiKey.trim() || undefined,
    default_model: form.defaultModel.trim() || undefined,
    models: form.modelsText
      .split(/[,\n]/)
      .map((item) => item.trim())
      .filter(Boolean),
    capabilities: ["chat", ...form.capabilities],
    effort_levels: form.effortLevels,
    effort_param: form.effortLevels.length
      ? form.effortParam.trim() || undefined
      : undefined,
    enabled: form.enabled,
  };
}

export default function ProviderAdmin({
  onChanged,
}: {
  onChanged: () => void;
}) {
  const [providers, setProviders] = useState<AdminProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<string | "new" | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const load = () =>
    getAdminProviders()
      .then((rows) => {
        setProviders(rows);
        setLoading(false);
      })
      .catch(async (reason) => {
        setError(await errorMessage(reason, "Could not load providers."));
        setLoading(false);
      });

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startCreate = () => {
    setForm(emptyForm);
    setEditingId("new");
    setError("");
  };
  const startEdit = (provider: AdminProvider) => {
    setForm(formFromProvider(provider));
    setEditingId(provider.id);
    setError("");
  };
  const cancelEdit = () => {
    setEditingId(null);
    setForm(emptyForm);
  };

  const submit = async () => {
    if (!form.label.trim() || !form.baseUrl.trim()) {
      setError("Label and base URL are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const payload = toPayload(form);
      if (editingId === "new") {
        await createAdminProvider(payload);
      } else if (editingId) {
        await updateAdminProvider(editingId, payload);
      }
      await load();
      onChanged();
      cancelEdit();
    } catch (reason) {
      setError(await errorMessage(reason, "Could not save this provider."));
    } finally {
      setSaving(false);
    }
  };

  const toggleEnabled = async (provider: AdminProvider) => {
    setBusyId(provider.id);
    try {
      await updateAdminProvider(provider.id, { enabled: !provider.enabled });
      await load();
      onChanged();
    } catch (reason) {
      setError(await errorMessage(reason, "Could not update this provider."));
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (provider: AdminProvider) => {
    setConfirmDeleteId(null);
    setBusyId(provider.id);
    try {
      await deleteAdminProvider(provider.id);
      await load();
      onChanged();
    } catch (reason) {
      setError(await errorMessage(reason, "Could not remove this provider."));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div
      css={css`
        margin-bottom: 14px;
      `}
    >
      <div
        css={css`
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 8px;
        `}
      >
        <strong
          css={css`
            color: #eaf3ff;
            font-size: 11px;
          `}
        >
          Manage providers
        </strong>
        {editingId === null && (
          <button type="button" css={primaryButtonCss} onClick={startCreate}>
            + Add provider
          </button>
        )}
      </div>

      {error && (
        <div
          css={css`
            margin-bottom: 8px;
            padding: 8px 10px;
            border: 1px solid rgba(255, 113, 136, 0.25);
            border-radius: 9px;
            background: rgba(255, 113, 136, 0.06);
            color: #ff9dad;
            font-size: 10px;
          `}
        >
          {error}
        </div>
      )}

      {!loading && providers.length === 0 && editingId === null && (
        <div
          css={css`
            ${panelCss};
            padding: 14px;
            color: #8fa2bd;
            font-size: 10.5px;
            text-align: center;
          `}
        >
          No providers yet. Add one to enable AI Studio chat for everyone.
        </div>
      )}

      {providers.length > 0 && (
        <div
          css={css`
            ${panelCss};
            overflow: hidden;
          `}
        >
          {providers.map((item) => (
            <div
              key={item.id}
              css={css`
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 10px 11px;
                border-top: 1px solid rgba(255, 255, 255, 0.05);

                &:first-of-type {
                  border-top: none;
                }
              `}
            >
              <div
                css={css`
                  flex: 1;
                  min-width: 0;
                `}
              >
                <div
                  css={css`
                    color: #dceaff;
                    font-size: 11px;
                    font-weight: 600;
                  `}
                >
                  {item.label}
                </div>
                <small
                  css={css`
                    display: block;
                    margin-top: 2px;
                    overflow: hidden;
                    color: #8194ad;
                    font-size: 9px;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                  `}
                >
                  {item.base_url} · {item.models.length || 0} model
                  {item.models.length === 1 ? "" : "s"} ·{" "}
                  {item.has_api_key ? "key set" : "no key"}
                </small>
              </div>
              <Switch
                checked={item.enabled}
                disabled={busyId === item.id}
                onChange={() => toggleEnabled(item)}
                label={`${item.enabled ? "Disable" : "Enable"} ${item.label}`}
              />
              {confirmDeleteId === item.id ? (
                <>
                  <span
                    css={css`
                      color: #ff9dad;
                      font-size: 9px;
                      white-space: nowrap;
                    `}
                  >
                    Remove?
                  </span>
                  <button
                    type="button"
                    css={dangerButtonCss}
                    onClick={() => remove(item)}
                    disabled={busyId === item.id}
                  >
                    Yes, remove
                  </button>
                  <button
                    type="button"
                    css={secondaryButtonCss}
                    onClick={() => setConfirmDeleteId(null)}
                    disabled={busyId === item.id}
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    css={secondaryButtonCss}
                    onClick={() => startEdit(item)}
                    disabled={busyId === item.id}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    css={dangerButtonCss}
                    onClick={() => setConfirmDeleteId(item.id)}
                    disabled={busyId === item.id}
                  >
                    Delete
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {editingId !== null && (
        <div
          css={css`
            ${panelCss};
            margin-top: 10px;
            padding: 12px;
          `}
        >
          <strong
            css={css`
              display: block;
              margin-bottom: 10px;
              color: #eaf3ff;
              font-size: 10.5px;
            `}
          >
            {editingId === "new" ? "Add provider" : "Edit provider"}
          </strong>

          <div
            css={css`
              display: grid;
              grid-template-columns: 1fr 1fr;
              gap: 8px;
              margin-bottom: 8px;
            `}
          >
            <div>
              <label css={labelCss} htmlFor="ai-provider-label">
                Label
              </label>
              <input
                id="ai-provider-label"
                css={fieldCss}
                value={form.label}
                onChange={(event) =>
                  setForm({ ...form, label: event.target.value })
                }
                placeholder="OpenAI"
              />
            </div>
            <div>
              <label css={labelCss} htmlFor="ai-provider-base-url">
                Base URL
              </label>
              <input
                id="ai-provider-base-url"
                css={fieldCss}
                value={form.baseUrl}
                onChange={(event) =>
                  setForm({ ...form, baseUrl: event.target.value })
                }
                placeholder="https://api.openai.com/v1"
              />
            </div>
          </div>

          <div
            css={css`
              margin-bottom: 8px;
            `}
          >
            <label css={labelCss} htmlFor="ai-provider-api-key">
              API key
            </label>
            <input
              id="ai-provider-api-key"
              type="password"
              autoComplete="new-password"
              css={fieldCss}
              value={form.apiKey}
              onChange={(event) =>
                setForm({ ...form, apiKey: event.target.value })
              }
              placeholder={
                editingId !== "new" ? "Leave blank to keep the current key" : "sk-…"
              }
            />
          </div>

          <div
            css={css`
              display: grid;
              grid-template-columns: 1fr 1fr;
              gap: 8px;
              margin-bottom: 8px;
            `}
          >
            <div>
              <label css={labelCss} htmlFor="ai-provider-default-model">
                Default model
              </label>
              <input
                id="ai-provider-default-model"
                css={fieldCss}
                value={form.defaultModel}
                onChange={(event) =>
                  setForm({ ...form, defaultModel: event.target.value })
                }
                placeholder="gpt-4.1-mini"
              />
            </div>
            <div>
              <label css={labelCss} htmlFor="ai-provider-models">
                Models (comma-separated)
              </label>
              <input
                id="ai-provider-models"
                css={fieldCss}
                value={form.modelsText}
                onChange={(event) =>
                  setForm({ ...form, modelsText: event.target.value })
                }
                placeholder="gpt-4.1-mini, gpt-4.1"
              />
            </div>
          </div>

          <div
            css={css`
              margin-bottom: 8px;
            `}
          >
            <span css={labelCss}>Capabilities</span>
            <div
              css={css`
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
              `}
            >
              {EXTRA_CAPABILITIES.map((item) => {
                const active = form.capabilities.includes(item.id);
                return (
                  <button
                    key={item.id}
                    type="button"
                    css={toggleChipCss(active)}
                    onClick={() =>
                      setForm({
                        ...form,
                        capabilities: active
                          ? form.capabilities.filter((c) => c !== item.id)
                          : [...form.capabilities, item.id],
                      })
                    }
                  >
                    {item.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div
            css={css`
              margin-bottom: 8px;
            `}
          >
            <span css={labelCss}>Reasoning effort tiers (optional)</span>
            <div
              css={css`
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
              `}
            >
              {EFFORT_TIERS.map((tier) => {
                const active = form.effortLevels.includes(tier);
                return (
                  <button
                    key={tier}
                    type="button"
                    css={toggleChipCss(active)}
                    onClick={() =>
                      setForm({
                        ...form,
                        effortLevels: active
                          ? form.effortLevels.filter((t) => t !== tier)
                          : [...form.effortLevels, tier],
                      })
                    }
                  >
                    {tier}
                  </button>
                );
              })}
            </div>
          </div>

          {form.effortLevels.length > 0 && (
            <div
              css={css`
                margin-bottom: 8px;
              `}
            >
              <label css={labelCss} htmlFor="ai-provider-effort-param">
                Effort request field
              </label>
              <input
                id="ai-provider-effort-param"
                css={fieldCss}
                value={form.effortParam}
                onChange={(event) =>
                  setForm({ ...form, effortParam: event.target.value })
                }
                placeholder="reasoning_effort"
              />
            </div>
          )}

          <div
            css={css`
              display: flex;
              align-items: center;
              justify-content: space-between;
              margin-top: 10px;
            `}
          >
            <div
              css={css`
                display: flex;
                align-items: center;
                gap: 8px;
              `}
            >
              <Switch
                checked={form.enabled}
                onChange={() => setForm({ ...form, enabled: !form.enabled })}
                label="Enabled"
              />
              <span
                css={css`
                  color: #9db0c9;
                  font-size: 9.5px;
                `}
              >
                Enabled
              </span>
            </div>
            <div
              css={css`
                display: flex;
                gap: 8px;
              `}
            >
              <button
                type="button"
                css={secondaryButtonCss}
                onClick={cancelEdit}
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="button"
                css={primaryButtonCss}
                onClick={submit}
                disabled={saving}
              >
                {saving ? "Saving…" : "Save provider"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
