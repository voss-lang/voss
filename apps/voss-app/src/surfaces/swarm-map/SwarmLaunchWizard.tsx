// V24 swarm surface — "Build your roster" launch wizard.
//
// A full-canvas, three-step intake shown in the swarm empty state: set the goal,
// compose the roster (presets + per-role agent/model), review + launch. Honest
// throughout: it self-connects the live server on launch (connectLiveServer),
// sends an explicit roster (per-role agent axis), and only the model choices the
// catalog verifies are offered. Native roles run in-process; CLI roles run via
// runSwarm() inside launchSwarm.

import { type Component, createSignal, For, Show } from 'solid-js';
import './swarmWizard.css';
import {
  liveServer,
  connectLiveServer,
  canConnectLiveServer,
} from '../../org/live/liveServer';
import { launchSwarm } from '../../org/live/swarmLaunch';
import {
  AGENT_MODEL_OPTIONS,
  ROSTER_PRESETS,
  buildRoster,
  renumberBuilders,
  builderCount,
  optionFor,
  toRoleSpecs,
  type RosterRole,
  type RoleKind,
} from '../../org/live/roster';

interface SwarmLaunchWizardProps {
  /** Called after a successful launch (the map then renders the live swarm). */
  onLaunched?: () => void;
}

const MAX_BUILDERS = 8;
const TOTAL_STEPS = 3;

const RoleIcon: Component<{ kind: RoleKind }> = (props) => (
  <svg
    class="swz-role__glyph"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <Show when={props.kind === 'coordinator'}>
      <path d="M3 7l4 4 5-6 5 6 4-4v10H3V7Z" />
    </Show>
    <Show when={props.kind === 'builder'}>
      <path d="m14 7 3-3 3 3-3 3-2-2-7 7 1 1-3 3-3-3 3-3 1 1 7-7-2-2Z" />
    </Show>
    <Show when={props.kind === 'reviewer'}>
      <path d="M4 4v16M4 5h12l-2 4 2 4H4" />
    </Show>
  </svg>
);

const roleLabel = (kind: RoleKind): string =>
  kind === 'coordinator' ? 'Conductor' : kind === 'builder' ? 'Engineer' : 'Auditor';

const SwarmLaunchWizard: Component<SwarmLaunchWizardProps> = (props) => {
  const [step, setStep] = createSignal(1);
  const [goal, setGoal] = createSignal('');
  const [roster, setRoster] = createSignal<RosterRole[]>(buildRoster(2));
  const [busy, setBusy] = createSignal(false);
  const [phase, setPhase] = createSignal<'connecting' | 'launching' | null>(null);
  const [note, setNote] = createSignal<string | null>(null);

  const connected = () => !!liveServer();
  const builders = () => builderCount(roster());
  const total = () => roster().length;
  const activePreset = () =>
    ROSTER_PRESETS.find((p) => p.builders === builders())?.name ?? null;

  const applyPreset = (n: number) => setRoster(buildRoster(n));

  const setRoleOption = (idx: number, optionId: string) => {
    const opt = AGENT_MODEL_OPTIONS.find((o) => o.id === optionId);
    if (!opt) return;
    setRoster((rs) =>
      rs.map((r, i) => (i === idx ? { ...r, agent: opt.agent, model: opt.model } : r)),
    );
  };

  const addBuilder = () => {
    setRoster((rs) => {
      if (builderCount(rs) >= MAX_BUILDERS) return rs;
      const reviewerAt = rs.findIndex((r) => r.kind === 'reviewer');
      const at = reviewerAt === -1 ? rs.length : reviewerAt;
      const next = [...rs];
      next.splice(at, 0, { name: 'builder', kind: 'builder', agent: 'voss', model: 'default' });
      return renumberBuilders(next);
    });
  };

  const removeRole = (idx: number) => {
    setRoster((rs) => {
      if (rs[idx]?.kind !== 'builder' || builderCount(rs) <= 1) return rs;
      return renumberBuilders(rs.filter((_, i) => i !== idx));
    });
  };

  const canNext = () => step() < TOTAL_STEPS && (step() !== 1 || goal().trim().length > 0);
  const canLaunch = () =>
    goal().trim().length > 0 && !busy() && (connected() || canConnectLiveServer());

  async function onLaunch(): Promise<void> {
    if (!goal().trim()) return;
    setBusy(true);
    setNote(null);
    try {
      let srv = liveServer();
      if (!srv) {
        setPhase('connecting');
        srv = await connectLiveServer();
      }
      if (!srv) {
        setNote('Open a workspace folder to connect a live Voss server.');
        return;
      }
      setPhase('launching');
      await launchSwarm(srv, {
        goal: goal().trim(),
        builders: builders(),
        roster: toRoleSpecs(roster()),
      });
      props.onLaunched?.();
    } catch (e) {
      const verb = phase() === 'connecting' ? 'connect' : 'launch orchestra';
      setNote(`Couldn't ${verb}: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
      setPhase(null);
    }
  }

  return (
    <div class="swz" role="group" aria-label="Launch an orchestra">
      <div class="swz__head">
        <span class="swz__mark" aria-hidden="true" />
        <h2 class="swz__title">
          {step() === 1 ? 'Set the goal' : step() === 2 ? 'Build your roster' : 'Review & launch'}
        </h2>
        <p class="swz__sub">
          <Show when={step() === 1} fallback={
            <Show when={step() === 2} fallback="Confirm the team, then launch the orchestra.">
              Pick a preset, then tune each agent. This is the team that ships your work.
            </Show>
          }>
            Describe what Voss should coordinate across the roster.
          </Show>
        </p>
      </div>

      <div class="swz__body">
        {/* Step 1 — Goal */}
        <Show when={step() === 1}>
          <label class="swz__field">
            <span class="swz__label">Goal</span>
            <textarea
              class="swz__goal"
              aria-label="Orchestra goal"
              placeholder="Describe the work to coordinate…"
              rows="5"
              autofocus
              value={goal()}
              onInput={(e) => setGoal(e.currentTarget.value)}
            />
          </label>
        </Show>

        {/* Step 2 — Roster */}
        <Show when={step() === 2}>
          <div class="swz__section-label">Quick presets</div>
          <div class="swz__presets">
            <For each={ROSTER_PRESETS}>
              {(p) => (
                <button
                  type="button"
                  classList={{ 'swz-preset': true, 'swz-preset--active': activePreset() === p.name }}
                  aria-pressed={activePreset() === p.name}
                  onClick={() => applyPreset(p.builders)}
                >
                  <span class="swz-preset__num">{p.total}</span>
                  <span class="swz-preset__name">{p.name}</span>
                </button>
              )}
            </For>
          </div>

          <div class="swz__chips" aria-hidden="true">
            <span class="swz-chip">1 Conductor</span>
            <span class="swz-chip">{builders()} Engineer{builders() === 1 ? '' : 's'}</span>
            <span class="swz-chip">1 Auditor</span>
            <span class="swz-chip__total">{total()} total</span>
          </div>

          <ul class="swz__roster">
            <For each={roster()}>
              {(role, i) => (
                <li class="swz-role">
                  <span class="swz-role__idx">{i() + 1}</span>
                  <span classList={{ 'swz-role__tile': true, [`swz-role__tile--${role.kind}`]: true }}>
                    <RoleIcon kind={role.kind} />
                  </span>
                  <span class="swz-role__name">{roleLabel(role.kind)}</span>
                  <select
                    class="swz-role__select"
                    aria-label={`${roleLabel(role.kind)} agent and model`}
                    value={optionFor(role).id}
                    onChange={(e) => setRoleOption(i(), e.currentTarget.value)}
                  >
                    <For each={AGENT_MODEL_OPTIONS}>
                      {(o) => <option value={o.id}>{o.label}</option>}
                    </For>
                  </select>
                  <Show
                    when={role.kind === 'builder' && builders() > 1}
                    fallback={<span class="swz-role__spacer" />}
                  >
                    <button
                      type="button"
                      class="swz-role__remove"
                      aria-label={`Remove ${role.name}`}
                      onClick={() => removeRole(i())}
                    >
                      ✕
                    </button>
                  </Show>
                </li>
              )}
            </For>
          </ul>

          <button
            type="button"
            class="swz__add"
            disabled={builders() >= MAX_BUILDERS}
            onClick={addBuilder}
          >
            + Add engineer
          </button>
        </Show>

        {/* Step 3 — Review */}
        <Show when={step() === 3}>
          <div class="swz-review">
            <div class="swz-review__row">
              <span class="swz-review__k">Goal</span>
              <span class="swz-review__v">{goal().trim()}</span>
            </div>
            <div class="swz-review__row">
              <span class="swz-review__k">Roster</span>
              <span class="swz-review__v">
                {builders()} engineer{builders() === 1 ? '' : 's'} · {total()} agents
              </span>
            </div>
            <ul class="swz-review__list">
              <For each={roster()}>
                {(role, i) => (
                  <li class="swz-review__item">
                    <span class="swz-role__idx">{i() + 1}</span>
                    <span classList={{ 'swz-role__tile': true, [`swz-role__tile--${role.kind}`]: true }}>
                      <RoleIcon kind={role.kind} />
                    </span>
                    <span class="swz-role__name">{roleLabel(role.kind)}</span>
                    <span class="swz-review__opt">{optionFor(role).label}</span>
                  </li>
                )}
              </For>
            </ul>
          </div>

          <Show when={!connected()}>
            <p
              classList={{ 'swz__note': true, 'swz__note--warn': !canConnectLiveServer() }}
              role="note"
            >
              <span aria-hidden="true">●</span>
              {canConnectLiveServer()
                ? 'Launch will start a live Voss server for this workspace.'
                : 'Open a workspace to connect a live Voss server.'}
            </p>
          </Show>
          <Show when={note()}>
            <p class="swz__note swz__note--warn" role="alert">
              <span aria-hidden="true">●</span>
              {note()}
            </p>
          </Show>
        </Show>
      </div>

      <div class="swz__footer">
        <button
          type="button"
          class="swz__nav swz__nav--ghost"
          disabled={step() === 1 || busy()}
          onClick={() => setStep((s) => Math.max(1, s - 1))}
        >
          ← Back
        </button>
        <span class="swz__steps">
          Step {step()} of {TOTAL_STEPS}
        </span>
        <Show
          when={step() < TOTAL_STEPS}
          fallback={
            <button
              type="button"
              class="swz__nav swz__nav--primary"
              disabled={!canLaunch()}
              onClick={() => void onLaunch()}
            >
              {phase() === 'connecting'
                ? 'Connecting…'
                : phase() === 'launching'
                  ? 'Launching…'
                  : 'Launch orchestra'}
            </button>
          }
        >
          <button
            type="button"
            class="swz__nav swz__nav--primary"
            disabled={!canNext()}
            onClick={() => setStep((s) => Math.min(TOTAL_STEPS, s + 1))}
          >
            Next →
          </button>
        </Show>
      </div>
    </div>
  );
};

export default SwarmLaunchWizard;
