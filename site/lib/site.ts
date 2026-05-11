export type Feature = {
  name: string;
  title: string;
  body: string;
};

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
  tagline: "A language for AI workflows.",
  description:
    "Voss makes confidence checking, token budgets, prompt construction, semantic routing, and agent lifecycle first-class language constructs — not boilerplate you write in every project.",
  repoUrl: "https://github.com/your-org/voss",
  prdUrl: "https://github.com/your-org/voss/blob/main/PRD.md",
  docsUrl: "https://docs.voss.dev",
  version: "0.1.0-pre",
  install: {
    primary: 'pip install -e ".[dev]"',
    primaryNote: "From the cloned repo. PyPI release with v1.",
  },
} as const;

export const features: readonly Feature[] = [
  {
    name: "probable<T>",
    title: "Confidence as a type",
    body:
      "Calls to a model return a value with a confidence score. Gates like `if intent @ 0.80` are checked by the compiler — no more silently trusting low-confidence output.",
  },
  {
    name: "ctx",
    title: "Token budgets, not prompt math",
    body:
      "`ContextScope(token_budget=3000)` is a language construct. Voss handles compression, eviction, and budget enforcement so your code stays declarative.",
  },
  {
    name: "match",
    title: "Semantic routing, compile-time",
    body:
      "Embedding-based `match` cases are computed at build time. Route by meaning without paying for an embedding call on every request.",
  },
  {
    name: "spawn / gather",
    title: "Agent concurrency primitives",
    body:
      "Spawn researchers in parallel, gather their results with a timeout, fall back gracefully on budget exhaustion. Like goroutines for agents.",
  },
  {
    name: "providers",
    title: "Anthropic, OpenAI, Ollama",
    body:
      "One runtime, swappable providers. Your Voss program doesn't care which model is behind it — switch with a config flag, not a rewrite.",
  },
  {
    name: "compile",
    title: "Readable Python out",
    body:
      "Voss compiles to debuggable Python you can read, diff, and own. No black-box runtime, no magic — your generated code is shippable on its own.",
  },
];

export const harness = {
  tagline: "A coding harness for shipping AI.",
  description:
    "The Voss harness is an agent loop that lives in your terminal. Drop into any repo, give it a goal, watch it read, edit, run, and verify code. Built for AI-first developers who already pay for Claude Pro or ChatGPT — and want their subscription to do the work.",
  pitch: [
    "Use the Claude or ChatGPT subscription you already have. No second API bill.",
    "Sandboxed by default. cwd jail, shell allowlist, no network surprises.",
    "Built on the same runtime as Voss the language. Confidence-gated planning, token budgets, episodic memory — all first-class.",
  ],
} as const;

export const harnessFeatures: readonly HarnessFeature[] = [
  {
    title: "Bring your own subscription",
    body:
      "OAuth into Claude Code or Codex CLI. The harness reuses those tokens — your Pro/Max plan covers the bill, no API key required.",
  },
  {
    title: "Permission modes that match how you work",
    body:
      "plan (read-only), edit (read + scoped writes), or auto (allowlisted everything). Decisions persist per-project, so you grant once and ship.",
  },
  {
    title: "Real tools, not toys",
    body:
      "fs_read, fs_glob, fs_grep, fs_write, fs_edit, shell_run with an allowlist, git_status, git_diff, and voss_check. Everything jailed to your cwd.",
  },
  {
    title: "Confidence-gated planning",
    body:
      "Each turn produces a `ProbableValue<Plan>`. Low-confidence plans get rerolled, not executed. Same primitive Voss programs use — eat your own dog food.",
  },
  {
    title: "Sessions you can resume",
    body:
      "Every chat persists to ~/.local/state/voss/sessions. Restart, switch machines, replay a transcript — the episodic memory comes with it.",
  },
  {
    title: "Headless or interactive",
    body:
      "`voss do \"ship the login flow\"` for one-shots. `voss chat` for the REPL. Same agent loop either way — script it in CI or babysit it locally.",
  },
];

export const harnessCommands: readonly CliCommand[] = [
  { cmd: 'voss do "fix the failing tests in tests/auth/"', desc: "One-shot agent task" },
  { cmd: "voss chat", desc: "Interactive REPL with persistent session" },
  { cmd: "voss chat --resume <id>", desc: "Pick up where you left off" },
  { cmd: "voss --auth=claude do ...", desc: "Force Claude Code OAuth" },
  { cmd: "voss --auth=codex do ...", desc: "Force Codex (ChatGPT) OAuth" },
  { cmd: "voss doctor", desc: "Verify credentials, tools, sandbox" },
];

export const cliCommands: readonly CliCommand[] = [
  { cmd: "voss init", desc: "Scaffold a new project" },
  { cmd: "voss run app.voss", desc: "Compile and execute" },
  { cmd: "voss compile app.voss", desc: "Emit readable Python" },
  { cmd: "voss check app.voss", desc: "Type-check without running" },
  { cmd: 'voss do "summarize this PR"', desc: "One-shot agent task" },
  { cmd: "voss chat", desc: "Interactive REPL" },
  { cmd: "voss doctor", desc: "Diagnose your environment" },
];
