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
          <h2 className="display text-4xl sm:text-5xl">
            Three workflows. <span className="em">One control layer.</span>
          </h2>
          <p className="mt-4 text-[var(--muted)]">
            Run the canonical <code className="font-mono text-[var(--foreground)]">samples/</code>{" "}
            programs with <code className="font-mono">voss run</code>, or compare them with the raw
            Python equivalents in <code className="font-mono">examples/raw_python/</code>.
          </p>
        </div>
        <CliShowcaseTabs examples={rendered} />
      </div>
    </section>
  );
}
