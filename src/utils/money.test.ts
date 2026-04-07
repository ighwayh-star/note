import { centsFromYuanText, formatCents } from '@/utils/money'

describe('money', () => {
  it('formatCents formats CNY', () => {
    expect(formatCents(1234, 'CNY')).toContain('12.34')
  })

  it('centsFromYuanText parses common inputs', () => {
    expect(centsFromYuanText('12.34')).toBe(1234)
    expect(centsFromYuanText('12')).toBe(1200)
    expect(centsFromYuanText(' 1,234.50 ')).toBe(123450)
  })
})

