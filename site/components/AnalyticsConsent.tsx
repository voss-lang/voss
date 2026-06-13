"use client";

import posthog from "posthog-js";
import { useEffect, useState } from "react";
import {
  ANALYTICS_CONSENT_ACCEPTED,
  ANALYTICS_CONSENT_DECLINED,
  readAnalyticsConsent,
  writeAnalyticsConsent,
} from "@/lib/analytics-consent";

export default function AnalyticsConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return;

    const id = window.setTimeout(() => {
      setVisible(readAnalyticsConsent() === null);
    }, 0);

    return () => window.clearTimeout(id);
  }, []);

  function accept() {
    posthog.opt_in_capturing();
    writeAnalyticsConsent(ANALYTICS_CONSENT_ACCEPTED);
    setVisible(false);
  }

  function decline() {
    posthog.opt_out_capturing();
    writeAnalyticsConsent(ANALYTICS_CONSENT_DECLINED);
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-labelledby="analytics-consent-title"
      aria-describedby="analytics-consent-desc"
      className="fixed inset-x-4 bottom-4 z-[100] mx-auto max-w-3xl rounded-xl border border-[var(--border)] bg-[color-mix(in_oklab,var(--surface)_94%,transparent)] p-4 shadow-[0_24px_60px_-24px_rgba(0,0,0,0.85)] backdrop-blur-xl sm:inset-x-6 sm:p-5"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p id="analytics-consent-title" className="text-sm font-medium text-[var(--foreground)]">
            Analytics cookies
          </p>
          <p id="analytics-consent-desc" className="mt-1 text-sm leading-relaxed text-[var(--muted)]">
            We use privacy-friendly analytics to see which pages and install paths help developers
            find Voss. No ads, no cross-site tracking.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <button
            type="button"
            onClick={decline}
            className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--foreground)]"
          >
            Decline
          </button>
          <button
            type="button"
            onClick={accept}
            className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--background)] transition hover:bg-[color-mix(in_oklab,var(--accent)_88%,white)]"
          >
            Accept
          </button>
        </div>
      </div>
    </div>
  );
}
