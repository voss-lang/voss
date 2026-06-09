// VCKP-13 capability-tier resolver (D-13). Pure module: no Solid imports, no
// produce/structuredClone — plain logic, fixture-testable.
//
// Tiers (SPEC VCKP-13): A = per-tool gate + sandbox + budget; B = sandbox +
// budget (no per-tool prompt); C = observe-only (budget-kill + audit + review).
// Honesty rules: an adopted already-running agent is ALWAYS C (a live PID
// cannot be retro-sandboxed, D-11); unmanaged spawns are C (nothing enforced).

import type { CapabilityTier } from './model/normalized';

export interface TierInput {
  cli: string;
  managed: boolean;
  /** True only when a per-tool permission proxy is ACTIVE for this CLI. */
  hookCapable: boolean;
  adopted: boolean;
}

export function resolveTier(input: TierInput): CapabilityTier {
  if (input.adopted) return 'C'; // no retro-sandbox — never above C
  if (!input.managed) return 'C'; // observe-only
  return input.hookCapable ? 'A' : 'B';
}

/**
 * Whether a per-tool permission proxy is ENFORCED for this CLI today.
 *
 * The VCKP-13b proxy (Claude Code hooks / OpenCode permission config) is not
 * shipped yet, so NO CLI is hook-enforced — every managed launch records tier
 * B (sandbox + budget). Flip per-CLI here when the proxy lands; never return
 * true ahead of real enforcement (T-V14-03: no overstated control).
 */
export function hookCapableCli(_cli: string): boolean {
  return false;
}
