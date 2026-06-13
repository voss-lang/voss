import type { Metadata } from "next";
import { site } from "@/lib/site";

export const ogImage = {
  url: "/og.png",
  width: 1200,
  height: 630,
  alt: `${site.name} — ${site.tagline}`,
} as const;

const homeTitle = `${site.name} - ${site.tagline}`;

/** Root layout defaults (metadataBase, OG image, Twitter card). */
export const rootMetadata: Metadata = {
  title: homeTitle,
  description: site.description,
  metadataBase: new URL(site.url),
  openGraph: {
    title: homeTitle,
    description: site.description,
    type: "website",
    images: [ogImage],
  },
  twitter: {
    card: "summary_large_image",
    title: homeTitle,
    description: site.description,
    images: [ogImage.url],
  },
};

function canonicalPath(path: string): string {
  if (path === "/" || path === "") return "/";
  return path.endsWith("/") ? path : `${path}/`;
}

/** Per-route title, description, Open Graph, Twitter, and canonical. */
export function pageMetadata(opts: {
  title: string;
  description: string;
  path: string;
}): Metadata {
  const canonical = canonicalPath(opts.path);

  return {
    title: opts.title,
    description: opts.description,
    alternates: { canonical },
    openGraph: {
      title: opts.title,
      description: opts.description,
      type: "website",
      images: [ogImage],
    },
    twitter: {
      card: "summary_large_image",
      title: opts.title,
      description: opts.description,
      images: [ogImage.url],
    },
  };
}
