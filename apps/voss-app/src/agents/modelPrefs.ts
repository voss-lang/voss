// V14-09 per-CLI model catalog + persisted user default.
//
// Persistence rides the existing appearance-settings flatten store
// (`cliDefaultModels` sub-key) — no new Tauri command. See appearance/settings.ts.
//
// MODEL CATALOG honesty (operator-locked): only the Claude aliases
// (opus/sonnet/haiku) are safe to hardcode as real — Claude Code resolves them
// server-side and they auto-track the latest. For every other CLI the
// conservative default is to inject NO `--model` flag (so a renamed/missing
// model can never break the launch — the local CLI uses its own default); the
// user may type an optional override that maps straight to the CLI's `--model`.

import {
  loadAppearanceSettings,
  saveAppearanceSettings,
  getCommittedAppearanceSettings,
} from '../appearance/settings';

/** A CLI binary that can carry a per-launch model choice. */
export type ModelCliKey = 'claude' | 'codex' | 'gemini' | 'opencode' | 'aider';

export interface ModelPreset {
  /** CLI binary spawned in the PTY. */
  cliBinary: ModelCliKey;
  /** Display name shown on the preset card. */
  label: string;
  /**
   * Built-in default model. `null` = inject no `--model` flag; the local CLI
   * picks its own default (the honest path for non-Claude CLIs).
   */
  defaultModel: string | null;
  /**
   * Selectable alternates surfaced as chips. Empty = free-text only / none.
   * Only populated where the values are verified real (Claude aliases).
   */
  alternates: string[];
  /**
   * Whether the model is hardcoded-safe (true) or an advisory override the
   * user fills in (false). Drives the card copy.
   */
  modelVerified: boolean;
}

/**
 * Per-CLI catalog. Claude is the only verified-real default; the rest omit the
 * flag by default and expose an optional override.
 */
export const MODEL_PRESETS: Record<ModelCliKey, ModelPreset> = {
  claude: {
    cliBinary: 'claude',
    label: 'Claude Code',
    defaultModel: 'sonnet',
    alternates: ['opus', 'sonnet', 'haiku'],
    modelVerified: true,
  },
  codex: {
    cliBinary: 'codex',
    label: 'Codex',
    defaultModel: null,
    alternates: [],
    modelVerified: false,
  },
  gemini: {
    cliBinary: 'gemini',
    label: 'Gemini',
    defaultModel: null,
    alternates: [],
    modelVerified: false,
  },
  opencode: {
    cliBinary: 'opencode',
    label: 'OpenCode',
    defaultModel: null,
    alternates: [],
    modelVerified: false,
  },
  aider: {
    cliBinary: 'aider',
    label: 'Aider',
    defaultModel: null,
    alternates: [],
    modelVerified: false,
  },
};

export const MODEL_CLI_KEYS: ModelCliKey[] = [
  'claude',
  'codex',
  'gemini',
  'opencode',
  'aider',
];

/**
 * Resolve the effective default model for a CLI: the user's saved choice if
 * present, else the preset's built-in default (`null` = omit `--model`).
 * Reads the in-memory committed appearance settings (synchronous, hydrated at
 * boot by loadModelPrefs()).
 */
export function defaultModelFor(cli: ModelCliKey): string | null {
  const saved = getCommittedAppearanceSettings().cliDefaultModels?.[cli];
  if (typeof saved === 'string' && saved.trim()) return saved.trim();
  return MODEL_PRESETS[cli].defaultModel;
}

/** Hydrate the persisted per-CLI defaults from the appearance store. */
export async function loadModelPrefs(): Promise<Record<string, string>> {
  const settings = await loadAppearanceSettings();
  return settings.cliDefaultModels ?? {};
}

/**
 * Persist the user's chosen default model for a CLI. An empty/blank model
 * clears the override (falls back to the preset built-in default).
 */
export async function saveDefaultModel(
  cli: ModelCliKey,
  model: string,
): Promise<void> {
  const committed = getCommittedAppearanceSettings();
  const next = { ...(committed.cliDefaultModels ?? {}) };
  const trimmed = model.trim();
  if (trimmed) {
    next[cli] = trimmed;
  } else {
    delete next[cli];
  }
  await saveAppearanceSettings({
    ...committed,
    cliDefaultModels: Object.keys(next).length > 0 ? next : undefined,
  });
}
