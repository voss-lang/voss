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
  tagline: "A local control plane for coding agents.",
  description:
    "Voss gives local agent runs scoped tools, reusable project memory, approval gates, independent review, and an audit trail you can replay before you trust the result.",
/** Canonical marketing origin (metadataBase, sitemap, robots, llms.txt) */
  url: "https://www.tryvoss.dev",
/** Static marketing routes (trailing slash applied in sitemap) */
  routes: [
    "",
    "/harness",
    "/ade",
    "/language",
    "/about",
    "/contact",
    "/security",
    "/privacy",
    "/disclosure",
    "/orchestration",
    "/audit",
  ] as const,
  repoUrl: "https://github.com/voss-lang/voss",
  // Public Mintlify docs (repo voss-lang/voss, site/docs, branch master).
  docsUrl: "https://docs.tryvoss.dev",
  install: {
    primary: "npm i -g @vosslang/cli",
    primaryNote: "Bundles the Voss Python harness, vendored Python 3.12, and the Go terminal client.",
  },
} as const;

export const harness = {
  tagline: "A coding harness for bounded repo work.",
  description:
    "The Voss harness is an agent loop that lives in your terminal. Run `voss` in any repo, give it a goal, and keep reads, edits, shell commands, memory, and resumes inside explicit boundaries.",
  pitch: [
    "Install through npm without managing Python yourself, or pip install from GitHub when you manage Python 3.11+ yourself.",
    "Modes are explicit: observe and plan for read-only work, edit for scoped changes, auto for higher-trust local automation.",
    "Project memory, code recall, and your AGENTS.md and CLAUDE.md instructions carry repo context across sessions.",
  ],
} as const;

export const harnessFeatures: readonly HarnessFeature[] = [
  {
    title: "Bring your own subscription",
    body:
      "Sign in with Claude Code or Codex OAuth, or use ANTHROPIC_API_KEY / OPENAI_API_KEY for CI. `/model` and `/auth` switch model and provider mid-session, and the choice persists.",
  },
  {
    title: "Permission modes that match how you work",
    body:
      "observe and plan are read-only, edit supports scoped writes, and auto allows broader local automation. Project rules in `.voss/permissions.yml` can deny tools outright.",
  },
  {
    title: "Real tools, not toys",
    body:
      "File, code search, symbol lookup, git, shell, and web tools. Core file tools stay project-scoped, shell runs from an allowlist, and network tools need `--allow-net`.",
  },
  {
    title: "Plans that admit doubt",
    body:
      "Each turn plans before it acts. The plan's confidence is recorded as the model's own report, and a plan below 0.60 stops to ask you instead of running.",
  },
  {
    title: "Sessions you can resume",
    body:
      "Sessions are stored per project under .voss/sessions. Resume by id or name with `voss resume` or `/resume`, and the saved transcript replays in the TUI.",
  },
  {
    title: "Code-aware recall",
    body:
      "`voss recall` and the `code_recall` tool search code and project memory together, with labeled sources and lexical fallback. Jev reranking is opt-in.",
  },
  {
    title: "Your MCP servers and skills",
    body:
      "Voss picks up the MCP servers and skills you already configured for Claude Code and Codex. MCP calls still pass Voss's network and permission checks.",
  },
  {
    title: "Instructions you can inspect",
    body:
      "AGENTS.md and CLAUDE.md load into every run within a token budget. `voss instructions show` lists each file, its token count, and its hash.",
  },
  {
    title: "Headless or interactive",
    body:
      "`voss do \"ship the login flow\"` for one-shots, bare `voss` for the full-screen Go TUI, and `voss serve` for clients. Same agent loop each way.",
  },
];

export const harnessCommands: readonly CliCommand[] = [
  { cmd: "voss", desc: "Full-screen Go terminal client" },
  { cmd: 'voss do "find the auth flow and name the risky files"', desc: "Read-only repo task" },
  { cmd: "voss sessions", desc: "List saved project sessions" },
  { cmd: "voss resume <id>", desc: "Pick up where you left off" },
  { cmd: 'voss recall "where is retry backoff handled?"', desc: "Search code and memory together" },
  { cmd: "voss mcp list", desc: "Show discovered MCP servers and tools" },
  { cmd: "voss instructions show", desc: "See the instructions the agent gets" },
  { cmd: "voss tools", desc: "Inspect available harness tools" },
  { cmd: "voss doctor", desc: "Verify credentials, tools, sandbox" },
];

export const cliCommands: readonly CliCommand[] = [
  { cmd: "voss team check", desc: "Validate roles, scope, budget, tools" },
  { cmd: 'voss team run "add password reset"', desc: "Run the goal as an engineering team" },
  { cmd: "voss board", desc: "Watch cards move across the board" },
  { cmd: "voss review <run_id>", desc: "Inspect independent reviewer verdicts" },
  { cmd: "voss audit <run_id>", desc: "Render the full replayable audit" },
  { cmd: 'voss judge review --criterion "..."', desc: "Advisory check against acceptance criteria" },
  { cmd: "voss session tree <root_id>", desc: "Per-agent budget, scope, status" },
  { cmd: 'voss recall "permission gate"', desc: "Search code and project memory" },
  { cmd: 'voss do "summarize this PR"', desc: "Single bounded agent task" },
  { cmd: "voss", desc: "Full-screen Go terminal client" },
  { cmd: "voss serve", desc: "Local REST + SSE API for clients and SDKs" },
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
    body: "Every tool, including MCP tools Voss discovers, is a typed, permissioned, auditable capability. Network and shell are default-deny unless a role is granted them.",
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
    body: "VOSS.md, AGENTS.md, project memory, session trees, and decisions keep institutional context inspectable across runs.",
    tone: "#8A5CF6",
  },
  {
    name: "Verification",
    label: "Review loop",
    body: "Independent Reviewer-A and Reviewer-B gate completion. Agents cannot mark their own work done, and Jev assessments add advisory evidence per criterion.",
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
