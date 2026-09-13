// S3.1/S3.8 shell-integration opt-in: off means Voss panes never set
// VOSS_EMBEDDED, so a sourced `voss shell-init` snippet stays inert.
import { createSignal } from 'solid-js';

const STORAGE_KEY = 'voss:shellIntegration';

const [enabled, setEnabled] = createSignal(
  localStorage.getItem(STORAGE_KEY) === 'true',
);

export function shellIntegrationEnabled(): boolean {
  return enabled();
}

export function setShellIntegration(next: boolean): void {
  localStorage.setItem(STORAGE_KEY, String(next));
  setEnabled(next);
}
