import { useState } from 'react'
import { EmptyState } from '@/components/shared/EmptyState'
import { PaginationControls } from '@/components/shared/PaginationControls'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { TestsetDetail } from '@/lib/api/testsets'

const ALL_VALUE = '__all__'
const originLabels = { sintetis: 'Sintetis', arsiparis: 'Nyata (arsiparis)' } as const
const pageSize = 25

export function TestsetQueryTable({ queries }: { queries: TestsetDetail['queries'] }) {
  const [split, setSplit] = useState('')
  const [source, setSource] = useState('')
  const [page, setPage] = useState(0)
  const matching = queries.filter(
    (query) => (!split || query.split === split) && (!source || query.source === source),
  )
  const start = page * pageSize

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>Daftar kueri</h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-4 text-sm">
          <div className="w-44 space-y-1.5">
            <Label htmlFor="testset-filter-split">Split</Label>
            <Select
              value={split || ALL_VALUE}
              onValueChange={(value) => {
                setSplit(value === ALL_VALUE ? '' : value)
                setPage(0)
              }}
            >
              <SelectTrigger id="testset-filter-split" className="w-full">
                <SelectValue placeholder="Semua split" />
              </SelectTrigger>
              <SelectContent position="popper">
                <SelectItem value={ALL_VALUE}>Semua split</SelectItem>
                <SelectItem value="tuning">Tuning</SelectItem>
                <SelectItem value="test">Test</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="w-52 space-y-1.5">
            <Label htmlFor="testset-filter-source">Asal kueri</Label>
            <Select
              value={source || ALL_VALUE}
              onValueChange={(value) => {
                setSource(value === ALL_VALUE ? '' : value)
                setPage(0)
              }}
            >
              <SelectTrigger id="testset-filter-source" className="w-full">
                <SelectValue placeholder="Semua asal" />
              </SelectTrigger>
              <SelectContent position="popper">
                <SelectItem value={ALL_VALUE}>Semua asal</SelectItem>
                <SelectItem value="sintetis">Sintetis</SelectItem>
                <SelectItem value="arsiparis">Nyata (arsiparis)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        {matching.length === 0 ? (
          <EmptyState message="Tidak ada kueri yang cocok dengan filter." />
        ) : (
          <>
            <ul className="divide-y divide-border rounded-lg border">
              {matching.slice(start, start + pageSize).map((query) => (
                <li key={query.query_id} className="space-y-1 px-3 py-3">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>
                      {query.query_id} · {query.base_query_id}
                    </span>
                    <Badge variant="outline">{query.split === 'tuning' ? 'Tuning' : 'Test'}</Badge>
                    <Badge variant="secondary">{originLabels[query.source]}</Badge>
                  </div>
                  <p className="text-sm font-medium break-words whitespace-pre-wrap">
                    {query.query_text}
                  </p>
                  <p className="text-xs break-words text-muted-foreground">
                    {query.query_type.replaceAll('_', ' ')} ·{' '}
                    {query.noise_type.replaceAll('_', ' ')}
                  </p>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <p aria-live="polite">
                {start + 1}–{Math.min(start + pageSize, matching.length)} dari {matching.length}{' '}
                kueri
              </p>
              <PaginationControls
                offset={start}
                limit={pageSize}
                total={matching.length}
                onPage={(nextOffset) => setPage(Math.floor(nextOffset / pageSize))}
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
