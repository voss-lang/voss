# Voss Marketing Site

Developer-facing marketing landing page + docs shell for [Voss](../README.md).

## Stack

- **Next.js 16** (App Router, Turbopack) — JavaScript, no TypeScript
- **Tailwind CSS v4**
- **Shiki** — build-time syntax highlighting (zero runtime JS)
- **Static export** (`output: "export"`) — deploys anywhere, intended for **Cloudflare Pages**

## Layout

```
site/
├── app/
│   ├── layout.jsx          # Root: fonts, metadata, dark theme
│   ├── page.jsx            # Landing page composition
│   ├── docs/page.jsx       # Docs placeholder (planned TOC)
│   └── globals.css         # Tailwind + accent CSS variables
├── components/
│   ├── Nav.jsx             # Wordmark + nav
│   ├── Hero.jsx            # H1, install snippet, PRD CTA
│   ├── FeatureGrid.jsx     # 5 first-class constructs
│   ├── CliShowcase.jsx     # Server: shiki-render examples
│   ├── CliShowcaseTabs.jsx # Client: tab switcher
│   ├── CommandList.jsx     # CLI verb reference
│   ├── InstallTabs.jsx     # pip / cargo / brew tabs
│   ├── CodeBlock.jsx       # Reusable shiki block
│   ├── CopyButton.jsx      # Clipboard helper
│   └── Footer.jsx
├── content/cli-examples.js # Hero examples (mirrors examples/raw_python/)
├── lib/site.js             # Strings: tagline, repo URL, version
├── public/logo.svg         # Placeholder wordmark
└── next.config.mjs         # static export config
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
- Final repo URL — placeholder `https://github.com/your-org/voss` in `lib/site.js`
- Docs content — `app/docs/page.jsx` is a placeholder with planned section list
- Replace `examples/raw_python/*.py` snippets in `content/cli-examples.js` with `.voss` source once the compiler ships
