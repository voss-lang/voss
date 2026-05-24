import { type Component, createSignal, createMemo, onMount, Show, For } from 'solid-js';
import './modal.css';

type CliTab = 'claude' | 'codex' | 'antigravity' | 'opencode' | 'voss' | 'custom';
type EffortLevel = 'low' | 'medium' | 'high' | 'max' | 'xhigh';

const CLI_TABS: { id: CliTab; label: string }[] = [
  { id: 'claude', label: 'Claude' },
  { id: 'codex', label: 'Codex' },
  { id: 'antigravity', label: 'Antigravity' },
  { id: 'opencode', label: 'OpenCode' },
  { id: 'voss', label: 'Voss' },
  { id: 'custom', label: 'Custom' },
];

interface CliProfile {
  models?: string[];
  effortLevels: EffortLevel[];
  effortLabel: string;
  effortDefault: EffortLevel;
  effortFlag: string;
}

const CLI_PROFILES: Record<string, CliProfile> = {
  claude: {
    models: ['opus', 'sonnet', 'haiku'],
    effortLevels: ['low', 'medium', 'high', 'max'],
    effortLabel: 'Effort',
    effortDefault: 'high',
    effortFlag: '--effort',
  },
  codex: {
    effortLevels: ['low', 'medium', 'high', 'xhigh'],
    effortLabel: 'Reasoning',
    effortDefault: 'medium',
    effortFlag: '--reasoning-effort',
  },
  antigravity: {
    effortLevels: ['low', 'medium', 'high'],
    effortLabel: 'Effort',
    effortDefault: 'medium',
    effortFlag: '--effort',
  },
  opencode: {
    effortLevels: ['low', 'medium', 'high'],
    effortLabel: 'Effort',
    effortDefault: 'medium',
    effortFlag: '--effort',
  },
};

export interface AgentLaunchConfig {
  cliBinary: string;
  cliArgs: string[];
  taskPrompt: string;
}

export interface AgentLaunchModalProps {
  onDismiss: () => void;
  onLaunch: (config: AgentLaunchConfig) => void;
  customAgents?: { name: string; command: string }[];
  onSaveCustomAgent?: (agent: { name: string; command: string }) => void;
}

const AgentLaunchModal: Component<AgentLaunchModalProps> = (props) => {
  let panelRef!: HTMLDivElement;
  let firstTabRef!: HTMLButtonElement;

  const [activeTab, setActiveTab] = createSignal<CliTab>('claude');
  const [model, setModel] = createSignal('');
  const [effort, setEffort] = createSignal<EffortLevel>('high');
  const [planMode, setPlanMode] = createSignal(false);
  const [skipPermissions, setSkipPermissions] = createSignal(false);
  const [taskPrompt, setTaskPrompt] = createSignal('');

  const profile = createMemo(() => CLI_PROFILES[activeTab()] as CliProfile | undefined);

  const switchTab = (tab: CliTab) => {
    setActiveTab(tab);
    setModel('');
    const p = CLI_PROFILES[tab];
    if (p) setEffort(p.effortDefault);
  };
  // Voss-specific
  const [vossCommand, setVossCommand] = createSignal<'chat' | 'do' | 'resume' | 'agent'>('chat');
  const [vossMode, setVossMode] = createSignal<'edit' | 'plan'>('edit');
  const [vossAuth, setVossAuth] = createSignal('');
  // Custom
  const [customName, setCustomName] = createSignal('');
  const [customCommand, setCustomCommand] = createSignal('');

  const [visible, setVisible] = createSignal(false);

  onMount(() => {
    requestAnimationFrame(() => setVisible(true));
    firstTabRef?.focus();
  });

  const buildConfig = (): AgentLaunchConfig => {
    const tab = activeTab();
    const task = taskPrompt().trim();

    if (tab === 'custom') {
      const parts = customCommand().trim().split(/\s+/);
      const binary = parts[0] || '';
      const args = parts.slice(1);
      if (customName() && customCommand()) {
        props.onSaveCustomAgent?.({ name: customName(), command: customCommand() });
      }
      return { cliBinary: binary, cliArgs: args, taskPrompt: task };
    }

    if (tab === 'voss') {
      const args: string[] = [vossCommand()];
      if (vossCommand() === 'do' || vossCommand() === 'agent') {
        args.push('--mode', vossMode());
      }
      if (vossAuth()) args.push('--auth', vossAuth());
      if (task) args.push(task);
      return { cliBinary: 'voss', cliArgs: args, taskPrompt: task };
    }

    // Generic: claude/codex/antigravity/opencode
    const binaryMap: Record<string, string> = {
      claude: 'claude',
      codex: 'codex',
      antigravity: 'gemini',
      opencode: 'opencode',
    };
    const binary = binaryMap[tab] || tab;
    const args: string[] = [];
    const p = CLI_PROFILES[tab];

    if (model()) args.push('--model', model());

    if (p && effort() !== p.effortDefault) {
      args.push(p.effortFlag, effort());
    }

    if (planMode()) {
      args.push('--plan');
    }

    if (skipPermissions()) {
      if (tab === 'claude') args.push('--dangerously-skip-permissions');
      else args.push('--skip-review');
    }

    if (task) args.push(task);

    return { cliBinary: binary, cliArgs: args, taskPrompt: task };
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
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isGenericTab = () => {
    const t = activeTab();
    return t === 'claude' || t === 'codex' || t === 'antigravity' || t === 'opencode';
  };

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

        {/* Tabs */}
        <div class="modal-tabs">
          <For each={CLI_TABS}>
            {(tab, i) => (
              <button
                ref={(el: HTMLButtonElement) => { if (i() === 0) firstTabRef = el; }}
                class={`modal-tab${activeTab() === tab.id ? ' modal-tab--active' : ''}`}
                onClick={() => switchTab(tab.id)}
              >
                {tab.label}
              </button>
            )}
          </For>
        </div>

        {/* Body */}
        <div class="modal-body">
          {/* Generic agent panel */}
          <Show when={isGenericTab()}>
            {/* Model selector */}
            <Show when={profile()?.models}>
              <div class="modal-section">
                <div class="modal-label">Model</div>
                <div class="modal-segmented">
                  <For each={profile()!.models!}>
                    {(m) => (
                      <button
                        class={`modal-segmented__btn${model() === m ? ' modal-segmented__btn--active' : ''}`}
                        onClick={() => setModel(model() === m ? '' : m)}
                      >
                        {m}
                      </button>
                    )}
                  </For>
                </div>
              </div>
            </Show>

            {/* Effort / Reasoning */}
            <Show when={profile()}>
              <div class="modal-section">
                <div class="modal-label">{profile()!.effortLabel}</div>
                <div class="modal-segmented">
                  <For each={profile()!.effortLevels}>
                    {(e) => (
                      <button
                        class={`modal-segmented__btn${effort() === e ? ' modal-segmented__btn--active' : ''}`}
                        onClick={() => setEffort(e)}
                      >
                        {e}
                      </button>
                    )}
                  </For>
                </div>
              </div>
            </Show>

            {/* Toggles */}
            <div class="modal-row">
              <label class="modal-switch" onClick={() => setPlanMode(!planMode())}>
                <div class={`modal-switch__track${planMode() ? ' modal-switch__track--on' : ''}`}>
                  <div class="modal-switch__thumb" />
                </div>
                <span class="modal-switch__label">Plan Mode</span>
              </label>
              <label class="modal-switch" onClick={() => setSkipPermissions(!skipPermissions())}>
                <div class={`modal-switch__track${skipPermissions() ? ' modal-switch__track--on' : ''}`}>
                  <div class="modal-switch__thumb" />
                </div>
                <span class="modal-switch__label">Skip Permissions</span>
              </label>
            </div>

            {/* Task prompt */}
            <div class="modal-section">
              <div class="modal-label">Task</div>
              <textarea
                class="modal-field modal-textarea"
                placeholder="Describe the task (optional — leave blank for interactive mode)"
                value={taskPrompt()}
                onInput={(e) => setTaskPrompt(e.currentTarget.value)}
              />
            </div>
          </Show>

          {/* Voss panel */}
          <Show when={activeTab() === 'voss'}>
            <div>
              <div class="modal-label">Command</div>
              <div class="modal-segmented" style={{ 'margin-top': '4px' }}>
                <For each={['chat', 'do', 'resume', 'agent'] as const}>
                  {(cmd) => (
                    <button
                      class={`modal-segmented__btn${vossCommand() === cmd ? ' modal-segmented__btn--active' : ''}`}
                      onClick={() => setVossCommand(cmd)}
                    >
                      {cmd}
                    </button>
                  )}
                </For>
              </div>
            </div>

            <div>
              <div class="modal-label">Mode</div>
              <div class="modal-segmented" style={{ 'margin-top': '4px' }}>
                <For each={['edit', 'plan'] as const}>
                  {(m) => (
                    <button
                      class={`modal-segmented__btn${vossMode() === m ? ' modal-segmented__btn--active' : ''}`}
                      onClick={() => setVossMode(m)}
                    >
                      {m}
                    </button>
                  )}
                </For>
              </div>
            </div>

            <div>
              <div class="modal-label">Auth</div>
              <input
                class="modal-field"
                placeholder="Auth choice (optional)"
                value={vossAuth()}
                onInput={(e) => setVossAuth(e.currentTarget.value)}
                style={{ 'margin-top': '4px' }}
              />
            </div>

            <div>
              <div class="modal-label">Task</div>
              <textarea
                class="modal-field modal-textarea"
                placeholder="Describe the task (optional — leave blank for interactive mode)"
                value={taskPrompt()}
                onInput={(e) => setTaskPrompt(e.currentTarget.value)}
                style={{ 'margin-top': '4px' }}
              />
            </div>
          </Show>

          {/* Custom panel */}
          <Show when={activeTab() === 'custom'}>
            <div>
              <div class="modal-label">Name</div>
              <input
                class="modal-field"
                placeholder="e.g. my-agent"
                value={customName()}
                onInput={(e) => setCustomName(e.currentTarget.value)}
                style={{ 'margin-top': '4px' }}
              />
            </div>

            <div>
              <div class="modal-label">Command</div>
              <input
                class="modal-field modal-field--mono"
                placeholder="e.g. /usr/local/bin/my-agent --flag"
                value={customCommand()}
                onInput={(e) => setCustomCommand(e.currentTarget.value)}
                style={{ 'margin-top': '4px' }}
              />
            </div>
          </Show>
        </div>

        {/* Footer */}
        <div class="modal-footer">
          <span class="modal-footer__hint">Press Ctrl+Enter to start</span>
          <button
            class="modal-btn-primary"
            style={{ 'border-radius': '3px' }}
            onClick={handleSubmit}
          >
            Launch Agent
          </button>
        </div>
      </div>
    </div>
  );
};

export default AgentLaunchModal;
