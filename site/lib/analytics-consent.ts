export const ANALYTICS_CONSENT_KEY = "voss-analytics-consent";
export const ANALYTICS_CONSENT_ACCEPTED = "accepted";
export const ANALYTICS_CONSENT_DECLINED = "declined";

export type AnalyticsConsentValue =
  | typeof ANALYTICS_CONSENT_ACCEPTED
  | typeof ANALYTICS_CONSENT_DECLINED;

export function readAnalyticsConsent(): AnalyticsConsentValue | null {
  if (typeof window === "undefined") return null;
  const value = localStorage.getItem(ANALYTICS_CONSENT_KEY);
  if (value === ANALYTICS_CONSENT_ACCEPTED || value === ANALYTICS_CONSENT_DECLINED) {
    return value;
  }
  return null;
}

export function writeAnalyticsConsent(value: AnalyticsConsentValue): void {
  localStorage.setItem(ANALYTICS_CONSENT_KEY, value);
}
