import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  CircleDollarSign,
  Code2,
  Database,
  FileCheck2,
  Network,
  RefreshCcw,
  ShieldCheck,
  Users,
  Workflow,
} from "lucide-react";
import { codeToHtml } from "shiki";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { pageMetadata } from "@/lib/metadata";
import { site } from "@/lib/site";

export const metadata = pageMetadata({
  title: `Language - ${site.name}`,
  description:
    "The Voss language surface: confidence, context, semantic routing, budgets, and agents as first-class constructs.",
  path: "/language",
});

const CONSTRUCTS = [
  {
    name: "probable<T>",
    icon: Code2,
    title: "Confidence belongs in the type system",
    body: "Model calls return values with confidence attached. Gates like `intent @ 0.80` make trust explicit instead of burying it in app code.",
  },
  {
    name: "ctx",
    icon: Boxes,
    title: "Prompt windows are scoped resources",
    body: "Context blocks define token budgets, inputs, compression, and eviction as part of the program structure.",
  },
  {
    name: "match similar",
    icon: Network,
    title: "Semantic routing is declarative",
    body: "Route by meaning with embedding indexes prepared ahead of runtime, not by sprinkling ad hoc similarity calls through handlers.",
  },
  {
    name: "within budget",
    icon: CircleDollarSign,
    title: "Cost limits are control flow",
    body: "Budgets and fallbacks are explicit language constructs, so overruns have a designed path instead of a surprise bill.",
  },
  {
    name: "spawn / gather",
    icon: Workflow,
    title: "Agents compose like concurrent tasks",
    body: "Parallel agent work, timeouts, and fallbacks are written directly, with the runtime owning lifecycle and coordination.",
  },
] as const;

const COORDINATION = [
  {
    name: "principles { }",
    icon: ShieldCheck,
    title: "Engineering culture as config",
    body: "Declare the principles every agent inherits — smallest diff, no claim without evidence, stay in scope. They compile to immutable config and are recorded in the audit.",
  },
  {
    name: "team \"name\" { }",
    icon: Users,
    title: "The roster is the source of truth",
    body: "Roles, scope, budget, tools, and model tier compile to a frozen team config. The EM can only dispatch to declared roles, and scope can never widen past the ceiling.",
  },
  {
    name: "gate done { }",
    icon: Workflow,
    title: "Completion has requirements",
    body: "A done gate names what must hold before a card ships: tests passed, independent review, evidence references. Agents can't mark their own work done.",
  },
  {
    name: "memory { }",
    icon: Database,
    title: "Institutional knowledge has a home",
    body: "Point decisions, sessions, and semantic memory at durable paths so context — and the session tree — survives across runs.",
  },
] as const;

const LANGUAGE_PROGRESS = [
  {
    title: "Failure paths are explicit",
    body: "Retries, fail-fast gathers, budget fallbacks, and bounded review loops are becoming part of the workflow model instead of hidden control flow.",
    icon: RefreshCcw,
  },
  {
    title: "Editor help is arriving",
    body: "Formatting, completions, hover text, and go-to-definition make .voss files easier to read and maintain in normal editor workflows.",
    icon: FileCheck2,
  },
  {
    title: "Context stays budgeted",
    body: "The roadmap treats long-running context as a budgeted resource: recent work stays detailed, older work is summarized, and savings must be measurable.",
    icon: CircleDollarSign,
  },
] as const;

const COORD_SAMPLE = `gate done {
  require tests_passed
  require independent_review
  require evidence_refs
}

memory {
  decisions: ".voss/decisions"
  sessions:  ".voss/sessions"
  semantic:  ".voss-cache/semantic"
}`;

const SAMPLE = `agent Classifier {
  ctx(token_budget: 1000) {
    intent = ask "Classify this request" probable<string>

    if intent @ 0.80 {
      return intent.value
    }

    fallback "unknown"
  }
}`;

export default async function LanguagePage() {
  const sampleHtml = await codeToHtml(SAMPLE.trimEnd(), {
    lang: "python",
    theme: "github-dark-default",
  });
  const coordHtml = await codeToHtml(COORD_SAMPLE.trimEnd(), {
    lang: "python",
    theme: "github-dark-default",
  });

  return (
    <>
      <Nav />
      <main>
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
          <div className="glow absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto grid max-w-6xl gap-10 px-6 pt-24 pb-20 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
            <div>
              <Badge variant="secondary" className="font-mono uppercase tracking-wider">
                Language
              </Badge>
              <h1 className="display mt-5 text-[clamp(2.5rem,6vw,4.5rem)]">
                AI patterns as <span className="em">syntax</span>.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
                Voss is a small AI-native language that compiles to readable Python. The core move
                is turning recurring AI workflow code into explicit constructs the compiler and
                runtime can reason about.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild size="lg">
                  <Link href={site.docsUrl} target="_blank" rel="noreferrer">
                    Read docs
                    <ArrowRight />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg">
                  <Link href={site.prdUrl} target="_blank" rel="noreferrer">
                    PRD
                  </Link>
                </Button>
              </div>
            </div>
            <div
              className="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 font-mono text-sm leading-7 [&_code]:font-mono [&_pre]:!bg-transparent [&_pre]:text-sm [&_pre]:leading-7"
              dangerouslySetInnerHTML={{ __html: sampleHtml }}
            />
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Recent direction
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                More workflow, <span className="em">less ceremony</span>.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                The language track is tightening the parts of agent work that usually leak into
                prompts: failure behavior, editor ergonomics, and context budgets.
              </p>
            </div>
            <div className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] md:grid-cols-3">
              {LANGUAGE_PROGRESS.map((item) => {
                const Icon = item.icon;

                return (
                  <article key={item.title} className="bg-[var(--surface)] p-6">
                    <Icon className="h-6 w-6 text-[var(--accent)]" />
                    <h3 className="mt-5 text-xl font-medium">{item.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{item.body}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Runtime constructs
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">Inside one agent.</h2>
              <p className="mt-4 text-[var(--muted)]">
                The pieces Voss treats as first-class instead of framework convention — confidence,
                context, routing, budget, and concurrency.
              </p>
            </div>
            <div className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] md:grid-cols-2">
              {CONSTRUCTS.map((item) => {
                const Icon = item.icon;

                return (
                  <article key={item.name} className="bg-[var(--surface)] p-6 transition hover:bg-[var(--surface-2)]">
                    <div className="mb-4 flex items-center gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--accent)]">
                        <Icon className="h-5 w-5" />
                      </span>
                      <span className="font-mono text-sm text-[var(--accent)]">{item.name}</span>
                    </div>
                    <h3 className="text-xl font-medium">{item.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{item.body}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Coordination spec
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Across a whole <span className="em">team</span>.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                The same language scales up from one agent to an engineering organization. Roles,
                principles, gates, and memory become declared, compiler-checked coordination — so a
                team run is shorter and clearer than the equivalent Python.
              </p>
            </div>
            <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
              <div className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] sm:grid-cols-2">
                {COORDINATION.map((item) => {
                  const Icon = item.icon;
                  return (
                    <article key={item.name} className="bg-[var(--surface)] p-6 transition hover:bg-[var(--surface-2)]">
                      <div className="mb-4 flex items-center gap-3">
                        <span className="flex h-10 w-10 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--accent)]">
                          <Icon className="h-5 w-5" />
                        </span>
                        <span className="font-mono text-sm text-[var(--accent)]">{item.name}</span>
                      </div>
                      <h3 className="text-lg font-medium">{item.title}</h3>
                      <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{item.body}</p>
                    </article>
                  );
                })}
              </div>
              <div
                className="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 font-mono text-sm leading-7 [&_pre]:!bg-transparent [&_pre]:text-xs [&_pre]:leading-6 sm:[&_pre]:text-sm"
                dangerouslySetInnerHTML={{ __html: coordHtml }}
              />
            </div>
            <div className="mt-10 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/orchestration">
                  See it orchestrate
                  <ArrowRight />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link href={site.prdUrl} target="_blank" rel="noreferrer">
                  PRD
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
