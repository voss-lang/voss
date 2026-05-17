import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Boxes, CircleDollarSign, Code2, Network, Workflow } from "lucide-react";
import { codeToHtml } from "shiki";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: `Language — ${site.name}`,
  description: "The Voss language surface: confidence, context, semantic routing, budgets, and agents as first-class constructs.",
};

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
              <h2 className="display text-4xl sm:text-5xl">The five constructs.</h2>
              <p className="mt-4 text-[var(--muted)]">
                These are the pieces Voss treats as first-class instead of framework convention.
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
      </main>
      <Footer />
    </>
  );
}
