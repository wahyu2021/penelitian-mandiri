import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { PageHeader } from '@/components/shared/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useSession } from '@/features/auth/useSession'
import { CompareForm, type CompareFormValues } from '@/features/compare/CompareForm'
import { ComparisonResults } from '@/features/compare/ComparisonResults'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { getComparison } from '@/lib/api/compare'
import { getSearchFilters } from '@/lib/api/search'
import { ApiError } from '@/lib/api/session'

function valuesFromUrl(params: URLSearchParams): CompareFormValues {
  return {
    q: params.get('q') ?? '',
    opd_id: params.get('opd_id') ?? '',
    year: params.get('year') ?? '',
    status: params.get('status') ?? '',
    limit: params.get('limit') ?? '10',
  }
}

function requestFromUrl(params: URLSearchParams) {
  const next = new URLSearchParams()
  for (const key of ['q', 'opd_id', 'year', 'status', 'limit']) {
    const value = params.get(key)
    if (value) next.set(key, value)
  }
  return next.toString()
}

export function ComparePage() {
  const session = useSession()
  const isAdmin = session.data?.user?.role === 'admin'
  const [urlParams, setUrlParams] = useSearchParams()
  const request = requestFromUrl(urlParams)
  const submittedQuery = urlParams.get('q')?.trim() ?? ''
  const options = useQuery({
    queryKey: ['search-filters'],
    queryFn: getSearchFilters,
    enabled: isAdmin,
  })
  const comparison = useQuery({
    queryKey: ['search-compare', request],
    queryFn: () => getComparison(request),
    enabled: isAdmin && Boolean(submittedQuery),
  })

  useUnauthorizedRedirect([options.error, comparison.error])

  function submit(form: CompareFormValues) {
    const next = new URLSearchParams()
    const q = form.q.trim()
    if (q) next.set('q', q)
    for (const key of ['opd_id', 'year', 'status'] as const) {
      if (form[key]) next.set(key, form[key])
    }
    if (form.limit !== '10') next.set('limit', form.limit)
    setUrlParams(next)
  }

  if (!isAdmin) {
    return <ForbiddenCard message="Perbandingan metode hanya tersedia untuk admin." />
  }

  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Analisis pencarian"
        title="Perbandingan metode"
        description="Bandingkan urutan arsip untuk kueri dan filter yang sama."
      />
      <CompareForm
        key={urlParams.toString()}
        initial={valuesFromUrl(urlParams)}
        options={options.data}
        optionsError={options.isError}
        retryOptions={() => void options.refetch()}
        onCompare={submit}
        onClear={() => setUrlParams(new URLSearchParams())}
      />
      {!submittedQuery ? (
        <p className="text-sm text-muted-foreground">
          Masukkan kata kunci untuk membandingkan metode.
        </p>
      ) : comparison.isPending ? (
        <div role="status" aria-label="Membandingkan metode" className="grid gap-4 lg:grid-cols-2">
          {[0, 1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-48 w-full" />
          ))}
        </div>
      ) : comparison.isError ? (
        comparison.error instanceof ApiError && comparison.error.status === 403 ? (
          <Card role="alert">
            <CardContent>
              <p>403 · Akses perbandingan ditolak oleh server.</p>
            </CardContent>
          </Card>
        ) : (
          <ErrorStateCard
            title="Perbandingan belum dapat ditampilkan."
            description="Periksa kueri, filter, dan sambungan layanan lalu coba lagi."
            onRetry={() => void comparison.refetch()}
          />
        )
      ) : (
        <ComparisonResults data={comparison.data} />
      )}
    </main>
  )
}
