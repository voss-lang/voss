import type { Metadata } from "next";
import Link from "next/link";
import { codeToHtml } from "shiki";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import CopyButton from "@/components/CopyButton";
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

const PERMISSION_MATRIX = [
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
          <div className="glow absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto max-w-6xl px-6 pt-24 pb-20 sm:pt-32 sm:pb-24">
            <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 font-mono text-xs text-[var(--muted)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
              voss harness
            </p>
            <h1 className="text-balance text-5xl font-semibold tracking-tight sm:text-6xl">
              Ship AI features without becoming an SRE.
            </h1>
            <p className="mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-[var(--muted)]">
              {harness.description}
            </p>
            <div className="mt-10 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
              <div className="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-3 font-mono text-sm">
                <span className="text-[var(--accent)]">$</span>
                <span className="select-all">voss do &quot;ship the login flow&quot;</span>
                <CopyButton text='voss do "ship the login flow"' />
              </div>
              <Link
                href="#install"
                className="inline-flex items-center justify-center rounded-lg border border-[var(--border)] px-4 py-3 text-sm transition hover:border-[var(--accent)]"
              >
                Install →
              </Link>
            </div>
          </div>
        </section>

        {/* Pitch bullets */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-16">
            <div className="grid gap-4 sm:grid-cols-3">
              {harness.pitch.map((p, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
                >
                  <p className="font-mono text-xs text-[var(--accent)]">{`0${i + 1}`}</p>
                  <p className="mt-2 text-sm leading-relaxed text-[var(--foreground)]">{p}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Sample transcript */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-8 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                A turn looks like this
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                Plan, edit, run, verify.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                Each turn is a confidence-gated plan, gated tool calls, and a verification step. You
                see what it&apos;s going to do before it does it.
              </p>
            </div>
            <div
              className="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-sm"
              // eslint-disable-next-line react/no-danger
              dangerouslySetInnerHTML={{ __html: sessionHtml }}
            />
          </div>
        </section>

        {/* Features */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                Built for AI-first builders.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                You&apos;re shipping AI inside a product. The harness is the agent that helps you do
                it — without leaving the terminal, without a second subscription, without
                surrendering your repo.
              </p>
            </div>
            <div className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] sm:grid-cols-2 lg:grid-cols-3">
              {harnessFeatures.map((f) => (
                <div
                  key={f.title}
                  className="bg-[var(--surface)] p-6 transition hover:bg-[var(--surface-2)]"
                >
                  <h3 className="text-lg font-medium">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">{f.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Permissions */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-10 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Permissions
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                Three modes. Persistent decisions.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                Every project gets its own permission record at{" "}
                <code className="font-mono">~/.config/voss/permissions.json</code>. Grant once,
                ship.
              </p>
            </div>
            <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]">
              <table className="w-full text-left text-sm">
                <thead className="bg-[var(--surface-2)] text-[var(--muted)]">
                  <tr>
                    <th className="px-5 py-3 font-mono text-xs uppercase tracking-wider">mode</th>
                    <th className="px-5 py-3 font-mono text-xs uppercase tracking-wider">reads</th>
                    <th className="px-5 py-3 font-mono text-xs uppercase tracking-wider">writes</th>
                    <th className="px-5 py-3 font-mono text-xs uppercase tracking-wider">shell</th>
                    <th className="px-5 py-3 font-mono text-xs uppercase tracking-wider">use when</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {PERMISSION_MATRIX.map((row) => (
                    <tr key={row.mode} className="font-mono">
                      <td className="px-5 py-4 text-[var(--accent)]">{row.mode}</td>
                      <td className="px-5 py-4">{row.reads}</td>
                      <td className="px-5 py-4">{row.writes}</td>
                      <td className="px-5 py-4">{row.shell}</td>
                      <td className="px-5 py-4 font-sans text-[var(--muted)]">{row.desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Auth */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-10 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">Auth</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                Three ways in. Subscription-first.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                If you already pay Anthropic or OpenAI for a coding tool, you don&apos;t need to pay
                them twice.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              {AUTH_PATHS.map((a) => (
                <div
                  key={a.name}
                  className="flex flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
                >
                  <h3 className="text-base font-medium">{a.name}</h3>
                  <p className="mt-2 grow text-sm leading-relaxed text-[var(--muted)]">{a.detail}</p>
                  <pre className="mt-4 overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--background)] p-3 font-mono text-[12px] text-[var(--foreground)]">
{a.cmd}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Commands */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-10 max-w-2xl">
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                The verbs you&apos;ll actually use.
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
              <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                Try it in a repo.
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
                  className="rounded-lg border border-[var(--accent)] bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90"
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
