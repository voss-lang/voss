import type { MetadataRoute } from "next";
import { site } from "@/lib/site";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  return site.routes.map((route) => ({
    url: `${site.url}${route}/`,
    changeFrequency: "weekly",
    priority: route === "" ? 1 : 0.8,
  }));
}
