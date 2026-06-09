// VCKP-09 (best-effort) — inline feedback write path. Where the protocol
// exposes a write path (NATIVE session: POST /session/:id/message via V13.1),
// a comment dispatches a follow-up to the bound sessionNodeId; where it does
// not (snapshot card), the affordance is disabled-with-reason — never a silent
// no-op (decisionActions.ts discipline).

import { describe, it, expect, vi, afterEach } from 'vitest';

// CardDrawer's import chain (orgStore) touches @tauri-apps/api/core.
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';
import {
  dispatchFollowUp,
  nativeSessionNodeId,
  FOLLOWUP_DISABLED_REASON,
  type FollowUpClient,
} from '../feedbackWritePath';
import {
  registerNativeCard,
  __resetBridgeMaps,
} from '../model/bridge';
import { setSelectedCardId } from '../selection';
import CardDrawer from '../cockpit/CardDrawer';

function mockClient() {
  return { postMessage: vi.fn().mockResolvedValue({ status: 'accepted' }) };
}

let dispose: (() => void) | undefined;
function mountDrawer(client?: FollowUpClient): HTMLElement {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(
    () => CardDrawer({ data: null, followUpClient: client }) as never,
    root,
  );
  return root;
}

afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
  __resetBridgeMaps();
  setSelectedCardId(null);
});

describe('dispatchFollowUp — native write path (VCKP-09)', () => {
  it('a native card dispatches the comment to the CORRECT sessionNodeId via the client', async () => {
    registerNativeCard('card-n1', 'sess-abc123def456');
    const client = mockClient();

    const res = await dispatchFollowUp({
      cardId: 'card-n1',
      comment: 'tighten the test coverage',
      client,
      hasNativePath: true,
    });

    expect(client.postMessage).toHaveBeenCalledOnce();
    // resolveCard routes to the harness sessionID, NOT the card id.
    expect(client.postMessage).toHaveBeenCalledWith(
      'sess-abc123def456',
      'tighten the test coverage',
    );
    expect(res).toEqual({ disabled: false, sessionNodeId: 'sess-abc123def456' });
  });

  it('a snapshot-only card returns disabled-with-reason and dispatches NOTHING', async () => {
    const client = mockClient();

    const res = await dispatchFollowUp({
      cardId: 'C1', // never registered as native — pure snapshot card
      comment: 'hello',
      client,
      hasNativePath: true,
    });

    expect(res.disabled).toBe(true);
    if (!res.disabled) throw new Error('expected disabled');
    expect(res.reason).toBe(FOLLOWUP_DISABLED_REASON);
    expect(res.reason.length).toBeGreaterThan(0);
    expect(client.postMessage).not.toHaveBeenCalled(); // no silent no-op, no fake dispatch
  });

  it('hasNativePath:false disables even a native-bound card (no client → no claim)', async () => {
    registerNativeCard('card-n2', 'sess-zzz');
    const client = mockClient();
    const res = await dispatchFollowUp({
      cardId: 'card-n2',
      comment: 'x',
      client,
      hasNativePath: false,
    });
    expect(res.disabled).toBe(true);
    expect(client.postMessage).not.toHaveBeenCalled();
  });

  it('nativeSessionNodeId resolves only registered native cards', () => {
    registerNativeCard('card-n3', 'sess-123');
    expect(nativeSessionNodeId('card-n3')).toBe('sess-123');
    expect(nativeSessionNodeId('snapshot-card')).toBeUndefined();
  });
});

describe('CardDrawer comment affordance — disabled-with-reason vs active', () => {
  function sendBtn(el: HTMLElement) {
    return Array.from(el.querySelectorAll('button')).find(
      (b) => b.textContent?.trim() === 'Send follow-up',
    ) as HTMLButtonElement;
  }

  it('snapshot card: the affordance renders DISABLED with the visible reason', () => {
    setSelectedCardId('C1'); // snapshot card — no native binding
    const el = mountDrawer(mockClient());
    const btn = sendBtn(el);
    expect(btn).toBeTruthy();
    expect(btn.disabled).toBe(true);
    expect(el.textContent).toContain(FOLLOWUP_DISABLED_REASON);
  });

  it('native card with a client: the affordance is ACTIVE and dispatches on click', async () => {
    registerNativeCard('card-live', 'sess-live-1');
    setSelectedCardId('card-live');
    const client = mockClient();
    const el = mountDrawer(client);

    const btn = sendBtn(el);
    expect(btn.disabled).toBe(false);

    const box = el.querySelector(
      'textarea[placeholder*="follow-up"]',
    ) as HTMLTextAreaElement;
    expect(box).toBeTruthy();
    fireEvent.input(box, { target: { value: 'please add edge-case tests' } });
    fireEvent.click(btn);
    await Promise.resolve(); // let the async dispatch settle

    expect(client.postMessage).toHaveBeenCalledWith(
      'sess-live-1',
      'please add edge-case tests',
    );
  });

  it('no client (live wiring absent): disabled-with-reason even for a native card', () => {
    registerNativeCard('card-live2', 'sess-live-2');
    setSelectedCardId('card-live2');
    const el = mountDrawer(undefined);
    expect(sendBtn(el).disabled).toBe(true);
    expect(el.textContent).toContain(FOLLOWUP_DISABLED_REASON);
  });
});
