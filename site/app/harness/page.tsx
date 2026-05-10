import type { Metadata } from "next";
import Link from "next/link";
import { codeToHtml } from "shiki";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import CopyButton from "@/components/CopyButton";
import Cursor from "@/components/Cursor";
import Terminal from "@/components/Terminal";
import Reveal, { Stagger, StaggerItem } from "@/components/Reveal";
import { harness, harnessFeatures, harnessCommands, site } from "@/lib/site";

export const metadata: Metadata = {
  title: `Harness — ${site.name}`,
  description: harness.description,
};

const SAMPLE_SESSION = `$ voss do "add a /healthz endpoint and a test for it"

[plan]   confidence 0.92
  1. fs_grep "FastAPI\\(" → app/main.py
  2. fs_edit app/main.py → add @app.get("/healthz")
  3. fs_write tests/test_health.py → pytest case
  4. shell_run pytest tests/test_health.py -q

[edit]   app/main.py        +4 -0    ✓ allow (mode=edit)
[write]  tests/test_health.py +12     ✓ allow (mode=edit)
[shell]  pytest tests/test_health.py -q
         1 passed in 0.18s              ✓

done. token spend: 4,128 / budget 8,000 — saved as session 0193…`;

type PermissionRow = {
  mode: "plan" | "edit" | "auto";
  reads: string;
  writes: string;
  shell: string;
  desc: string;
};

const PERMISSION_MATRIX: PermissionRow[] = [
  { mode: "plan", reads: "auto", writes: "prompt", shell: "prompt", desc: "Inspect a repo without touching it." },
  { mode: "edit", reads: "auto", writes: "scoped", shell: "prompt", desc: "Default. Reads + writes inside cwd, ask before shell." },
  { mode: "auto", reads: "auto", writes: "auto", shell: "auto", desc: "Allowlisted everything. Destructive patterns still prompt." },
];

const AUTH_PATHS = [
  {
    name: "Claude Code OAuth",
    detail: "Reuses your Claude Pro / Max subscription via the Claude Code login. macOS Keychain or ~/.claude/.credentials.json.",
    cmd: "claude login    # then: voss --auth=claude do ...",
  },
  {
    name: "Codex / ChatGPT OAuth",
    detail: "Reuses your ChatGPT subscription via the Codex CLI auth file. Tokens auto-refresh.",
    cmd: "codex login     # then: voss --auth=codex do ...",
  },
  {
    name: "Plain API key",
    detail: "Drop ANTHROPIC_API_KEY or OPENAI_API_KEY in the env. Useful for CI.",
    cmd: 'export ANTHROPIC_API_KEY=sk-ant-...',
  },
];

function valueClass(v: string): string {
  if (v === "auto") return "text-[var(--accent)]";
  if (v === "prompt") return "text-[var(--foreground)]";
  if (v === "scoped") return "text-[var(--foreground)]";
  return "text-[var(--muted)]";
}

export default async function HarnessPage() {
  const sessionHtml = await codeToHtml(SAMPLE_SESSION, {
    lang: "shellsession",
    theme: "github-dark-default",
  });

  return (
    <>
      <Nav />
      <main>
        {/* Hero */}
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
          <div className="glow absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto max-w-6xl px-6 pt-24 pb-20 sm:pt-32 sm:pb-24">
            <Reveal>
              <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 font-mono text-xs text-[var(--muted)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
                voss harness
              </p>
            </Reveal>
            <Reveal delay={0.05}>
              <h1 className="display text-balance text-6xl sm:text-7xl">
                Ship AI features<br />
                <span className="em">without becoming an SRE.</span>
              </h1>
            </Reveal>
            <Reveal delay={0.1}>
              <p className="mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-[var(--muted)]">
                {harness.description}
              </p>
            </Reveal>
            <Reveal delay={0.15}>
              <div className="mt-10 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
                <div className="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-3 font-mono text-sm">
                  <span className="text-[var(--accent)]">$</span>
                  <span className="select-all">voss do &quot;ship the login flow&quot;</span>
                  <Cursor />
                  <CopyButton text='voss do "ship the login flow"' />
                </div>
                <Link
                  href="#install"
                  className="inline-flex items-center justify-center rounded-lg border border-[var(--border)] px-4 py-3 text-sm transition hover:border-[var(--accent)]"
                >
                  Install →
                </Link>
              </div>
            </Reveal>
          </div>
        </section>

        {/* Pitch bullets */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-16">
            <Stagger className="grid gap-4 sm:grid-cols-3">
              {harness.pitch.map((p, i) => (
                <StaggerItem
                  key={i}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
                >
                  <p className="font-mono text-xs text-[var(--accent)]">{`0${i + 1}`}</p>
                  <p className="mt-2 text-sm leading-relaxed text-[var(--foreground)]">{p}</p>
                </StaggerItem>
              ))}
            </Stagger>
          </div>
        </section>

        {/* Sample transcript with terminal chrome */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-8 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                A turn looks like this
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Plan, edit, run, <span className="em">verify</span>.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                Each turn is a confidence-gated plan, gated tool calls, and a verification step. You
                see what it&apos;s going to do before it does it.
              </p>
            </div>
            <Terminal title="~/voss-app — voss do">
              <div
                className="overflow-x-auto p-6 text-sm"
                // eslint-disable-next-line react/no-danger
                dangerouslySetInnerHTML={{ __html: sessionHtml }}
              />
            </Terminal>
          </div>
        </section>

        {/* Features */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <h2 className="display text-4xl sm:text-5xl">
                Built for <span className="em">AI-first builders</span>.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                You&apos;re shipping AI inside a product. The harness is the agent that helps you do
                it — without leaving the terminal, without a second subscription, without
                surrendering your repo.
              </p>
            </div>
            <Stagger className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] sm:grid-cols-2 lg:grid-cols-3">
              {harnessFeatures.map((f) => (
                <StaggerItem
                  key={f.title}
                  className="bg-[var(--surface)] p-6 transition hover:bg-[var(--surface-2)]"
                >
                  <h3 className="text-lg font-medium">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">{f.body}</p>
                </StaggerItem>
              ))}
            </Stagger>
          </div>
        </section>

        {/* Permissions — redesigned as styled rows with hover accent strip */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-10 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Permissions
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Three modes. <span className="em">Persistent decisions.</span>
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                Every project gets its own permission record at{" "}
                <code className="font-mono text-[var(--foreground)]">
                  ~/.config/voss/permissions.json
                </code>
                . Grant once, ship.
              </p>
            </div>

            <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]">
              {/* header row */}
              <div className="hidden grid-cols-[140px_1fr_1fr_1fr_2.2fr] items-center gap-6 border-b border-[var(--border)] bg-[var(--surface-2)] px-6 py-3 font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--muted)] sm:grid">
                <span>mode</span>
                <span>reads</span>
                <span>writes</span>
                <span>shell</span>
                <span>use when</span>
              </div>

              {PERMISSION_MATRIX.map((row) => (
                <div
                  key={row.mode}
                  className="group relative grid grid-cols-2 items-center gap-4 border-b border-[var(--border)] px-6 py-5 last:border-b-0 transition hover:bg-[var(--surface-2)] sm:grid-cols-[140px_1fr_1fr_1fr_2.2fr] sm:gap-6"
                >
                  <span className="absolute left-0 top-0 h-full w-[3px] origin-top scale-y-0 bg-[var(--accent)] transition-transform duration-300 group-hover:scale-y-100" />

                  <div className="col-span-2 sm:col-span-1">
                    <span className="inline-flex items-center rounded-md border border-[var(--accent)]/40 bg-[var(--accent-soft)] px-2.5 py-1 font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                      {row.mode}
                    </span>
                  </div>

                  <Cell label="reads" value={row.reads} className={valueClass(row.reads)} />
                  <Cell label="writes" value={row.writes} className={valueClass(row.writes)} />
                  <Cell label="shell" value={row.shell} className={valueClass(row.shell)} />

                  <p className="col-span-2 text-sm text-[var(--muted)] sm:col-span-1">{row.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Auth */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-10 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">Auth</p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Three ways in. <span className="em">Subscription-first.</span>
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                If you already pay Anthropic or OpenAI for a coding tool, you don&apos;t need to pay
                them twice.
              </p>
            </div>
            <Stagger className="grid gap-4 sm:grid-cols-3">
              {AUTH_PATHS.map((a) => (
                <StaggerItem
                  key={a.name}
                  className="flex flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
                >
                  <h3 className="text-base font-medium">{a.name}</h3>
                  <p className="mt-2 grow text-sm leading-relaxed text-[var(--muted)]">{a.detail}</p>
                  <pre className="mt-4 overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--background)] p-3 font-mono text-[12px] text-[var(--foreground)]">
{a.cmd}
                  </pre>
                </StaggerItem>
              ))}
            </Stagger>
          </div>
        </section>

        {/* Commands */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-10 max-w-2xl">
              <h2 className="display text-4xl sm:text-5xl">
                The verbs you&apos;ll <span className="em">actually use</span>.
              </h2>
            </div>
            <ul className="divide-y divide-[var(--border)] overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] font-mono text-sm">
              {harnessCommands.map((c) => (
                <li
                  key={c.cmd}
                  className="flex flex-col gap-1 px-5 py-4 transition hover:bg-[var(--surface-2)] sm:flex-row sm:items-center sm:justify-between"
                >
                  <span>
                    <span className="text-[var(--accent)]">$ </span>
                    {c.cmd}
                  </span>
                  <span className="text-xs text-[var(--muted)] sm:text-sm">{c.desc}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Install */}
        <section id="install" className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-10 sm:p-14">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Install
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Try it <span className="em">in a repo</span>.
              </h2>
              <p className="mt-4 max-w-2xl text-[var(--muted)]">
                Clone Voss, install in editable mode, log into your Claude or Codex account, and run{" "}
                <code className="font-mono text-[var(--foreground)]">voss doctor</code> to verify.
              </p>
              <pre className="mt-6 overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--background)] p-5 font-mono text-sm text-[var(--foreground)]">
{`git clone ${site.repoUrl}
cd voss
${site.install.primary}
voss doctor`}
              </pre>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  href="/docs"
                  className="rounded-lg border border-[var(--accent)] bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-[var(--background)] transition hover:opacity-90"
                >
                  Read the docs
                </Link>
                <Link
                  href="/"
                  className="rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm transition hover:border-[var(--accent)]"
                >
                  About the language
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

function Cell({
  label,
  value,
  className = "",
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className="font-mono text-sm tabular-nums">
      <span className="mb-0.5 block text-[10px] uppercase tracking-widest text-[var(--muted)] sm:hidden">
        {label}
      </span>
      <span className={className}>{value}</span>
    </div>
  );
}
