const numberFormat = new Intl.NumberFormat('id-ID')

const currencyFormat = new Intl.NumberFormat('id-ID', {
  style: 'currency',
  currency: 'IDR',
  maximumFractionDigits: 0,
})

const dateTimeFormat = new Intl.DateTimeFormat('id-ID', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

export function formatNumber(value: number): string {
  return numberFormat.format(value)
}

export function formatCurrencyIdr(value: number): string {
  return currencyFormat.format(value)
}

export function formatDateTimeId(value: string): string {
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : dateTimeFormat.format(parsed)
}
