const PALETTE = [
  "rv-tag--teal",
  "rv-tag--blue",
  "rv-tag--purple",
  "rv-tag--green",
  "rv-tag--orange",
] as const;

export type ProjectColorClass = (typeof PALETTE)[number];

export function projectColorClass(project: string): ProjectColorClass {
  let hash = 5381;
  for (let i = 0; i < project.length; i++) {
    // eslint-disable-next-line no-bitwise
    hash = ((hash << 5) + hash) ^ project.charCodeAt(i);
  }
  const idx = Math.abs(hash) % PALETTE.length;
  return PALETTE[idx];
}
