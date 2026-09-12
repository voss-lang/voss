import { MODEL_PRESETS } from '../../agents/modelPrefs';
import type { RoleSpecBody } from './swarmClient';

export type RoleKind = 'coordinator' | 'builder' | 'reviewer';

export const NATIVE_AGENT = 'voss';

export const DEFAULT_MODEL = 'default';

export interface RosterRole {

  name: string;
  kind: RoleKind;
  agent: string;
  model: string;
}

export interface AgentModelOption {
  id: string;
  label: string;
  agent: string;
  model: string;

  native: boolean;
}

const cap = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);

export const AGENT_MODEL_OPTIONS: AgentModelOption[] = [
  { id: NATIVE_AGENT, label: 'Native · Voss', agent: NATIVE_AGENT, model: DEFAULT_MODEL, native: true },
  ...MODEL_PRESETS.claude.alternates.map((m) => ({
    id: `claude:${m}`,
    label: `Claude · ${cap(m)}`,
    agent: 'claude',
    model: m,
    native: false,
  })),
  { id: 'codex', label: 'Codex', agent: 'codex', model: DEFAULT_MODEL, native: false },
  { id: 'gemini', label: 'Gemini', agent: 'gemini', model: DEFAULT_MODEL, native: false },
  { id: 'opencode', label: 'OpenCode', agent: 'opencode', model: DEFAULT_MODEL, native: false },
  { id: 'aider', label: 'Aider', agent: 'aider', model: DEFAULT_MODEL, native: false },
];

export const DEFAULT_OPTION = AGENT_MODEL_OPTIONS[0];

export function optionFor(role: { agent: string; model: string }): AgentModelOption {
  return (
    AGENT_MODEL_OPTIONS.find((o) => o.agent === role.agent && o.model === role.model) ??
    DEFAULT_OPTION
  );
}

export interface RosterPreset {
  name: string;
  builders: number;
  total: number;
}
export const ROSTER_PRESETS: RosterPreset[] = [
  { name: 'Recon', builders: 1, total: 3 },
  { name: 'Squad', builders: 2, total: 4 },
  { name: 'Crew', builders: 4, total: 6 },
  { name: 'Swarm', builders: 6, total: 8 },
];

export function buildRoster(
  builders: number,
  base: AgentModelOption = DEFAULT_OPTION,
): RosterRole[] {
  const n = Math.max(1, builders);
  const mk = (name: string, kind: RoleKind): RosterRole => ({
    name,
    kind,
    agent: base.agent,
    model: base.model,
  });
  return [
    mk('coordinator', 'coordinator'),
    ...Array.from({ length: n }, (_, i) => mk(`builder-${i + 1}`, 'builder')),
    mk('reviewer', 'reviewer'),
  ];
}

export function renumberBuilders(roles: RosterRole[]): RosterRole[] {
  let b = 0;
  return roles.map((r) => {
    if (r.kind !== 'builder') return r;
    b += 1;
    return { ...r, name: `builder-${b}` };
  });
}

export const builderCount = (roles: RosterRole[]): number =>
  roles.filter((r) => r.kind === 'builder').length;

export function toRoleSpecs(roles: RosterRole[]): RoleSpecBody[] {
  return roles.map((r) => ({ name: r.name, agent: r.agent, model: r.model }));
}

export const hasCliRole = (roles: RosterRole[]): boolean =>
  roles.some((r) => r.agent !== NATIVE_AGENT);
