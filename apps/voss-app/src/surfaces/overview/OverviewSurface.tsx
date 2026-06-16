// V24-05 (VADE2-05) — Overview mission-control surface.
//
// Condensed roll-up over the same status grouping as TasksSurface: a per-group
// count strip plus the ACTIVE and BLOCKED groups expanded (the work that needs
// eyes). Reuses GROUPS / groupCards / TaskRow from TasksSurface — no
// re-derivation, no duplicated row markup.

import { type Component, For, Show } from 'solid-js';
import '../surfaces.css';
import { runData, loading, loadError } from '../../org/orgStore';
import { cardsFromRunData } from '../../org/boardDerive';
import { GROUPS, groupCards, TaskRow } from '../tasks/TasksSurface';
import SurfaceHeader, { type SurfaceHeaderProps } from '../SurfaceHeader';

export type OverviewSurfaceProps = Pick<
  SurfaceHeaderProps,
  'projectName' | 'projectPath' | 'gitBranch' | 'onNewSession' | 'onNewTask'
>;

// The groups the Overview expands inline (the rest are roll-up counts only).
const EXPANDED_KEYS = ['active', 'blocked'] as const;
const EXPANDED_GROUPS = GROUPS.filter((g) =>
  (EXPANDED_KEYS as readonly string[]).includes(g.key),
);

const OverviewSurface: Component<OverviewSurfaceProps> = (props) => {
  const cards = () => cardsFromRunData(runData());
  const grouped = () => groupCards(cards());

  return (
    <div class="surface" role="tabpanel" aria-label="Overview">
      <SurfaceHeader
        projectName={props.projectName ?? ''}
        projectPath={props.projectPath}
        gitBranch={props.gitBranch}
        onNewSession={props.onNewSession}
        onNewTask={props.onNewTask}
      />
      <Show
        when={!loading()}
        fallback={
          <div class="org-spinner">
            <span class="org-spinner__glyph">⟳</span>
          </div>
        }
      >
        <Show
          when={!loadError()}
          fallback={
            <div class="org-error-state">
              <p class="org-error-state__heading">Couldn't load Overview.</p>
              <p class="org-error-state__body">Check that Voss is running.</p>
            </div>
          }
        >
          <Show
            when={cards().length > 0}
            fallback={
              <div class="surface-empty">
                <p class="surface-empty__title">No active Tasks</p>
                <p class="surface-empty__hint">Use ⌘K to ask Voss to start one.</p>
              </div>
            }
          >
            <div class="surface__body">
              <div class="surface-rollup">
                <For each={GROUPS}>
                  {(group) => (
                    <Show when={grouped()[group.key].length > 0}>
                      <div class="surface-rollup__chip">
                        <span
                          class="surface-group__dot"
                          style={{ background: group.color }}
                        />
                        <span class="surface-rollup__label">{group.label}</span>
                        <span class="surface-rollup__num">
                          {grouped()[group.key].length}
                        </span>
                      </div>
                    </Show>
                  )}
                </For>
              </div>

              <For each={EXPANDED_GROUPS}>
                {(group) => (
                  <Show when={grouped()[group.key].length > 0}>
                    <div class="surface-group">
                      <div class="surface-group__header">
                        <span
                          class="surface-group__dot"
                          style={{ background: group.color }}
                        />
                        <span class="surface-group__name">{group.label}</span>
                        <span class="surface-group__count">
                          {grouped()[group.key].length}
                        </span>
                      </div>
                      <For each={grouped()[group.key]}>
                        {(card) => <TaskRow card={card} color={group.color} />}
                      </For>
                    </div>
                  </Show>
                )}
              </For>
            </div>
          </Show>
        </Show>
      </Show>
    </div>
  );
};

export default OverviewSurface;
