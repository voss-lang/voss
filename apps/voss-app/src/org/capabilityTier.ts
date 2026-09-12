import type { CapabilityTier } from './model/normalized';

export interface TierInput {
  cli: string;
  managed: boolean;

  hookCapable: boolean;
  adopted: boolean;
}

export function resolveTier(input: TierInput): CapabilityTier {
  if (input.adopted) return 'C'; // no retro-sandbox — never above C
  if (!input.managed) return 'C'; // observe-only
  return input.hookCapable ? 'A' : 'B';
}

export function hookCapableCli(_cli: string): boolean {
  return false;
}
