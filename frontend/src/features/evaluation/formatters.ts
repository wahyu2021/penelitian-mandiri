const METHOD_NAMES: Record<string, string> = {
  like_baseline: 'LIKE Baseline',
  levenshtein: 'Levenshtein',
  jaro_winkler: 'Jaro-Winkler',
  token_set: 'Token Set',
  ngram: 'N-Gram',
}

const CONFIG_NAMES: Record<string, string> = {
  baseline: 'Baseline',
  equal: 'Equal',
  tuned: 'Tuned',
}

export function formatMethodName(method: string): string {
  return METHOD_NAMES[method] ?? method
}

export function formatMethodLabel(method: string, config: string): string {
  const baseName = formatMethodName(method)
  if (method === 'like_baseline' || config === 'baseline') {
    return baseName
  }
  const cfgName = CONFIG_NAMES[config] ?? config
  return `${baseName} (${cfgName})`
}

export function formatDecimal(value: number, digits = 4): string {
  return value.toFixed(digits).replace('.', ',')
}

export function formatPercent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits).replace('.', ',')}%`
}
