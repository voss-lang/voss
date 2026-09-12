import type { CapabilityTier } from './model/normalized';

export interface TierInput {
  cli: string;
  managed: boolean;
/** True only when a tool permission proxy is ACTIVE for this CLI */
  hookCapable: boolean;
  adopted: boolean;
}

export function resolveTier(input: TierInput): CapabilityTier {
  if (input.adopted) return 'C'; // no retro-sandbox — never above C
  if (!input.managed) return 'C'; // observe-only
  return input.hookCapable ? 'A' : 'B';
}

/**
 * Whether a tool permission proxy is ENFORCED for this CLI today
 * The -13b proxy (Claude Code hooks / OpenCode permission config) is not
 */
export function hookCapableCli(_cli: string): boolean {
  return false;
}
