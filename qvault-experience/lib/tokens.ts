// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Design Tokens (JS mirror of CSS vars)
// Extracted from Q-Vault OS design_tokens.py & theme.py
// ═══════════════════════════════════════════════════════════════

export const colors = {
  void: '#01020e',
  base: '#040f22',
  surface: '#0b162d',
  elevated: '#0f2842',
  overlay: '#243558',

  cyan: '#00e6ff',
  cyanBright: '#66f2ff',
  cyanDim: '#3a8fa8',
  purple: '#9c27ff',
  pink: '#ff2fd1',
  steel: '#2f6183',

  success: '#00ff88',
  warning: '#ffaa00',
  danger: '#ff3333',

  text: '#e6f7ff',
  textDim: '#9ec0d5',
  textMuted: '#4a6880',
} as const;

export const motion = {
  instant: 100,
  snappy: 150,
  smooth: 300,
  cinematic: 600,
  dramatic: 1200,
} as const;

export const easing = {
  precise: 'power2.out',
  physical: 'power3.inOut',
  tension: 'power4.in',
  release: 'expo.out',
} as const;

export const fonts = {
  display: "'Inter', system-ui, sans-serif",
  mono: "'JetBrains Mono', 'Cascadia Code', monospace",
} as const;

export const radius = {
  sm: 4,
  md: 8,
  lg: 12,
} as const;
