export const pct = (x: number, digits = 1): string => `${(x * 100).toFixed(digits)}%`;

export const secs = (x: number, digits = 2): string => `${x.toFixed(digits)}s`;

export const num = (x: number): string => x.toLocaleString("en-US");

export const compact = (x: number): string =>
  Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 }).format(x);
