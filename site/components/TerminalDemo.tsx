import { codeToHtml } from "shiki";
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

type Props = {
  title?: string;
  className?: string;
};

// Server component — shiki runs at build time, ships zero JS.
export default async function TerminalDemo({
  title = "~/voss-app — voss do",
  className = "",
}: Props) {
  const html = await codeToHtml(SAMPLE_SESSION, {
    lang: "shellsession",
    theme: "github-dark-default",
  });
  return (
    <Terminal title={title} className={className}>
      <div
        className="overflow-x-auto p-6 text-[13px] leading-relaxed"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </Terminal>
  );
}
