import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { SearchForm, type FormValues } from '@/features/search/SearchForm'
import { SearchResultList } from '@/features/search/SearchResultList'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { getSearchFilters, getSearchResults } from '@/lib/api/search'

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
    <main className="space-y-6 py-5 sm:py-6">
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
        <LoadingState label="Mencari arsip" rows={2} rowClassName="h-24 w-full" />
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
