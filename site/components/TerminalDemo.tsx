import { Fragment, type ReactNode } from "react";
import Terminal from "./Terminal";

export const SAMPLE_SESSION = `$ voss do --mode=auto "add a /healthz endpoint and a test for it"

[plan]   confidence 0.92
  1. fs_grep "FastAPI\\(" → app/main.py
  2. fs_edit app/main.py → add @app.get("/healthz")
  3. fs_write tests/test_health.py → pytest case
  4. shell_run pytest tests/test_health.py -q

[edit]   app/main.py        +4 -0    ✓ allow (mode=auto)
[write]  tests/test_health.py +12     ✓ allow (mode=auto)
[shell]  pytest tests/test_health.py -q
         1 passed in 0.18s              ✓

done. token spend: 4,128 / budget 8,000 — saved as session 0193…`;

// Python-esque palette (github-dark family). One stable color per token kind.
const C = {
  prompt: "#8b949e",
  command: "#7ee787", // voss / subcommand — keyword
  tool: "#79c0ff", // fs_grep, shell_run — function call
  string: "#a5d6ff",
  number: "#f2cc60",
  tag: "#d2a8ff", // [plan] [edit] [write] [shell]
  flag: "#ffa657", // --mode=auto
  path: "#56d4bb", // app/main.py
  ok: "#3fb950", // ✓
  muted: "#6e7681", // → and trailing notes
  text: "#c9d1d9",
} as const;

// Order matters: earlier patterns win.
const RULES: { re: RegExp; color: string }[] = [
  { re: /^"[^"]*"/, color: C.string },
  { re: /^\[[a-z]+\]/, color: C.tag },
  { re: /^--[a-z][\w-]*(?:=[^\s]+)?/, color: C.flag },
  { re: /^[a-z]+_[a-z_]+\b/, color: C.tool },
  { re: /^[\w./-]+\.py\b/, color: C.path },
  { re: /^[+-]?\d[\d,]*(?:\.\d+)?s?/, color: C.number },
  { re: /^✓/, color: C.ok },
  { re: /^[→—]/, color: C.muted },
];

function tokenize(line: string, key: number): ReactNode {
  // Prompt line: "$ voss do …" — color $ + first two words as command.
  let rest = line;
  const head: ReactNode[] = [];
  const prompt = rest.match(/^\$ /);
  if (prompt) {
    head.push(
      <span key="p" style={{ color: C.prompt }}>
        ${" "}
      </span>,
    );
    rest = rest.slice(2);
    const cmd = rest.match(/^voss(?:\s+\w+)?/);
    if (cmd) {
      head.push(
        <span key="c" style={{ color: C.command }}>
          {cmd[0]}
        </span>,
      );
      rest = rest.slice(cmd[0].length);
    }
  }

  const out: ReactNode[] = [...head];
  let buf = "";
  let i = 0;
  const flush = () => {
    if (buf) {
      out.push(
        <span key={`t${i}`} style={{ color: C.text }}>
          {buf}
        </span>,
      );
      buf = "";
    }
  };

  while (rest.length > 0) {
    let matched = false;
    for (const { re, color } of RULES) {
      const m = rest.match(re);
      if (m) {
        flush();
        out.push(
          <span key={`m${i}`} style={{ color }}>
            {m[0]}
          </span>,
        );
        rest = rest.slice(m[0].length);
        i += 1;
        matched = true;
        break;
      }
    }
    if (!matched) {
      buf += rest[0];
      rest = rest.slice(1);
    }
  }
  flush();
  return <Fragment key={key}>{out}</Fragment>;
}

type Props = {
  title?: string;
  className?: string;
};

// Server component — tokenizes at build time, ships zero JS.
export default function TerminalDemo({
  title = "~/voss-app — voss do",
  className = "",
}: Props) {
  const lines = SAMPLE_SESSION.split("\n");
  return (
    <Terminal title={title} className={className}>
      <pre className="overflow-x-auto p-6 font-mono text-[13px] leading-relaxed">
        <code>
          {lines.map((line, idx) => (
            <Fragment key={idx}>
              {line ? tokenize(line, idx) : " "}
              {idx < lines.length - 1 ? "\n" : null}
            </Fragment>
          ))}
        </code>
      </pre>
    </Terminal>
  );
}
