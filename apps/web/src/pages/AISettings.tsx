import { useEffect, useState } from 'react';
import { Bot, ExternalLink, Save, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { useAICatalog, useAISettings, useCredentials, usePermissions, useUpdateAISettings } from '../hooks/useApi';
import type {
  AITask,
  AIModelProfileDTO,
  AIProviderSelectionDTO,
  AISettingsDTO,
  AITaskPolicyDTO,
} from '../types';

const TASKS: { key: AITask; label: string; description: string }[] = [
  { key: 'investigation', label: 'Investigation', description: 'Evidence collection and operational reasoning' },
  { key: 'root_cause', label: 'Root Cause', description: 'Hypothesis analysis and cause validation' },
  { key: 'remediation_planning', label: 'Remediation Planning', description: 'Structured remediation plan generation' },
  { key: 'verification', label: 'Verification', description: 'Recovery validation after actions' },
  { key: 'explanation', label: 'Explanation', description: 'Human-readable incident and result explanations' },
  { key: 'classification', label: 'Classification', description: 'Incident/resource classification' },
];

function accessLabel(profile: AIModelProfileDTO) {
  if (profile.local) return 'Local';
  if (profile.availability === 'paid') return 'Paid';
  if (profile.availability === 'mixed') return 'Mixed';
  return 'Free';
}

function SelectionEditor({
  value,
  catalog,
  credentials,
  onChange,
  allowEmpty = false,
}: {
  value: AIProviderSelectionDTO | null;
  catalog: AIModelProfileDTO[];
  credentials: { id: string; name: string; credential_type: string; enabled: boolean }[];
  onChange: (value: AIProviderSelectionDTO | null) => void;
  allowEmpty?: boolean;
}) {
  const runnable = catalog.filter((profile) => profile.runtime_supported);
  const currentId = value ? value.provider + '/' + value.model : '';
  const selected = currentId
    ? runnable.find((profile) => profile.provider + '/' + profile.id === currentId)
    : allowEmpty
      ? undefined
      : runnable.find((profile) => profile.local);
  const selectValue = currentId || (allowEmpty ? '' : selected ? selected.provider + '/' + selected.id : '');

  const selectModel = (id: string) => {
    if (!id) {
      if (allowEmpty) onChange(null);
      return;
    }
    const profile = runnable.find((item) => item.provider + '/' + item.id === id);
    if (!profile) return;
    onChange({
      provider: profile.provider,
      model: profile.id,
      credential_id: profile.credential_mode === 'api_key' ? value?.credential_id ?? null : null,
      base_url: profile.provider === 'openai_compatible' ? value?.base_url ?? null : null,
    });
  };

  return (
    <div className="space-y-3">
      <select
        value={selectValue}
        onChange={(event) => selectModel(event.target.value)}
        className="w-full rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text"
      >
        {allowEmpty && <option value="">Disabled</option>}
        {runnable.map((profile) => (
          <option key={profile.provider + '/' + profile.id} value={profile.provider + '/' + profile.id}>
            {profile.display_name} · {accessLabel(profile)}
          </option>
        ))}
      </select>
      {selected && (
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="default">{accessLabel(selected)}</Badge>
          {selected.credential_mode === 'api_key' && <Badge variant="default">Requires API Key</Badge>}
          {selected.local && <Badge variant="default">Bundled</Badge>}
          {selected.autonomous_ops_ready && <Badge variant="default">Autonomous ready</Badge>}
          {selected.context_window_tokens && (
            <span className="text-[11px] text-nexus-textMuted">
              Context {selected.context_window_tokens.toLocaleString()} tokens
            </span>
          )}
        </div>
      )}
      {selected?.provider === 'openai_compatible' && value && (
        <input
          value={value.base_url ?? ''}
          onChange={(event) => onChange({ ...value, base_url: event.target.value || null })}
          placeholder="https://your-provider.example/v1"
          className="w-full rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text"
        />
      )}
      {selected?.credential_mode === 'api_key' && value && (
        <select
          value={value.credential_id ?? ''}
          onChange={(event) => onChange({ ...value, credential_id: event.target.value || null })}
          className="w-full rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text"
        >
          <option value="">Select API key credential…</option>
          {credentials
            .filter((item) => item.enabled && ['api_key', 'token'].includes(item.credential_type))
            .map((credential) => (
              <option key={credential.id} value={credential.id}>
                {credential.name}
              </option>
            ))}
        </select>
      )}
    </div>
  );
}

type EditableTaskPolicy = AITaskPolicyDTO & {
  __label: string;
  __description: string;
};

function TaskPolicyEditor({
  policy,
  catalog,
  credentials,
  onChange,
}: {
  policy: EditableTaskPolicy;
  catalog: AIModelProfileDTO[];
  credentials: { id: string; name: string; credential_type: string; enabled: boolean }[];
  onChange: (value: AITaskPolicyDTO) => void;
}) {
  const selection =
    policy.mode === 'explicit'
      ? {
          provider: policy.provider!,
          model: policy.model!,
          credential_id: policy.credential_id,
          base_url: policy.base_url,
        }
      : null;

  return (
    <div className="rounded-lg border border-nexus-border bg-nexus-surfaceHover p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="font-medium text-nexus-text">{policy.__label}</p>
          <p className="text-xs text-nexus-textMuted">{policy.__description}</p>
        </div>
        <select
          value={policy.mode}
          onChange={(event) =>
            onChange(
              event.target.value === 'auto'
                ? { mode: 'auto', provider: null, model: null, credential_id: null, base_url: null }
                : {
                    mode: 'explicit',
                    provider: selection?.provider ?? 'ollama',
                    model: selection?.model ?? 'hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M',
                    credential_id: selection?.credential_id ?? null,
                    base_url: selection?.base_url ?? null,
                  },
            )
          }
          className="rounded-lg border border-nexus-border bg-nexus-surface px-3 py-2 text-sm text-nexus-text"
        >
          <option value="auto">AUTO · Router decides</option>
          <option value="explicit">Explicit model</option>
        </select>
      </div>
      {policy.mode === 'explicit' && (
        <div className="mt-3">
          <SelectionEditor
            value={selection}
            catalog={catalog}
            credentials={credentials}
            onChange={(next) =>
              onChange({
                mode: 'explicit',
                provider: next?.provider ?? null,
                model: next?.model ?? null,
                credential_id: next?.credential_id ?? null,
                base_url: next?.base_url ?? null,
              })
            }
          />
        </div>
      )}
    </div>
  );
}

export function AISettingsPage() {
  const catalogQuery = useAICatalog();
  const settingsQuery = useAISettings();
  const credentialsQuery = useCredentials();
  const permissionsQuery = usePermissions();
  const update = useUpdateAISettings();
  const [form, setForm] = useState<AISettingsDTO | null>(null);

  useEffect(() => {
    if (settingsQuery.data) setForm(settingsQuery.data);
  }, [settingsQuery.data]);

  const catalog = catalogQuery.data ?? [];
  const credentials = credentialsQuery.data?.credentials ?? [];
  const runnableCatalog = catalog.filter((item) => item.runtime_supported);

  const taskEntries: EditableTaskPolicy[] = TASKS.map((task) => ({
    ...(form?.tasks?.[task.key] ?? {
      mode: 'auto',
      provider: null,
      model: null,
      credential_id: null,
      base_url: null,
    }),
    __label: task.label,
    __description: task.description,
  }));

  const updateSelection = (
    key: 'primary' | 'fallback',
    value: AIProviderSelectionDTO | null,
  ) => {
    if (!form) return;
    setForm({ ...form, [key]: value });
  };

  const save = async () => {
    if (!form) return;
    const tasks = Object.fromEntries(
      TASKS.map((task) => [
        task.key,
        {
          mode: taskEntries.find((entry) => entry.__label === task.label)?.mode ?? 'auto',
          provider: taskEntries.find((entry) => entry.__label === task.label)?.provider ?? null,
          model: taskEntries.find((entry) => entry.__label === task.label)?.model ?? null,
          credential_id:
            taskEntries.find((entry) => entry.__label === task.label)?.credential_id ?? null,
          base_url: taskEntries.find((entry) => entry.__label === task.label)?.base_url ?? null,
        },
      ]),
    ) as AISettingsDTO['tasks'];

    await update.mutateAsync({ ...form, tasks });
  };

  if (catalogQuery.isLoading || settingsQuery.isLoading || credentialsQuery.isLoading || permissionsQuery.isLoading) {
    return <Card><p className="text-sm text-nexus-textMuted">Loading AI configuration…</p></Card>;
  }

  if (catalogQuery.error || settingsQuery.error || credentialsQuery.error || permissionsQuery.error || !form) {
    return <Card><p className="text-sm text-red-300">Unable to load AI configuration.</p></Card>;
  }

  const canManage = permissionsQuery.data?.permissions.includes('ai.manage') ?? false;

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-nexus-primary" />
            <h1 className="text-2xl font-bold text-nexus-text">AI Settings</h1>
            <Badge variant="default">{runnableCatalog.length} runtime models</Badge>
          </div>
          <p className="mt-1 text-sm text-nexus-textMuted">
            Configure primary, fallback, local AI and task-specific model policy for this workspace.
          </p>
        </div>
        {canManage && <button
          onClick={() => void save()}
          disabled={update.isPending}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-nexus-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {update.isPending ? 'Saving…' : 'Save AI settings'}
        </button>}
        {!canManage && <Badge variant="default">Read-only AI policy</Badge>}
      </div>

      <Card className="border-blue-900/50 bg-blue-900/10">
        <div className="flex items-start gap-3">
          <ShieldCheck className="mt-0.5 h-5 w-5 text-blue-300" />
          <div>
            <p className="font-medium text-blue-200">Credentials stay server-side</p>
            <p className="mt-1 text-xs text-nexus-textMuted">
              API key values remain encrypted in the vault and are never returned to this page.
            </p>
            <Link to="/credentials" className="mt-2 inline-flex items-center gap-1 text-xs text-nexus-primary hover:underline">
              Manage API key credentials <ExternalLink className="h-3 w-3" />
            </Link>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="text-lg font-semibold text-nexus-text">Primary provider</h2>
          <p className="mt-1 text-xs text-nexus-textMuted">Used first when its capabilities match the task.</p>
          <div className="mt-4">
            <SelectionEditor
              value={form.primary}
              catalog={catalog}
              credentials={credentials}
              onChange={(value) => value && updateSelection('primary', value)}
            />
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-nexus-text">Fallback provider</h2>
          <p className="mt-1 text-xs text-nexus-textMuted">Used when the selected path is unavailable or fails.</p>
          <div className="mt-4">
            <SelectionEditor
              value={form.fallback}
              catalog={catalog}
              credentials={credentials}
              allowEmpty
              onChange={(value) => updateSelection('fallback', value)}
            />
          </div>
        </Card>
      </div>

      <Card>
        <h2 className="text-lg font-semibold text-nexus-text">Local fallback</h2>
        <p className="mt-1 text-xs text-nexus-textMuted">Bundled Ollama model used when cloud paths are unavailable.</p>
        <div className="mt-4">
          <select
            value={form.local_model}
            onChange={(event) => setForm({ ...form, local_model: event.target.value })}
            className="w-full rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text"
          >
            {catalog
              .filter((item) => item.local && item.runtime_supported)
              .map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.display_name}
                </option>
              ))}
          </select>
        </div>
      </Card>

      <Card>
        <div>
          <h2 className="text-lg font-semibold text-nexus-text">Task-specific model policy</h2>
          <p className="mt-1 text-xs text-nexus-textMuted">
            AUTO lets the NEXUS Router select a capable provider. Explicit pins that task to a model.
          </p>
        </div>
        <div className="mt-4 space-y-3">
          {taskEntries.map((policy, index) => (
            <TaskPolicyEditor
              key={TASKS[index].key}
              policy={policy}
              catalog={catalog}
              credentials={credentials}
              onChange={(next) => {
                const tasks = { ...form.tasks };
                tasks[TASKS[index].key] = {
                  mode: next.mode,
                  provider: next.provider,
                  model: next.model,
                  credential_id: next.credential_id,
                  base_url: next.base_url,
                };
                setForm({ ...form, tasks });
              }}
            />
          ))}
        </div>
      </Card>

      {canManage && update.error && <p className="text-sm text-red-300">{update.error.message}</p>}
      {update.isSuccess && <p className="text-sm text-green-300">AI settings saved.</p>}
    </div>
  );
}
