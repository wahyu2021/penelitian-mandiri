import { FileText } from 'lucide-react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { HighlightedText } from '@/features/search/HighlightedText'
import type { SearchResults } from '@/lib/api/search'

type SearchResultItem = SearchResults['items'][number]

export function SearchResultCard({
  item,
  query,
  method,
  returnSearch,
}: {
  item: SearchResultItem
  query: string
  method: string
  returnSearch: string
}) {
  return (
    <Card>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <p className="font-semibold">
            <Link
              className="text-primary underline-offset-4 hover:underline focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              to={{
                pathname: `/app/archives/${item.id}`,
                search: returnSearch ? `?${returnSearch}` : '',
              }}
            >
              Arsip #{item.id}
            </Link>
          </p>
          <Badge variant="secondary">
            {method === 'like' ? 'Cocok' : `Skor ${item.score.toFixed(3)}`}
          </Badge>
        </div>
        <p className="break-words text-sm leading-6">
          <HighlightedText text={item.summary_raw || 'Ringkasan tidak tersedia'} query={query} />
        </p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>{item.opd_name || 'OPD tidak tersedia'}</span>
          <span>{item.year ?? 'Tahun tidak tersedia'}</span>
          {item.file_number && <span>Nomor berkas {item.file_number}</span>}
          {item.spm_number && <span>SPM {item.spm_number}</span>}
          {item.has_document && (
            <span className="inline-flex items-center gap-1">
              <FileText aria-hidden="true" className="size-3.5" /> Ada berkas digital
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
