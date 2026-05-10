import { codeToHtml } from "shiki";
import { cliExamples, type CliExample } from "@/content/cli-examples";
import CliShowcaseTabs, { type RenderedExample } from "./CliShowcaseTabs";

export default async function CliShowcase() {
  const rendered: RenderedExample[] = await Promise.all(
    cliExamples.map(async (ex: CliExample) => ({
      ...ex,
      html: await codeToHtml(ex.code.trimEnd(), {
        lang: ex.lang,
        theme: "github-dark-default",
      }),
    })),
  );

  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mb-10 max-w-2xl">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Three patterns. One CLI.
          </h2>
          <p className="mt-4 text-[var(--muted)]">
            Run any example from the <code className="font-mono text-[var(--foreground)]">examples/</code>{" "}
            folder. The compiler accepts <code className="font-mono">.voss</code> source; the runtime works with raw
            Python today.
          </p>
        </div>
        <CliShowcaseTabs examples={rendered} />
      </div>
    </section>
  );
}
