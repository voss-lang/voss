/** Known agent CLI binary names for foreground process detection. */
export const KNOWN_AGENT_CLIS = new Set([
  'claude',
  'codex',
  'gemini',
  'opencode',
  'aider',
  'cursor',
]);

export function isKnownAgentCli(proc: string): boolean {
  return KNOWN_AGENT_CLIS.has(proc.toLowerCase());
}
