// V24-10 (VADE2-10) — Memory surface (honest state).
//
// Voss memory is real but lives in the harness (voss/harness/memory_store.py,
// memory_cli.py) and is reachable today via the `/memory` slash command inside a
// Voss session. It is NOT exposed over the server HTTP API the app talks to (routes
// are session/cost/permission/doctor only — verified), so the app has no live
// memory data to render. This surface states that plainly and points to the real
// entry point. It synthesizes NO memory rows (honest-signal discipline, same as the
// Swarm Map's missing-signal handling).
//
// Live in-app memory data is deferred backend work (a `/memory` HTTP route + typed
// client) tracked as a follow-up requirement — see V24-10-PLAN.md "Deferred".

import { type Component } from 'solid-js';
import '../surfaces.css';

const MemorySurface: Component = () => (
  <div class="surface" role="tabpanel" aria-label="Memory">
    <div class="surface__header">
      <span class="surface__title">Memory</span>
    </div>
    <div class="surface__body">
      <div class="surface-empty">
        <p class="surface-empty__title">Memory is managed by the Voss harness</p>
        <p class="surface-empty__hint">
          Recall and inspect memory from a Voss session with the{' '}
          <code>/memory</code> command. A live in-app memory view isn't wired yet —
          it needs a server endpoint, which is tracked as follow-up work.
        </p>
      </div>
    </div>
  </div>
);

export default MemorySurface;
