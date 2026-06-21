/**
 * tagColor — deterministic tag-to-palette mapping.
 *
 * Hashes a tag string to one of 5 fixed palette slots so every tag has
 * a stable, consistent color in both the FilterPanel and the RunCard chips.
 *
 * CSS classes (rv-tag--<hue>) are defined in runs-viewer.css.
 * No runtime hex math; contrast is guaranteed by fixed token pairs chosen
 * to meet WCAG AA (>=4.5:1):
 *   --it-<hue>-100 bg     + --it-<hue>-600/700 text  (resting)
 *   --it-<hue>-500/600 bg + white text               (active / .is-active)
 * (gold is intentionally excluded: its scale tops out at -500, which is
 *  too light to reach AA text contrast on the -100 background.)
 */

const PALETTE = [
  "rv-tag--teal",
  "rv-tag--blue",
  "rv-tag--purple",
  "rv-tag--green",
  "rv-tag--orange",
] as const;

export type TagColorClass = (typeof PALETTE)[number];

/**
 * Deterministic djb2-style hash over the tag string.
 * Returns a CSS class name like "rv-tag--teal".
 */
export function tagColorClass(tag: string): TagColorClass {
  let hash = 5381;
  for (let i = 0; i < tag.length; i++) {
    // eslint-disable-next-line no-bitwise
    hash = ((hash << 5) + hash) ^ tag.charCodeAt(i);
  }
  const idx = Math.abs(hash) % PALETTE.length;
  return PALETTE[idx];
}
