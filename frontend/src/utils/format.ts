export function formatPercent(value?: number | null) {
  if (value === undefined || value === null) return '-';
  return `${Math.round(value * 100)}%`;
}

export function formatText(value?: string | null) {
  return value && value.trim() ? value : '-';
}

export function formatDateTime(value?: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}
