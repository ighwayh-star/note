export function formatCents(cents: number, currency = 'CNY'): string {
  const value = (cents || 0) / 100
  const formatted = new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
  return formatted
}

export function centsFromYuanText(text: string): number {
  const cleaned = (text || '').trim().replace(/[，,\s]/g, '')
  if (!cleaned) return 0
  const num = Number(cleaned)
  if (!Number.isFinite(num)) return 0
  return Math.round(num * 100)
}

