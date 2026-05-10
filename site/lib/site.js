export const site = {
  name: "Voss",
  tagline: "A language for AI workflows.",
  description:
    "Voss makes confidence checking, token budgets, prompt construction, semantic routing, and agent lifecycle first-class language constructs — not boilerplate you write in every project.",
  repoUrl: "https://github.com/your-org/voss",
  prdUrl: "https://github.com/your-org/voss/blob/main/PRD.md",
  version: "0.1.0-pre",
  install: {
    primary: 'pip install -e ".[dev]"',
    primaryNote: "From the cloned repo. PyPI release with v1.",
  },
};

export const features = [
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
];

export const cliCommands = [
  { cmd: "voss init", desc: "Scaffold a new project" },
  { cmd: "voss run app.voss", desc: "Compile and execute" },
  { cmd: "voss compile app.voss", desc: "Emit readable Python" },
  { cmd: "voss check app.voss", desc: "Type-check without running" },
  { cmd: 'voss do "summarize this PR"', desc: "One-shot agent task" },
  { cmd: "voss chat", desc: "Interactive REPL" },
  { cmd: "voss doctor", desc: "Diagnose your environment" },
];
