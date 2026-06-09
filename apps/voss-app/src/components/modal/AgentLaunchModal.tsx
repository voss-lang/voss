import { type Component, createSignal, createMemo, onMount, Show, For } from 'solid-js';
import './modal.css';
import type { CapabilityTier } from '../../org/model/normalized';
import {
  MODEL_PRESETS,
  MODEL_CLI_KEYS,
  defaultModelFor,
  saveDefaultModel,
  type ModelCliKey,
} from '../../agents/modelPrefs';

// V14-09 (D-09 sparse premium): preset launcher for external agent CLIs.
// Presets are the five known agent CLIs plus a plain Terminal. Native Voss runs
// go through RunCommandBar (D-04) — they are intentionally NOT here. No raw
// command, no effort matrices, no Skip-Permissions toggle.

type PresetId = ModelCliKey | 'terminal';

const PRESETS: { id: PresetId; label: string }[] = [
  { id: 'claude', label: 'Claude' },
  { id: 'codex', label: 'Codex' },
  { id: 'gemini', label: 'Gemini' },
  { id: 'opencode', label: 'OpenCode' },
  { id: 'aider', label: 'Aider' },
  { id: 'terminal', label: 'Terminal' },
];

type Placement = 'right' | 'below' | 'newtab';

const PLACEMENTS: { id: Placement; label: string }[] = [
  { id: 'right', label: 'Right' },
  { id: 'below', label: 'Below' },
  { id: 'newtab', label: 'New tab' },
];

export interface AgentLaunchConfig {
  cliBinary: string;
  cliArgs: string[];
  taskPrompt: string;
  placement: Placement;
  managed: boolean;
  tier: CapabilityTier;
  kind?: 'agent' | 'terminal';
}

export interface AgentLaunchModalProps {
  onDismiss: () => void;
  onLaunch: (config: AgentLaunchConfig) => void;
}

const AgentLaunchModal: Component<AgentLaunchModalProps> = (props) => {
  let panelRef!: HTMLDivElement;
  let firstTabRef!: HTMLButtonElement;

  const [activePreset, setActivePreset] = createSignal<PresetId>('claude');
  const [model, setModel] = createSignal('');
  const [workingDir, setWorkingDir] = createSignal('');
  const [taskPrompt, setTaskPrompt] = createSignal('');
  const [managed, setManaged] = createSignal(false);
  const [placement, setPlacement] = createSignal<Placement>('right');

  const [visible, setVisible] = createSignal(false);

  const isTerminal = () => activePreset() === 'terminal';
  const cliKey = createMemo<ModelCliKey | null>(() =>
    isTerminal() ? null : (activePreset() as ModelCliKey),
  );
  const preset = createMemo(() => {
    const k = cliKey();
    return k ? MODEL_PRESETS[k] : null;
  });

  // The effective model for the active preset: explicit selection, else the
  // persisted/built-in default. `null` = no flag injected (CLI's own default).
  const effectiveModel = createMemo<string | null>(() => {
    const k = cliKey();
    if (!k) return null;
    const sel = model().trim();
    if (sel) return sel;
    return defaultModelFor(k);
  });

  const switchPreset = (id: PresetId) => {
    setActivePreset(id);
    setModel('');
  };

  onMount(() => {
    requestAnimationFrame(() => setVisible(true));
    firstTabRef?.focus();
  });

  const buildConfig = (): AgentLaunchConfig => {
    const task = taskPrompt().trim();
    const cwd = workingDir().trim();

    if (isTerminal()) {
      // Plain login shell — no agentConfig wired in App (see blankTerminalWiring).
      return {
        cliBinary: '',
        cliArgs: [],
        taskPrompt: '',
        placement: placement(),
        managed: false,
        tier: 'C',
        kind: 'terminal',
      };
    }

    const k = cliKey()!;
    const args: string[] = [];

    // Persist the chosen default model so the next launch pre-fills it. Only
    // when the user actively selected one (never overwrite with a blank).
    const selected = model().trim();
    if (selected) void saveDefaultModel(k, selected);

    const resolvedModel = effectiveModel();
    if (resolvedModel) args.push('--model', resolvedModel);
    if (cwd) args.push('--cwd', cwd);
    if (task) args.push(task);

    return {
      cliBinary: k,
      cliArgs: args,
      taskPrompt: task,
      placement: placement(),
      managed: managed(),
      tier: 'B',
      kind: 'agent',
    };
  };

  const handleSubmit = () => {
    props.onLaunch(buildConfig());
  };

  const onBackdropClick = (e: MouseEvent) => {
    if (panelRef && !panelRef.contains(e.target as Node)) {
      props.onDismiss();
    }
  };

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      props.onDismiss();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  const managedCopy = () =>
    `External agent — uses your local ${preset()?.label ?? activePreset()} & credentials; advisory scope (full management arrives later).`;

  return (
    <div class="modal-backdrop" onClick={onBackdropClick} onKeyDown={onKeyDown}>
      <div
        ref={panelRef}
        class={`modal-panel${visible() ? ' modal-panel--visible' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Header */}
        <div class="modal-header">
          <span id="modal-title" class="modal-header__title">New Agent Session</span>
          <button class="modal-header__dismiss" onClick={() => props.onDismiss()} aria-label="Dismiss">×</button>
        </div>

        {/* Preset tabs */}
        <div class="modal-tabs">
          <For each={PRESETS}>
            {(p, i) => (
              <button
                ref={(el: HTMLButtonElement) => { if (i() === 0) firstTabRef = el; }}
                class={`modal-tab${activePreset() === p.id ? ' modal-tab--active' : ''}`}
                onClick={() => switchPreset(p.id)}
              >
                {p.label}
              </button>
            )}
          </For>
        </div>

        {/* Body */}
        <div class="modal-body">
          {/* Agent preset panel */}
          <Show when={!isTerminal()}>
            {/* Model */}
            <div class="modal-section">
              <div class="modal-label">Model</div>
              <Show
                when={preset()!.modelVerified && preset()!.alternates.length > 0}
                fallback={
                  <input
                    class="modal-field modal-field--mono"
                    placeholder={`optional — leave blank for ${preset()!.label}'s own default`}
                    value={model()}
                    onInput={(e) => setModel(e.currentTarget.value)}
                  />
                }
              >
                <div class="modal-segmented">
                  <For each={preset()!.alternates}>
                    {(m) => (
                      <button
                        class={`modal-segmented__btn${effectiveModel() === m ? ' modal-segmented__btn--active' : ''}`}
                        onClick={() => setModel(m)}
                      >
                        {m}
                      </button>
                    )}
                  </For>
                </div>
              </Show>
              <div class="modal-hint">
                {effectiveModel()
                  ? `${preset()!.label} · ${effectiveModel()}`
                  : `${preset()!.label} · uses its own default model`}
              </div>
            </div>

            {/* Working dir */}
            <div class="modal-section">
              <div class="modal-label">Working directory</div>
              <input
                class="modal-field modal-field--mono"
                placeholder="optional — defaults to the workspace folder"
                value={workingDir()}
                onInput={(e) => setWorkingDir(e.currentTarget.value)}
              />
            </div>

            {/* Task prompt */}
            <div class="modal-section">
              <div class="modal-label">What should it work on?</div>
              <textarea
                class="modal-field modal-textarea"
                placeholder="optional"
                value={taskPrompt()}
                onInput={(e) => setTaskPrompt(e.currentTarget.value)}
              />
            </div>

            {/* Pane placement */}
            <div class="modal-section">
              <div class="modal-label">Placement</div>
              <div class="modal-segmented">
                <For each={PLACEMENTS}>
                  {(p) => (
                    <button
                      class={`modal-segmented__btn${placement() === p.id ? ' modal-segmented__btn--active' : ''}`}
                      onClick={() => setPlacement(p.id)}
                    >
                      {p.label}
                    </button>
                  )}
                </For>
              </div>
            </div>

            {/* Managed-launch toggle (tier B honesty) */}
            <div class="modal-section">
              <label class="modal-switch" onClick={() => setManaged(!managed())}>
                <div class={`modal-switch__track${managed() ? ' modal-switch__track--on' : ''}`}>
                  <div class="modal-switch__thumb" />
                </div>
                <span class="modal-switch__label">Managed launch</span>
              </label>
              <div class="modal-hint">{managedCopy()}</div>
            </div>
          </Show>

          {/* Terminal preset panel */}
          <Show when={isTerminal()}>
            <div class="modal-section">
              <div class="modal-hint">
                Opens a plain shell — type any CLI yourself. Voss injects nothing;
                a missing command errors naturally.
              </div>
            </div>

            <div class="modal-section">
              <div class="modal-label">Placement</div>
              <div class="modal-segmented">
                <For each={PLACEMENTS}>
                  {(p) => (
                    <button
                      class={`modal-segmented__btn${placement() === p.id ? ' modal-segmented__btn--active' : ''}`}
                      onClick={() => setPlacement(p.id)}
                    >
                      {p.label}
                    </button>
                  )}
                </For>
              </div>
            </div>
          </Show>
        </div>

        {/* Footer */}
        <div class="modal-footer">
          <span class="modal-footer__hint">Press Ctrl+Enter to start</span>
          <button
            class="modal-btn-primary"
            onClick={handleSubmit}
          >
            {isTerminal() ? 'Open Terminal' : 'Launch Agent'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AgentLaunchModal;
