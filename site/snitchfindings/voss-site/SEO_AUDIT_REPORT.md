# SEO & Marketing Audit — Voss site

**Audited by Snitch: Marketing** · on-page suite (source mode)

```
audit_mode_detected: source
stack_detected:      Next.js 16.2.6 App Router, static export (output: "export"), Tailwind v4, PostHog
target:              /Users/benjaminmarks/Projects/Voss/site
categories_scanned:  on-page suite — indexability, meta/OG, headings, images,
                     structured data, AI-search/llms.txt, CWV contributors,
                     analytics/consent, accessibility-as-SEO, 404/internal linking
off_site:            skipped (brand maturity: minimal — no off-site surface to audit)
methodology_note:    findings derived from direct source reads (Read/Grep). Built-in
                     SEO rules applied; per-category guidance files not individually loaded.
html_render:         see SEO_AUDIT_REPORT.html
```

---

## Executive snapshot

**Bottleneck:** the site is well-built on-page (per-route titles, descriptive alt text, explicit image dimensions, security headers, a clean llms.txt) but has **no machine-readable crawl surface** — no `sitemap.xml`, no `robots.txt`, no canonical tags, and no structured data — so search engines and AI crawlers have to infer everything.

**The fix:** add the four Next.js file-conventions that static export supports out of the box (`app/sitemap.ts`, `app/robots.ts`, per-page `alternates.canonical`, one JSON-LD block) plus an OG image. All are additive, none touch existing layout.

**This week:** confirm the production domain (see Validity Precondition below — `metadataBase` says `voss.dev`, docs say `tryvoss.dev`), then ship sitemap + robots + canonical in one commit.

**Top 3 findings:**
1. **High** — No `sitemap.xml` and no `robots.txt` (zero crawl directives, no sitemap pointer).
2. **High** — `twitter.card: "summary_large_image"` declared with no OG/Twitter image anywhere → blank social cards.
3. **High** — Subpage Open Graph titles all inherit the homepage OG title (child routes set `title`/`description` but never `openGraph`).

Read the rest if you want the canonical-tag gap, the missing structured data, the 404 page, the consent/analytics no-op, and the font/bundle CWV contributors.

---

## Critical unknowns & validity preconditions

| # | Unknown | Why it matters | Type |
|---|---------|----------------|------|
| 1 | **Is the production marketing domain actually `voss.dev`?** | `app/layout.tsx:18` sets `metadataBase: new URL("https://voss.dev")` and `public/llms.txt` uses `https://voss.dev/*` absolute URLs — but `lib/site.ts:19` points docs at `https://docs.tryvoss.dev` and the repo is `bm9797/Voss`. If the site deploys to `tryvoss.dev` (or anything other than `voss.dev`), **every** canonical, OG URL, and llms.txt link resolves to the wrong host. | **Validity precondition** — invalidates the OG/canonical/llms approach if wrong, not just a tweak. |
| 2 | Is there a consent/cookie banner anywhere in the deploy? | PostHog is initialised with `opt_out_capturing_by_default: true` (`components/PostHogProvider.tsx`) and no opt-in UI exists in source. If there's no banner, analytics captures **nothing** in production. | Changes whether analytics findings are "broken" or "intentional". |
| 3 | Is `public/_headers` (Netlify/Cloudflare format) actually applied? | `.vercel/` is present and `vercel.json` carries its own headers. On Vercel, `public/_headers` is served as a static file, not interpreted — so the two header sets may diverge silently. | Affects which CSP/security headers are live. |

---

## Site context

- **Purpose:** marketing / product site for **Voss**, a terminal-native AI coding harness + `.voss` control language for bounded, budget-aware agent workflows.
- **Business model:** developer tool (npm `@vosslang/cli`); conversion = install command copy + outbound to docs/GitHub/PRD (tracked via PostHog `outbound_click` / `copy_install_command`).
- **Primary conversion:** copy the install command (`Hero.tsx`, `InstallTabs.tsx`) and click through to docs/GitHub.
- **Audience:** engineers evaluating AI agent tooling.
- **Surfaces (8 routes):** `/`, `/harness`, `/ade`, `/language`, `/security`, `/roadmap`, `/orchestration`, `/audit`. All statically exported.

## Assumptions — confirm before acting

| Assumption | Basis | Risk if wrong |
|------------|-------|---------------|
| Production host is `voss.dev` | `metadataBase` + llms.txt | OG/canonical/llms all point to wrong domain (see Precondition 1) |
| Brand is pre-launch / minimal off-site presence | no social/backlink config in source | Off-site cats skipped; revisit post-launch |
| Deploy target is Vercel | `.vercel/`, `vercel.json` | `_headers` file assumptions change |

---

## Findings

### Finding 1 — No `sitemap.xml`

- **SEO Impact:** High
- **Surface:** Source
- **Evidence:** Verified via `ls app/sitemap.ts public/sitemap.xml` and `find app public -iname "*sitemap*"` → **0 matches**. Scope: full `app/` and `public/` trees. No `app/sitemap.ts` (Next.js sitemap file-convention, which **does** emit a static `sitemap.xml` under `output: "export"`) and no hand-written `public/sitemap.xml`.
- **Risk:** Search engines must discover all 8 routes purely by crawling internal links. New or orphan-ish routes (`/orchestration`, `/audit`, `/roadmap`) get slower, less reliable indexing, and you lose `lastmod` signals. AI crawlers (which increasingly read sitemaps) get no canonical route list.
- **Fix:** Add `app/sitemap.ts` — emits `sitemap.xml` at build under static export:
  ```ts
  import type { MetadataRoute } from "next";

  const base = "https://voss.dev"; // confirm domain first (Precondition 1)
  const routes = ["", "/harness", "/ade", "/language", "/security", "/roadmap", "/orchestration", "/audit"];

  export default function sitemap(): MetadataRoute.Sitemap {
    return routes.map((r) => ({
      url: `${base}${r}/`, // trailingSlash: true is set in next.config
      changeFrequency: "weekly",
      priority: r === "" ? 1 : 0.8,
    }));
  }
  ```
- **Priority:** P1 (Quick Win)
- **Confidence:** High
- **Affected pages:** Whole site (all 8 routes undiscoverable via sitemap).

### Finding 2 — No `robots.txt`

- **SEO Impact:** High
- **Surface:** Source
- **Evidence:** Verified via `ls app/robots.ts public/robots.txt` and `find app public -iname "*robots*"` → **0 matches** across `app/` and `public/`. No crawl directives and no sitemap pointer are served.
- **Risk:** Crawlers receive no `Sitemap:` directive (compounding Finding 1) and no explicit allow signal. For a JS-export site this also means AI/LLM crawlers (GPTBot, ClaudeBot, PerplexityBot, Google-Extended) have no declared policy — you can neither invite nor gate them.
- **Fix:** Add `app/robots.ts` (emits `robots.txt` under static export):
  ```ts
  import type { MetadataRoute } from "next";

  export default function robots(): MetadataRoute.Robots {
    return {
      rules: { userAgent: "*", allow: "/" },
      sitemap: "https://voss.dev/sitemap.xml", // confirm domain
    };
  }
  ```
- **Priority:** P1 (Quick Win)
- **Confidence:** High
- **Affected pages:** Whole site.

### Finding 3 — `summary_large_image` declared with no OG/Twitter image

- **SEO Impact:** High
- **Schema.org type:** —
- **Surface:** Source
- **Evidence:** `app/layout.tsx:24-28`
  ```tsx
  twitter: {
    card: "summary_large_image",
    title: `${site.name} - ${site.tagline}`,
    description: site.description,
  },
  ```
  Verified via `grep -rn "og:image|openGraph.*image|images:|twitter.*image|opengraph-image" app/ components/ lib/ public/` and `find app -iname "opengraph-image*" -o -iname "twitter-image*"` → **0 matches**. `openGraph` in `layout.tsx:19-23` has `title/description/type` but no `images`.
- **Risk:** A `summary_large_image` card with no image renders as a blank/large empty card on X, and link unfurls on LinkedIn/Slack/Discord/iMessage fall back to no preview image. For a dev tool shared in exactly those channels, this directly suppresses share CTR.
- **Fix:** Add a 1200×630 image and reference it. Either drop `app/opengraph-image.png` (1200×630) for Next's auto-convention, or add explicit `images` to `layout.tsx` metadata:
  ```tsx
  openGraph: {
    title: `${site.name} - ${site.tagline}`,
    description: site.description,
    type: "website",
    images: [{ url: "/og.png", width: 1200, height: 630, alt: `${site.name} — ${site.tagline}` }],
  },
  twitter: { card: "summary_large_image", /* …inherits images */ },
  ```
- **Priority:** P1 (Quick Win)
- **Confidence:** High
- **Affected pages:** All 8 routes (root `metadata` applies site-wide).

### Finding 4 — Subpage Open Graph titles inherit the homepage OG title

- **SEO Impact:** High
- **Surface:** Source
- **Evidence:** Child routes set only `title` + `description`, never `openGraph`. e.g. `app/security/page.tsx:21-23`:
  ```tsx
  export const metadata: Metadata = {
    title: `Security - ${site.name}`,
    description: "How Voss approaches harness permissions, local credentials, …",
  };
  ```
  Verified via `grep -rn "openGraph" app/*/page.tsx` → **0 matches** in any of the 7 subroutes. Next.js merges child `metadata` over the layout, but `openGraph` is a **separate object**: since children never set `openGraph.title`, all 7 subpages inherit `layout.tsx:20` → `"Voss - The operating layer for AI engineering teams."`
- **Risk:** Sharing `/security`, `/harness`, `/audit`, etc. on any platform shows the **homepage** OG title and description, not the page's. Every deep-link share is mislabelled, flattening the per-page positioning you already wrote.
- **Fix:** Either set `openGraph.title`/`description` per route, or factor a helper so each page's `title`/`description` feed `openGraph`. Minimal per-page form:
  ```tsx
  export const metadata: Metadata = {
    title: `Security - ${site.name}`,
    description: "How Voss approaches harness permissions…",
    openGraph: { title: `Security - ${site.name}`, description: "How Voss approaches harness permissions…" },
  };
  ```
- **Priority:** P2 (Important)
- **Confidence:** High
- **Affected pages:** All 7 subroutes (`/harness`, `/ade`, `/language`, `/security`, `/roadmap`, `/orchestration`, `/audit`).

### Finding 5 — No canonical URLs on any route

- **SEO Impact:** Medium
- **Surface:** Source
- **Evidence:** Verified via `grep -rn "canonical|alternates" app/ lib/` → **0 matches** across all routes and metadata. `metadataBase` is set (`layout.tsx:18`) but no `alternates.canonical` exists anywhere.
- **Risk:** `next.config.ts` sets `trailingSlash: true` and `vercel.json` sets `cleanUrls: true`. That combination can serve a route at more than one path (`/security`, `/security/`, and the `.html` artifact). Without a self-referencing canonical, query-string and UTM variants of every page compete as separate URLs in the index, diluting ranking signals. Self-referencing canonicals also harden against scraper/syndication duplication.
- **Fix:** Add a per-route canonical. With a small helper in `lib/site.ts` or inline:
  ```tsx
  // app/security/page.tsx
  export const metadata: Metadata = {
    title: `Security - ${site.name}`,
    description: "…",
    alternates: { canonical: "/security/" },
  };
  ```
  (Relative path resolves against `metadataBase`. Homepage → `canonical: "/"`.)
- **Priority:** P2 (Important)
- **Confidence:** Medium
- **Affected pages:** All 8 routes.

### Finding 6 — No structured data (JSON-LD)

- **SEO Impact:** Medium
- **Schema.org type:** Organization, SoftwareApplication
- **Surface:** Source
- **Evidence:** Verified via `grep -rn "application/ld+json|@context|schema.org|jsonLd" app/ components/ lib/` → **0 matches**. No `Organization`, no `SoftwareApplication`, no `BreadcrumbList`.
- **Risk:** Google and AI answer engines have no explicit entity to attach to "Voss". For a developer tool, `SoftwareApplication` (with `applicationCategory: DeveloperApplication`, `operatingSystem`, `offers` free) and `Organization` (name, url, logo, sameAs → GitHub) are the two highest-leverage schemas for knowledge-panel eligibility and AI citation. Their absence means the brand entity is inferred, not declared.
- **Fix:** Add a single JSON-LD `<script>` in `app/layout.tsx` (or a `StructuredData` component) emitting `Organization` + `SoftwareApplication`. Static-export safe (renders at build). Example `SoftwareApplication`:
  ```tsx
  <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
    "@context": "https://schema.org", "@type": "SoftwareApplication",
    name: "Voss", applicationCategory: "DeveloperApplication",
    operatingSystem: "macOS, Linux, Windows",
    offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
    url: "https://voss.dev", sameAs: ["https://github.com/bm9797/Voss"],
  })}} />
  ```
- **Priority:** P2 (Important)
- **Confidence:** High
- **Affected pages:** Whole site (best placed in root layout).

### Finding 7 — No custom 404 page

- **SEO Impact:** Low
- **Surface:** Source
- **Evidence:** Verified via `ls app/not-found.tsx app/global-error.tsx` → **0 matches**. Next.js serves its built-in 404.
- **Risk:** Mistyped/expired URLs (and crawler hits on dropped routes) land on a dead-end default page with no nav, no recovery links, and off-brand styling. Lost opportunity to retain the visitor and redistribute internal link equity back to live routes.
- **Fix:** Add `app/not-found.tsx` reusing `Nav` + `Footer` with links back to `/`, `/harness`, docs.
- **Priority:** P3 (Plan)
- **Confidence:** High
- **Affected pages:** All non-existent paths.

### Finding 8 — Three font families with wide weight range (CWV contributor)

- **SEO Impact:** Low
- **Surface:** Source
- **Evidence:** `app/layout.tsx:7-13`
  ```tsx
  const poppins = Poppins({ weight: ["300","400","500","600","700"], subsets: ["latin"], … });
  const geistSans = Geist({ subsets: ["latin"], … });
  const geistMono = Geist_Mono({ subsets: ["latin"], … });
  ```
  Three families; Poppins loads 5 weights.
- **Risk:** `next/font` self-hosts and adds `font-display: swap` (good — no render-blocking external request, no FOIT), but 3 families × multiple weights is real transfer weight on first paint and a minor LCP contributor on slow links. Verify all 5 Poppins weights are actually used in the type scale.
- **Fix:** Audit usage; drop unused weights (e.g. if 300 and 600 are unused, request `["400","500","700"]`). Consider whether Geist Sans + Geist Mono alone can carry the design without Poppins.
- **Priority:** P3 (Plan)
- **Confidence:** Medium
- **Affected pages:** All routes (fonts in root layout).

### Finding 9 — Analytics captures nothing without a consent opt-in path

- **SEO Impact:** Low (operational / measurement, not ranking)
- **Surface:** Source
- **Evidence:** `components/PostHogProvider.tsx`
  ```tsx
  posthog.init(POSTHOG_KEY, { …, opt_out_capturing_by_default: true });
  // comment: call posthog.opt_in_capturing() after obtaining consent
  ```
  Verified via `grep -rn "opt_in_capturing|cookie|consent|banner" app/ components/` → no opt-in call and no consent UI in source.
- **Risk:** With opt-out-by-default and no banner to flip consent, PostHog initialises but captures no pageviews/events in production. The `outbound_click` and `copy_install_command` conversion events you instrumented never fire — you're flying blind on the primary conversion. (This is GDPR-correct posture, just incomplete: the consent step is missing, not the privacy stance.)
- **Fix:** Add a lightweight consent banner that calls `posthog.opt_in_capturing()` on accept, or — if the launch decision is "no PII, legitimate-interest analytics" — set capturing on by default in jurisdictions where permitted. Decide explicitly; right now it's neither measuring nor banner-gated.
- **Priority:** P2 (Important — it's your only conversion signal)
- **Confidence:** Medium (pending Precondition 2 — a banner may exist outside source).

---

## What's working (facts, verified)

- **Per-route titles + descriptions:** all 7 subroutes export `metadata` with a route-specific `title` and `description` (verified `app/{harness,ade,language,security,roadmap,orchestration,audit}/page.tsx`). Title pattern `"<Page> - Voss"`; homepage `"Voss - The operating layer for AI engineering teams."`
- **One `<h1>` per page:** verified via `grep -rc "<h1"` — each route renders exactly one h1 (homepage's lives in `components/Hero.tsx:21`).
- **`metadataBase` set:** `app/layout.tsx:18` → relative OG/canonical URLs will resolve (correctness depends on Precondition 1).
- **Image alt text + explicit dimensions:** `Hero.tsx:55` and `app/ade/page.tsx:146` pass descriptive `alt`; `ProductScreenshot.tsx` requires `width`/`height` and sets `sizes`/`priority` → CLS-safe. Decorative logo correctly uses `alt=""` + `aria-hidden="true"` (`Logo.tsx:13-14`).
- **`lang` attribute:** `app/layout.tsx:33` → `<html lang="en">`.
- **llms.txt:** `public/llms.txt` is well-formed — H1, blockquote summary, sectioned link lists (Primary Pages / Documentation / Developer Resources / Optional) with descriptive annotations per link. (URLs depend on Precondition 1.)
- **Mobile menu accessibility:** `components/MobileMenu.tsx:39-48` — `<button>` with `aria-expanded`, `aria-controls`, dynamic `aria-label`.
- **Security headers:** `vercel.json` ships HSTS (preload), `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, and a CSP; static assets get immutable cache-control.
- **Self-hosted fonts:** `next/font/google` → no third-party font request, automatic `swap`.

## Skipped (with reason)

- **Off-site cats (paid/social/backlinks/email/PR/local/affiliate/PLG):** Skipped — brand maturity **minimal**; no off-site surface in source to audit. Revisit post-launch.
- **Cat: hreflang / i18n:** Skipped — single-locale site (`lang="en"`, no `next-intl`/locale routing found).
- **Cat: VideoObject / video schema:** Skipped — no `<video>` or embeds found.
- **Cat: e-commerce / Product / Offer-as-PDP:** Skipped — no commerce surface (free CLI tool).
- **Cat: brand SERP (live):** Skipped live-capture — source mode can't run SERP queries; on-site Organization-schema check ran (Finding 6). Re-run in crawl mode for the brand-SERP capture.

---

## 30/60/90 — recommended order

**This week (P1, one commit):**
1. **Confirm the production domain** (Precondition 1) — blocks correctness of everything URL-shaped.
2. Add `app/sitemap.ts` + `app/robots.ts` (Findings 1, 2).
3. Add OG image + `openGraph.images` (Finding 3).

**Next 30 days (P2):**
4. Per-route `openGraph` titles/descriptions (Finding 4).
5. Per-route `alternates.canonical` (Finding 5).
6. `Organization` + `SoftwareApplication` JSON-LD (Finding 6).
7. Resolve the analytics/consent decision (Finding 9) — you have no conversion signal until this is settled.

**Plan (P3):**
8. Custom `app/not-found.tsx` (Finding 7).
9. Font-weight audit (Finding 8).

---

*Audited by Snitch: Marketing. The markdown is the canonical artifact; the HTML is a derived view.*
