import { useQuery } from '@tanstack/react-query'
import { FileText } from 'lucide-react'
import { Link, useSearchParams } from 'react-router'
import { ErrorStateCard, PageHeader } from '@/components/shared/PageLayout'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { HighlightedText } from '@/features/search/HighlightedText'
import { SearchForm, type FormValues } from '@/features/search/SearchForm'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { getSearchFilters, getSearchResults, type SearchResults } from '@/lib/api/search'

function valuesFromUrl(params: URLSearchParams): FormValues {
  return {
    q: params.get('q') ?? '',
    opd_id: params.get('opd_id') ?? '',
    year: params.get('year') ?? '',
    status: params.get('status') ?? '',
    limit: params.get('limit') ?? '20',
  }
}

function requestFromUrl(params: URLSearchParams) {
  const next = new URLSearchParams()
  for (const key of ['q', 'opd_id', 'year', 'status', 'limit', 'offset']) {
    const value = params.get(key)
    if (value) next.set(key, value)
  }
  return next.toString()
}

export function SearchPage() {
  const [urlParams, setUrlParams] = useSearchParams()
  const options = useQuery({ queryKey: ['search-filters'], queryFn: getSearchFilters })
  const request = requestFromUrl(urlParams)
  const submittedQuery = urlParams.get('q')?.trim() ?? ''
  const results = useQuery({
    queryKey: ['search', request],
    queryFn: () => getSearchResults(request),
    enabled: Boolean(submittedQuery),
  })
  const urlKey = urlParams.toString()

  useUnauthorizedRedirect([options.error, results.error])

  function submit(form: FormValues) {
    const next = new URLSearchParams()
    const q = form.q.trim()
    if (q) next.set('q', q)
    for (const key of ['opd_id', 'year', 'status'] as const) {
      if (form[key]) next.set(key, form[key])
    }
    if (form.limit !== '20') next.set('limit', form.limit)
    setUrlParams(next)
  }

  function clear() {
    setUrlParams(new URLSearchParams())
  }

  function changePage(offset: number) {
    const next = new URLSearchParams(urlParams)
    if (offset === 0) next.delete('offset')
    else next.set('offset', String(offset))
    setUrlParams(next)
  }

  return (
    <main className="space-y-6 py-8 sm:py-10">
      <PageHeader
        eyebrow="Temu kembali"
        title="Pencarian arsip"
        description="Cari berdasarkan nomor SPM, pekerjaan, atau pihak."
      />

      <SearchForm
        key={urlKey}
        initial={valuesFromUrl(urlParams)}
        options={options.data}
        optionsError={options.isError}
        retryOptions={() => void options.refetch()}
        onSearch={submit}
        onClear={clear}
      />

      {!submittedQuery ? (
        <p className="text-sm text-muted-foreground">Masukkan kata kunci untuk mulai mencari.</p>
      ) : results.isPending ? (
        <div role="status" aria-label="Mencari arsip" className="space-y-3">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : results.isError ? (
        <ErrorStateCard
          title="Pencarian belum dapat ditampilkan."
          description="Periksa filter dan sambungan layanan, lalu coba lagi."
          onRetry={() => void results.refetch()}
        />
      ) : (
        <SearchResultList data={results.data} onPage={changePage} returnSearch={request} />
      )}
    </main>
  )
}

function SearchResultList({
  data,
  onPage,
  returnSearch,
}: {
  data: SearchResults
  onPage: (offset: number) => void
  returnSearch: string
}) {
  const { limit, offset, total } = data.pagination
  const start = data.items.length === 0 ? 0 : offset + 1
  const end = Math.min(offset + data.items.length, total)
  return (
    <section aria-labelledby="results-title" className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="results-title" className="text-lg font-semibold">
            Hasil pencarian
          </h2>
          <p className="text-sm text-muted-foreground">{total} arsip cocok</p>
        </div>
        {data.items.length > 0 && (
          <p className="text-sm text-muted-foreground">
            Menampilkan {start}–{end} dari {total}
          </p>
        )}
      </div>
      <p className="text-xs leading-5 text-muted-foreground">
        {data.method === 'like'
          ? 'Menampilkan kecocokan kata tepat, tanpa peringkat kemiripan.'
          : 'Diurutkan berdasarkan kemiripan kata kunci; skor hanya untuk urutan hasil.'}
      </p>
      {data.items.length === 0 ? (
        <Card>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {total === 0
                ? 'Tidak ada arsip yang cocok. Coba kata kunci atau filter lain.'
                : 'Halaman ini tidak berisi hasil. Kembali ke halaman sebelumnya.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {data.items.map((item) => (
            <Card key={item.id}>
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
                    {data.method === 'like' ? 'Cocok' : `Skor ${item.score.toFixed(3)}`}
                  </Badge>
                </div>
                <p className="break-words text-sm leading-6">
                  <HighlightedText
                    text={item.summary_raw || 'Ringkasan tidak tersedia'}
                    query={data.query}
                  />
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
          ))}
        </div>
      )}
      {total > limit && (
        <div className="flex items-center justify-end gap-2">
          <Button
            variant="outline"
            disabled={offset === 0}
            onClick={() => onPage(Math.max(0, offset - limit))}
          >
            Sebelumnya
          </Button>
          <Button
            variant="outline"
            disabled={offset + limit >= total}
            onClick={() => onPage(offset + limit)}
          >
            Berikutnya
          </Button>
        </div>
      )}
    </section>
  )
}
