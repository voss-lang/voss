export type CliCommand = {
  cmd: string;
  desc: string;
};

export type HarnessFeature = {
  title: string;
  body: string;
};

export const site = {
  name: "Voss",
  tagline: "The operating layer for AI engineering teams.",
  description:
    "Voss runs AI coding agents like an engineering team: declared roles, hard budgets, scoped tools, independent review, and a replayable audit of every action. One goal in, audited work out.",
  /** Canonical marketing origin (metadataBase, sitemap, robots, llms.txt). */
  url: "https://voss.dev",
  /** Static marketing routes (trailing slash applied in sitemap). */
  routes: [
    "",
    "/harness",
    "/ade",
    "/language",
    "/security",
    "/roadmap",
    "/orchestration",
    "/audit",
  ] as const,
  repoUrl: "https://github.com/bm9797/Voss",
  prdUrl: "https://github.com/bm9797/Voss/blob/main/PRD.md",
  // Public Mintlify docs (repo voss-lang/voss, site/docs, branch master).
  docsUrl: "https://docs.tryvoss.dev",
  install: {
    primary: "npm i -g @vosslang/cli",
    primaryNote: "Bundles the Voss Python harness with vendored Python 3.12.",
  },
} as const;

export const harness = {
  tagline: "A coding harness for bounded repo work.",
  description:
    "The Voss harness is an agent loop that lives in your terminal. Drop into any repo, give it a goal, and keep reads, edits, shell commands, memory, and resumes inside explicit boundaries.",
  pitch: [
    "Install through npm without managing Python yourself, or use pip when you want the Python package directly.",
    "Modes are explicit: plan for read-only work, edit for scoped changes, auto for higher-trust local automation.",
    "Project memory lives in VOSS.md and .voss/memory, so useful repo context can survive beyond one chat.",
  ],
} as const;

export const harnessFeatures: readonly HarnessFeature[] = [
  {
    title: "Bring your own subscription",
    body:
      "Use Claude Code or Codex CLI auth when available, or fall back to ANTHROPIC_API_KEY / OPENAI_API_KEY for CI and reliable provider access.",
  },
  {
    title: "Permission modes that match how you work",
    body:
      "plan is read-only, edit supports scoped writes, and auto allows broader local automation through the lower-level safeguards.",
  },
  {
    title: "Real tools, not toys",
    body:
      "fs_read, fs_glob, fs_grep, fs_write, fs_edit, shell_run with an allowlist, git_status, git_diff, and voss_check. Everything jailed to your cwd.",
  },
  {
    title: "Confidence-gated planning",
    body:
      "Each turn produces a `ProbableValue<Plan>`. Low-confidence plans get rerolled, not executed. It is the same primitive Voss programs use.",
  },
  {
    title: "Sessions you can resume",
    body:
      "Sessions are stored per project under .voss/sessions. List them, resume by id, and keep prior runs tied to the repo.",
  },
  {
    title: "Headless or interactive",
    body:
      "`voss do \"ship the login flow\"` for one-shots. `voss chat` for the REPL. Same agent loop either way, whether scripted or supervised locally.",
  },
];

export const harnessCommands: readonly CliCommand[] = [
  { cmd: 'voss do "find the auth flow and name the risky files"', desc: "Read-only repo task" },
  { cmd: "voss chat", desc: "Interactive REPL with persistent session" },
  { cmd: "voss sessions", desc: "List saved project sessions" },
  { cmd: "voss resume <id>", desc: "Pick up where you left off" },
  { cmd: "voss tools", desc: "Inspect available harness tools" },
  { cmd: "voss config --show", desc: "Inspect local harness config" },
  { cmd: "voss doctor", desc: "Verify credentials, tools, sandbox" },
];

export const cliCommands: readonly CliCommand[] = [
  { cmd: "voss team check", desc: "Validate roles, scope, budget, tools" },
  { cmd: 'voss team run "add password reset"', desc: "Run the goal as an engineering team" },
  { cmd: "voss board", desc: "Watch cards move across the board" },
  { cmd: "voss review <run_id>", desc: "Inspect independent reviewer verdicts" },
  { cmd: "voss session tree <root_id>", desc: "Per-agent budget, scope, status" },
  { cmd: "voss capabilities list", desc: "Inspect the agent toolbelt" },
  { cmd: 'voss do "summarize this PR"', desc: "Single bounded agent task" },
  { cmd: "voss chat", desc: "Interactive REPL with live subagents" },
  { cmd: "voss doctor", desc: "Diagnose your environment" },
];

export type Primitive = {
  name: string;
  label: string;
  body: string;
  tone: string;
};

// The six product primitives (ORCHESTRATION_LAYERS.md §4.1).
export const primitives: readonly Primitive[] = [
  {
    name: "Capabilities",
    label: "Toolbelt",
    body: "Every tool is a typed, permissioned, auditable capability. Network and shell are default-deny unless a role is granted them.",
    tone: "#FF5B1F",
  },
  {
    name: "Principles",
    label: "Culture",
    body: "Engineering principles are first-class config in .voss, injected into every agent context and recorded in the audit.",
    tone: "#C58A0F",
  },
  {
    name: "Orchestration",
    label: "Delegation",
    body: "An Engineering Manager loop turns one idea into scoped cards, assigns roles, partitions budget, and integrates the result.",
    tone: "#2A6FDB",
  },
  {
    name: "Roles",
    label: "Specialists",
    body: "architect, backend, frontend, tester, reviewer, skeptic, docs — declared in .voss team{} with their own scope, budget, and model tier.",
    tone: "#1F8A4C",
  },
  {
    name: "Memory",
    label: "Knowledge",
    body: "VOSS.md, project memory, session trees, and decisions keep institutional context inspectable across runs.",
    tone: "#8A5CF6",
  },
  {
    name: "Verification",
    label: "Review loop",
    body: "Independent Reviewer-A and Reviewer-B gate completion. Agents cannot mark their own work done.",
    tone: "#D6457A",
  },
];

export type OrgStep = { step: string; title: string; body: string };

// The Engineering Manager loop (ORCHESTRATION_LAYERS.md §3.1, §7).
export const orgLoop: readonly OrgStep[] = [
  { step: "01", title: "Scope into cards", body: "The EM converts one human idea into bounded work cards with acceptance criteria." },
  { step: "02", title: "Assign roles", body: "Each card is routed to a declared role from the team roster, with a recorded rationale." },
  { step: "03", title: "Partition budget", body: "Budget and scope fan out down the session tree. No child can overspend its parent." },
  { step: "04", title: "Execute in parallel", body: "Workers run concurrently inside their scope, within WIP limits, where it is safe to." },
  { step: "05", title: "Verify continuously", body: "Reviewer-A authors the verification bar from the original idea — not the EM's summary." },
  { step: "06", title: "Review independently", body: "Reviewer-B judges the diff narrative-blind and can fail idea-divergent work." },
  { step: "07", title: "Block or integrate", body: "Unverified or out-of-scope work is blocked with a reason. Clean work is integrated." },
  { step: "08", title: "Audit and sign off", body: "A replayable audit report is produced. Humans sign off only at meaningful moments." },
];

// CLI demo for the MVP team-run flow (ORCHESTRATION_LAYERS.md §11).
export const teamRunDemo = `$ voss team check
  team "default" ok — 7 roles, budget 120k, scope src/** tests/** docs/**

$ voss team run "Add password reset flow with tests"
  → 4 cards derived · assigned architect, backend, tester, docs
  → budget partitioned · 4 workers dispatched
  → reviewer-A authored 6 checks · reviewer-B verdict: pass (0.91)
  → run_id 7f3a9c · 1 card blocked (rescoped) · audit ready

$ voss review 7f3a9c
  per-card reviewer-A + reviewer-B verdicts · evidence refs · outcomes`;

export type AuditSection = { n: string; title: string };

// The audit report sections (ORCHESTRATION_LAYERS.md §9).
export const auditSections: readonly AuditSection[] = [
  { n: "01", title: "Goal" },
  { n: "02", title: "Active Team" },
  { n: "03", title: "Principles" },
  { n: "04", title: "Scope and Budget" },
  { n: "05", title: "Board Timeline" },
  { n: "06", title: "Work Cards" },
  { n: "07", title: "Agent Actions" },
  { n: "08", title: "Diff Summary" },
  { n: "09", title: "Tests and Evals" },
  { n: "10", title: "Reviewer-A Verification" },
  { n: "11", title: "Reviewer-B Verdict" },
  { n: "12", title: "Blocked / Killed / Rescoped" },
  { n: "13", title: "Evidence References" },
  { n: "14", title: "Residual Risks" },
  { n: "15", title: "Final Human Decision" },
];

// Org-layer invariants the cage enforces (ORCHESTRATION_LAYERS.md §11).
export const orgInvariants: readonly string[] = [
  "The EM cannot invent roles outside the declared roster",
  "Workers cannot write outside their assigned scope",
  "Budget cannot be oversold — it is a security boundary",
  "Agents cannot mark their own work Done",
  "Done requires independent reviewer evidence",
  "Ceiling, confidence threshold, and roster are immutable mid-run",
];
