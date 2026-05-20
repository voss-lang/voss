/**
 * A7-01 Task 1 — simple substring fuzzy scoring with recency boost.
 *
 * Case-insensitive substring match. Prefix matches score higher.
 * Recent command ids receive a fixed score boost (CMD-04).
 * No external dependency — ~40 lines. Pure.
 */

/** Fixed boost for recently-used commands (CMD-04 recency). */
const RECENCY_BOOST = 100;

/**
 * Score a single label against a query.
 * Returns -1 for no match, ≥ 0 for a match.
 * Higher = better. Prefix matches > mid-string matches. Recency adds a flat boost.
 */
export function scoreCommand(
  query: string,
  label: string,
  isRecent: boolean,
): number {
  if (!query) return isRecent ? RECENCY_BOOST : 0;

  const q = query.toLowerCase();
  const l = label.toLowerCase();
  const idx = l.indexOf(q);
  if (idx === -1) return -1;

  // Prefix match (idx 0) scores highest; deeper matches score less.
  let score = 100 - idx;
  if (isRecent) score += RECENCY_BOOST;
  return score;
}

/**
 * Rank a list of items by fuzzy score against a query.
 * Items with no match are excluded. Sorted descending by score.
 */
export function rankCommandItems<T extends { id: string; label: string }>(
  query: string,
  items: readonly T[],
  recentIds: ReadonlySet<string>,
): T[] {
  return items
    .map((item) => ({
      item,
      score: scoreCommand(query, item.label, recentIds.has(item.id)),
    }))
    .filter((s) => s.score >= 0)
    .sort((a, b) => b.score - a.score)
    .map((s) => s.item);
}
