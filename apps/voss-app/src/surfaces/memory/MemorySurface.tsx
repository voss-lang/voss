// V24-10 / V24-11 (VADE2-10/11) — Memory surface.
//
// Voss memory lives in the harness (voss/harness/memory_store.py). V24-11 exposed it
// over the loopback server's GET /memory route, so when the app has a live server
// (baseUrl + token + cwd) this surface renders the real memory summary + a recall
// search. With no live server it falls back to the honest harness-backed state
// (the /memory slash command). It synthesizes NO rows — hits come only from the
// server (honest-signal discipline, like the swarm surface).

import {
  type Component,
  createResource,
  createSignal,
  For,
  Match,
  Show,
  Switch,
} from 'solid-js';
import '../surfaces.css';
import './memory.css';
import { fetchMemory, type MemoryResponse } from '../../org/live/memoryClient';

export interface MemorySurfaceProps {
  baseUrl?: string;
  token?: string;
  cwd?: string;
}

/** Honest fallback when the app has no live server to query. */
const MemoryFallback: Component = () => (
  <div class="surface__body">
    <div class="surface-empty">
      <p class="surface-empty__title">Memory is managed by the Voss harness</p>
      <p class="surface-empty__hint">
        Recall and inspect memory from a Voss session with the{' '}
        <code>/memory</code> command. Start a session in this workspace to browse
        memory here.
      </p>
    </div>
  </div>
);

const MemorySurface: Component<MemorySurfaceProps> = (props) => {
  const live = () => !!(props.baseUrl && props.token && props.cwd);

  const [submitted, setSubmitted] = createSignal('');
  const [query, setQuery] = createSignal('');

  const [data] = createResource(
    () =>
      live()
        ? {
            baseUrl: props.baseUrl!,
            token: props.token!,
            cwd: props.cwd!,
            q: submitted(),
          }
        : null,
    (args: { baseUrl: string; token: string; cwd: string; q: string }) =>
      fetchMemory(args.baseUrl, args.token, args.cwd, args.q || undefined),
  );

  return (
    <div class="surface" role="tabpanel" aria-label="Memory">
      <div class="surface__header">
        <span class="surface__title">Memory</span>
      </div>
      <Show when={live()} fallback={<MemoryFallback />}>
        <div class="surface__body">
          <form
            class="memory-search"
            onSubmit={(e) => {
              e.preventDefault();
              setSubmitted(query());
            }}
          >
            <input
              class="memory-search__input"
              type="search"
              placeholder="Search memory…"
              aria-label="Search memory"
              value={query()}
              onInput={(e) => setQuery(e.currentTarget.value)}
            />
          </form>

          <Switch>
            <Match when={data.loading}>
              <div class="org-spinner">
                <span class="org-spinner__glyph">⟳</span>
              </div>
            </Match>
            <Match when={data.error}>
              <div class="org-error-state">
                <p class="org-error-state__heading">Couldn't load memory.</p>
                <p class="org-error-state__body">Check that Voss is running.</p>
              </div>
            </Match>
            <Match when={data()}>
              {(resp: () => MemoryResponse) => (
                <>
                  <Show when={resp().hits.length > 0} fallback={
                    <pre class="memory-summary">{resp().summary}</pre>
                  }>
                    <div class="memory-hits">
                      <For each={resp().hits}>
                        {(hit) => (
                          <div class="memory-hit">
                            <div class="memory-hit__head">
                              <span class="memory-hit__locator">{hit.locator}</span>
                              <span class="memory-hit__source">{hit.source}</span>
                            </div>
                            <p class="memory-hit__excerpt">{hit.excerpt}</p>
                          </div>
                        )}
                      </For>
                    </div>
                  </Show>
                </>
              )}
            </Match>
          </Switch>
        </div>
      </Show>
    </div>
  );
};

export default MemorySurface;
