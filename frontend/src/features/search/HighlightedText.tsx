import type { ReactNode } from 'react'

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function HighlightedText({ text, query }: { text: string; query: string }) {
  const terms = [...new Set(query.trim().split(/\s+/).filter(Boolean))]
  if (terms.length === 0) return text
  const pattern = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'gi')
  const termSet = new Set(terms.map((term) => term.toLocaleLowerCase('id-ID')))
  const parts: ReactNode[] = text.split(pattern).map((part, index) =>
    termSet.has(part.toLocaleLowerCase('id-ID')) ? (
      <mark key={index} className="rounded-sm bg-amber-100 px-0.5 text-inherit">
        {part}
      </mark>
    ) : (
      part
    ),
  )
  return <>{parts}</>
}
