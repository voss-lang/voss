import { codeToHtml, type BundledLanguage } from "shiki";

type Props = {
  code: string;
  lang?: BundledLanguage;
  className?: string;
};

// Server component — shiki runs at build time, ships zero JS.
export default async function CodeBlock({
  code,
  lang = "python",
  className = "",
}: Props) {
  const html = await codeToHtml(code.trimEnd(), {
    lang,
    theme: "github-dark-default",
  });
  return (
    <div
      className={`overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 ${className}`}
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
