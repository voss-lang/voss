import { type Component, createSignal, createMemo, onMount, Show, For } from 'solid-js';
import './modal.css';
import {
  adoptAgent,
  inferRole,
  inferRisk,
  ADOPT_UNAVAILABLE_REASON,
  type AdoptResult,
  type AdoptRisk,
} from '../../org/adopt';

// V14-10 (VCKP-12, D-10/D-11/D-12): "Let Voss manage this agent" — adopt a
// running ad-hoc terminal agent forward-only. Copy states OUTCOMES in plain
// language only: the internal-mechanics vocabulary is banned from every string
// here (D-10), and nothing may promise per-action gating for an external agent
// (adopt is always tier C, D-11). Budget-stop is the one hard promise allowed.

const RISKS: AdoptRisk[] = ['low', 'med', 'high'];

type Destination = 'current' | 'new';

export interface AdoptAgentModalProps {
  paneId: string;
  cliBinary: string;
  /** Existing run the agent can join, or null when none is open. */
  runId: string | null;
  /** False when this build exposes no way to record the agent's work. */
  harnessAdoptAvailable: boolean;
  onDismiss: () => void;
  onAdopt: (result: AdoptResult) => void;
}

const AdoptAgentModal: Component<AdoptAgentModalProps> = (props) => {
  let panelRef!: HTMLDivElement;
  let roleRef!: HTMLInputElement;

  const [destination, setDestination] = createSignal<Destination>(
    props.runId ? 'current' : 'new',
  );
  const [role, setRole] = createSignal(inferRole(props.cliBinary));
  const [riskTouched, setRiskTouched] = createSignal(false);
  const [riskSel, setRiskSel] = createSignal<AdoptRisk>('med');
  const [budget, setBudget] = createSignal('10');
  const [scope, setScope] = createSignal('');

  const [visible, setVisible] = createSignal(false);

  const budgetNum = createMemo(() => {
    const n = parseFloat(budget());
    return Number.isFinite(n) && n > 0 ? n : 0;
  });

  // D-12: risk stays pre-inferred (tracking scope/budget edits) until the user
  // picks one explicitly; after that the edit wins.
  const effectiveRisk = createMemo<AdoptRisk>(() =>
    riskTouched() ? riskSel() : inferRisk({ scope: scope(), budget: budgetNum() }),
  );

  onMount(() => {
    requestAnimationFrame(() => setVisible(true));
    roleRef?.focus();
  });

  const handleSubmit = () => {
    if (!props.harnessAdoptAvailable) return;
    const result = adoptAgent({
      paneId: props.paneId,
      runId: destination() === 'current' ? props.runId : null,
      scope: scope().trim(),
      budget: budgetNum(),
      cliBinary: props.cliBinary,
      harnessAdoptAvailable: props.harnessAdoptAvailable,
      role: role().trim() || undefined,
      risk: effectiveRisk(),
    });
    props.onAdopt(result);
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
          <span id="modal-title" class="modal-header__title">Let Voss manage this agent</span>
          <button class="modal-header__dismiss" onClick={() => props.onDismiss()} aria-label="Dismiss">×</button>
        </div>

        {/* Body */}
        <div class="modal-body">
          {/* Add it to */}
          <div class="modal-section">
            <div class="modal-label">Add it to</div>
            <div class="modal-segmented">
              <button
                class={`modal-segmented__btn${destination() === 'current' ? ' modal-segmented__btn--active' : ''}`}
                disabled={!props.runId}
                onClick={() => setDestination('current')}
              >
                Current run
              </button>
              <button
                class={`modal-segmented__btn${destination() === 'new' ? ' modal-segmented__btn--active' : ''}`}
                onClick={() => setDestination('new')}
              >
                A new run
              </button>
            </div>
          </div>

          {/* As the task */}
          <div class="modal-section">
            <div class="modal-label">As the task</div>
            <input
              ref={roleRef}
              class="modal-field"
              aria-label="Role"
              placeholder="e.g. executor"
              value={role()}
              onInput={(e) => setRole(e.currentTarget.value)}
            />
            <div class="modal-segmented">
              <For each={RISKS}>
                {(r) => (
                  <button
                    class={`modal-segmented__btn${effectiveRisk() === r ? ' modal-segmented__btn--active' : ''}`}
                    onClick={() => {
                      setRiskSel(r);
                      setRiskTouched(true);
                    }}
                  >
                    {r}
                  </button>
                )}
              </For>
            </div>
            <div class="modal-hint">
              Voss suggests these from what it can see — change either one.
            </div>
          </div>

          {/* Limits */}
          <div class="modal-section">
            <div class="modal-label">Limits</div>
            <input
              class="modal-field modal-field--mono"
              aria-label="Spending limit in dollars"
              inputmode="decimal"
              placeholder="spending limit (USD)"
              value={budget()}
              onInput={(e) => setBudget(e.currentTarget.value)}
            />
            <input
              class="modal-field modal-field--mono"
              aria-label="Where it should work"
              placeholder="optional — folder it should stay inside"
              value={scope()}
              onInput={(e) => setScope(e.currentTarget.value)}
            />
            <div class="modal-hint">
              Voss stops the agent at the spending limit. The folder boundary is
              a guideline the agent is asked to follow — Voss flags anything
              outside it for you.
            </div>
          </div>

          {/* From now on, Voss will */}
          <div class="modal-section">
            <div class="modal-label">From now on, Voss will</div>
            <div class="modal-hint">· track what this agent spends</div>
            <div class="modal-hint">· keep a record of its work</div>
            <div class="modal-hint">· warn you near the spending limit, and stop it at the limit</div>
            <div class="modal-hint">· ask you to review the result before it counts as done</div>
            <div class="modal-hint">
              Tracking starts now — anything the agent did before this isn't counted.
            </div>
          </div>

          {/* Disabled-with-reason: no fake affordance when no write-path exists */}
          <Show when={!props.harnessAdoptAvailable}>
            <div class="modal-section">
              <div class="modal-hint">{ADOPT_UNAVAILABLE_REASON}</div>
            </div>
          </Show>
        </div>

        {/* Footer */}
        <div class="modal-footer">
          <span class="modal-footer__hint">Press Ctrl+Enter to confirm</span>
          <button
            class="modal-btn-primary"
            disabled={!props.harnessAdoptAvailable}
            onClick={handleSubmit}
          >
            Hand to Voss
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdoptAgentModal;
