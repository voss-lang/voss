# Voss Marketing Site

Developer-facing marketing landing page + docs shell for [Voss](../README.md).

## Stack

- **Next.ts 16** (App Router, Turbopack) — TypeScript
- **Tailwind CSS v4**
- **Shiki** — build-time syntax highlighting (zero runtime JS)
- **Static export** (`output: "export"`) — deploys anywhere, intended for **Cloudflare Pages**

## Layout

```
site/
├── app/
│   ├── layout.tsx          # Root: fonts, metadata, dark theme
│   ├── page.tsx            # Landing page composition
│   ├── docs/page.tsx       # Docs placeholder (planned TOC)
│   └── globals.css         # Tailwind + accent CSS variables
├── components/
│   ├── Nav.tsx             # Wordmark + nav
│   ├── Hero.tsx            # H1, install snippet, PRD CTA
│   ├── FeatureGrid.tsx     # 5 first-class constructs
│   ├── CliShowcase.tsx     # Server: shiki-render examples
│   ├── CliShowcaseTabs.tsx # Client: tab switcher
│   ├── CommandList.tsx     # CLI verb reference
│   ├── InstallTabs.tsx     # pip / cargo / brew tabs
│   ├── CodeBlock.tsx       # Reusable shiki block
│   ├── CopyButton.tsx      # Clipboard helper
│   └── Footer.tsx
├── content/cli-examples.ts # Hero examples (mirrors examples/raw_python/)
├── lib/site.ts             # Strings: tagline, repo URL, version
├── public/logo.svg         # Placeholder wordmark
└── next.config.ts          # static export config
```

## Develop

```bash
cd site
npm install
npm run dev          # http://localhost:3000
```

## Build

```bash
npm run build        # static export to ./out
npx serve out        # smoke-test the static bundle
```

## Deploy (Cloudflare Pages)

- Build command: `npm run build`
- Output directory: `out`
- Root directory: `site`

## Open items

- Logo / final color scheme — accent currently `#7c5cff`, themed via `app/globals.css` (`--accent`)
- Final repo URL — placeholder `https://github.com/your-org/voss` in `lib/site.ts`
- Docs content — `app/docs/page.tsx` is a placeholder with planned section list
- Replace `examples/raw_python/*.py` snippets in `content/cli-examples.ts` with `.voss` source once the compiler ships
