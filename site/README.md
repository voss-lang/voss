# Voss Marketing Site

Developer-facing marketing landing page plus a separate Mintlify docs project for [Voss](../README.md).

## Stack

- **Next.ts 16** (App Router, Turbopack) — TypeScript
- **Tailwind CSS v4**
- **shadcn/ui primitives** — local Button/Badge components in `components/ui/`
- **Shiki** — build-time syntax highlighting (zero runtime JS)
- **Static export** (`output: "export"`) — deploys anywhere, intended for **Cloudflare Pages**
- **Mintlify** — public developer docs under `site/docs/`

## Layout

```
site/
├── app/
│   ├── layout.tsx          # Root: fonts, metadata, dark theme
│   ├── page.tsx            # Landing page composition
│   ├── docs/page.tsx       # Handoff page to Mintlify docs
│   └── globals.css         # Tailwind + accent CSS variables
├── components/
│   ├── Nav.tsx             # Wordmark + nav
│   ├── Hero.tsx            # H1, install snippet, PRD CTA
│   ├── FeatureGrid.tsx     # 5 first-class constructs
│   ├── CliShowcase.tsx     # Server: shiki-render examples
│   ├── CliShowcaseTabs.tsx # Client: tab switcher
│   ├── CommandList.tsx     # CLI verb reference
│   ├── InstallTabs.tsx     # pip / cargo / brew tabs
│   ├── ui/                 # shadcn/ui primitives
│   ├── CodeBlock.tsx       # Reusable shiki block
│   ├── CopyButton.tsx      # Clipboard helper
│   └── Footer.tsx
├── branding/voss-mark-ignite-2048.png # Transparent Voss mark
├── content/cli-examples.ts # Hero examples (mirrors examples/raw_python/)
├── docs/                   # Mintlify docs project
│   ├── docs.json           # Mintlify site config and navigation
│   ├── index.mdx           # Docs landing page
│   ├── get-started/        # Install, quickstart, first task/edit
│   ├── harness/            # Harness concepts, commands, modes, tools
│   ├── language/           # .voss workflow-control docs
│   ├── guides/             # Task-oriented workflows
│   ├── reference/          # CLI/config/troubleshooting reference
│   ├── security/           # Trust and execution model
│   └── roadmap/            # v0.1 M-phase roadmap
├── lib/site.ts             # Strings: tagline, repo URL, version
├── public/logo.svg         # Fallback Voss mark
└── next.config.ts          # static export config
```

## Develop

```bash
cd site
npm install
npm run dev          # http://localhost:3000
```

## Develop Docs

Mintlify expects commands to run from the directory containing `docs.json`. The package scripts handle that.

```bash
npm i -g mint
cd site
npm run docs:dev
```

The marketing site points Docs links at `site.docsUrl` in `lib/site.ts` (`https://docs.voss.dev` by default).

## Build

```bash
npm run build        # static export to ./out
npx serve out        # smoke-test the static bundle
```

## Validate Docs

```bash
npm run docs:validate
npm run docs:links
npm run docs:a11y
```

## Deploy (Cloudflare Pages)

- Build command: `npm run build`
- Output directory: `out`
- Root directory: `site`

## Deploy Docs (Mintlify)

- Docs root directory: `site/docs`
- Config file: `site/docs/docs.json`
- Intended public URL: `https://docs.voss.dev`
- Keep docs deployment separate from the Next static export.

## Open items

- Docs domain wiring — `site.docsUrl` currently points to `https://docs.voss.dev`
- Replace `examples/raw_python/*.py` snippets in `content/cli-examples.ts` with `.voss` source once the compiler ships
