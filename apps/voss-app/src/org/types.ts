// V13.1-REPLACE: hand-authored stopgap — replace with codegen contract snapshot when Phase V13.1 TypeScript Local Client SDK lands.
//
// Pure type/interface module: no imports, no logic, no side effects.
// Shapes mirror the VERIFIED upstream CLI-JSON contracts (V11-RESEARCH.md
// "Upstream JSON Contracts"). guards.ts is the runtime boundary that rejects
// drift between these declared shapes and the real `load_run` output (D-02).

// --- Session tree node + transitions -----------------------------------------

export interface Envelope {
  limit: number;
  spent: number;
}

export type ExitReason = 'done' | 'timeout' | 'killed' | 'error';

export interface TerminalState {
  exit_reason: ExitReason;
  final: unknown;
}

export interface VerdictSnapshot {
  conf: number;
  source: 'A' | 'B';
  tier: string;
  verdict: 'pass' | 'fail' | 'block';
  notes: string;
  evidence_refs: string[];
  domain_inferred: string;
}

export interface BoardTransition {
  kind: 'board.transition';
  from: string;
  to: string;
  outcome: string;
  verdict_snapshot: VerdictSnapshot | null;
}

export interface EmTicket {
  kind: 'em.ticket';
  id: string;
  card_id: string;
  risk_tier: 'low' | 'med' | 'high';
  ts: string;
}

export interface EmRouting {
  kind: 'em.routing';
  id: string;
  card_id: string;
  chosen_role: string;
  candidates_considered: string[];
  rationale_text: string;
  ts: string;
}

export interface EmKill {
  kind: 'em.kill';
  killed_node_id: string;
  rationale_text: string;
  evidence_refs: string[];
  killed_at: string;
}

export interface EmRescope {
  kind: 'em.rescope';
  predecessor_card_id: string;
  successor_card_id: string;
  diff_summary: string;
  rationale_text: string;
  rescoped_at: string;
}

/** Discriminated union over `kind` — every transition shape a node may hold. */
export type Transition =
  | BoardTransition
  | EmTicket
  | EmRouting
  | EmKill
  | EmRescope
  | RunFinal;

export interface SessionTreeNode {
  id: string;
  root_id: string;
  parent_run_id: string | null;
  envelope: Envelope;
  terminal_state: TerminalState | null;
  created_at: string;
  ended_at: string | null;
  transitions: Transition[];
  scope: string | null;
  role: string | null;
}

// --- Run final ---------------------------------------------------------------

export interface SignOff {
  decision: 'approve' | 'reject';
  ts: string;
}

export interface RunFinal {
  kind: 'em.run_final';
  root_id: string;
  idea: string;
  total_cards: number;
  done_count: number;
  blocked_count: number;
  killed_count: number;
  rescope_count: number;
  em_iterations: number;
  ts: string;
  sign_off?: SignOff;
}

// --- Review sidecar ----------------------------------------------------------

export interface AVerification {
  result: string;
  test_path_or_rubric: string;
  notes: string;
}

export interface BVerdict {
  verdict: string;
  conf: number;
  tier: string;
  domain_inferred: string;
  notes: string;
  evidence_refs: string[];
}

export interface ReviewSidecar {
  a_verification: AVerification | null;
  b_verdict: BVerdict | null;
  final_outcome: 'pass' | 'fail' | 'block' | '?';
}

// --- Audit report ------------------------------------------------------------

export interface AuditCard {
  node_id: string;
  column: string;
  risk_tier: string;
  retry_count: number;
  is_killed: boolean;
}

export interface Leak6 {
  status: string;
  evidence: string;
  mitigation_present: boolean;
}

export interface AuditSnapshot {
  root_id: string;
  nodes: string[];
  cards: AuditCard[];
  kills: EmKill[];
  rescopes: EmRescope[];
  routings: EmRouting[];
  verdicts: VerdictSnapshot[];
  liveness: Array<Record<string, unknown>>;
  leak6: Leak6;
  run_final: RunFinal | null;
}

export interface AuditReport {
  run_id: string;
  idea: string;
  principles: Array<[string, string]>;
  team_config: { source: string; roster_ids: string[] };
  snapshot: AuditSnapshot;
  review_sidecars: Record<string, ReviewSidecar>;
  run_final: RunFinal | null;
  signoff_ack: unknown | null;
  calibration: Record<string, unknown> | null;
  sections_missing: string[];
  unsupported_claims: string[];
}

// --- Command results ---------------------------------------------------------

/** One entry from `enumerate_runs`. */
export interface RunEntry {
  run_id: string;
  mtime_secs: number;
  has_run_final: boolean;
}

/** Result of `run_decision` (D-08: stdout/stderr/exit captured). */
export interface DecisionResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exit_code: number;
}

/** Aggregate returned by `load_run` — the root contract guards.ts validates. */
export interface RunData {
  run_id: string;
  session_tree: { root_id: string; nodes: SessionTreeNode[] };
  review: Record<string, ReviewSidecar>;
  audit: AuditReport | null;
  run_final: RunFinal | null;
}

// --- Replay reducer view types (D-05/D-06) -----------------------------------

export interface CardSnapshot {
  id: string;
  role: string | null;
  risk: string;
  status: string;
  budget: { limit: number; spent: number };
}

/** Board/card state reconstructed at a single replay step. */
export interface BoardFrame {
  columns: Record<string, CardSnapshot[]>;
  step: number;
  eventLabel: string;
}
