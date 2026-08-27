/** Stable per-theme accent hues (violet / blue / amber / green), derived from theme key. */

const THEME_ACCENT_TOKENS = [
  "--sig-positioning",
  "--sig-partnership",
  "--sig-pricing",
  "--brand-jfrog",
] as const;

export function themeAccentVar(themeKey: string): string {
  let hash = 0;
  for (let i = 0; i < themeKey.length; i += 1) {
    hash = (hash + themeKey.charCodeAt(i) * (i + 1)) % 997;
  }
  return THEME_ACCENT_TOKENS[hash % THEME_ACCENT_TOKENS.length];
}
