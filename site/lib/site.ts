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
  tagline: "A coding harness for bounded AI work.",
  description:
    "Voss is a terminal-native AI coding harness for bounded repo work, with a .voss control language for confidence-aware, budget-bounded workflows.",
  repoUrl: "https://github.com/bm9797/Voss",
  prdUrl: "https://github.com/bm9797/Voss/blob/main/PRD.md",
  // Public Mintlify docs (repo voss-lang/voss, site/docs, branch master).
  docsUrl: "https://docs.tryvoss.dev",
  install: {
    primary: "npm i -g @vosslang/cli",
    primaryNote: "Bundles the Voss Python harness with vendored Python 3.12.",
  },
} as const;

export const features: readonly Feature[] = [
  {
    name: "probable<T>",
    title: "Confidence as a type",
    body:
      "Calls to a model return a value with a confidence score. Gates like `if intent @ 0.80` are checked by the compiler, so low-confidence output cannot slip through silently.",
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
      "One runtime, swappable providers. Your Voss program does not care which model is behind it. Switch with config, not a rewrite.",
  },
  {
    name: "compile",
    title: "Readable Python out",
    body:
      "Voss compiles to debuggable Python you can read, diff, and own. No black-box runtime or hidden magic. Your generated code stays shippable.",
  },
];

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
  { cmd: "voss init", desc: "Scaffold a new project" },
  { cmd: "voss run app.voss", desc: "Compile and execute" },
  { cmd: "voss compile app.voss", desc: "Emit readable Python" },
  { cmd: "voss check app.voss", desc: "Type-check without running" },
  { cmd: 'voss do "summarize this PR"', desc: "One-shot agent task" },
  { cmd: "voss chat", desc: "Interactive REPL" },
  { cmd: "voss doctor", desc: "Diagnose your environment" },
];
