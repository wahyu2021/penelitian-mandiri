import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { sessionKey, useSession } from '@/features/auth/useSession'
import { CompareForm, type CompareFormValues } from '@/features/compare/CompareForm'
import { getComparison, type CompareResults } from '@/lib/api/compare'
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
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  useEffect(() => {
    if (
      [options.error, comparison.error].some(
        (error) => error instanceof ApiError && error.status === 401,
      )
    ) {
      queryClient.removeQueries({ queryKey: sessionKey })
      navigate('/login', { replace: true })
    }
  }, [options.error, comparison.error, queryClient, navigate])

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
    return (
      <main className="py-8 sm:py-10">
        <Card role="alert">
          <CardContent>
            <h1 className="text-xl font-semibold">403 · Akses ditolak</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Perbandingan metode hanya tersedia untuk admin.
            </p>
          </CardContent>
        </Card>
      </main>
    )
  }

  return (
    <main className="space-y-6 py-8 sm:py-10">
      <header>
        <p className="text-sm font-medium text-muted-foreground">Analisis pencarian</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
          Perbandingan metode
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Bandingkan urutan arsip untuk kueri dan filter yang sama.
        </p>
      </header>
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
          <Card role="alert">
            <CardContent className="space-y-3">
              <p className="font-medium">Perbandingan belum dapat ditampilkan.</p>
              <p className="text-sm text-muted-foreground">
                Periksa kueri, filter, dan sambungan layanan lalu coba lagi.
              </p>
              <Button variant="outline" onClick={() => void comparison.refetch()}>
                <RefreshCw aria-hidden="true" /> Coba lagi
              </Button>
            </CardContent>
          </Card>
        )
      ) : (
        <ComparisonResults data={comparison.data} />
      )}
    </main>
  )
}

function ComparisonResults({ data }: { data: CompareResults }) {
  return (
    <section aria-labelledby="comparison-title" className="space-y-4">
      <div>
        <h2 id="comparison-title" className="text-lg font-semibold">
          Hasil per metode
        </h2>
        <p className="text-sm text-muted-foreground">
          Kueri: “{data.query}” · Maksimal {data.limit} arsip per metode
        </p>
      </div>
      <p className="rounded-md border border-border bg-muted/50 px-4 py-3 text-sm leading-6">
        {data.score_note} Bandingkan urutan dan arsip yang ditemukan, bukan nilai skor lintas
        metode.
      </p>
      <div className="grid items-start gap-4 lg:grid-cols-2">
        {data.methods.map((method) => (
          <Card key={method.name}>
            <CardHeader className="border-b border-border">
              <CardTitle>
                <h3>{method.label}</h3>
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                {method.items.length} hasil dalam daftar metode ini
              </p>
            </CardHeader>
            <CardContent>
              {method.items.length === 0 ? (
                <p className="py-3 text-sm text-muted-foreground">
                  Tidak ada arsip yang cocok untuk metode ini.
                </p>
              ) : (
                <table className="w-full table-fixed text-left text-sm">
                  <caption className="sr-only">Urutan hasil {method.label}</caption>
                  <thead className="text-xs text-muted-foreground">
                    <tr>
                      <th scope="col" className="w-10 py-2 font-medium">
                        No.
                      </th>
                      <th scope="col" className="py-2 font-medium">
                        Arsip dan ringkasan
                      </th>
                      <th scope="col" className="w-20 py-2 text-right font-medium">
                        {method.name === 'like' ? 'Status' : 'Skor'}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {method.items.map((item, index) => (
                      <tr key={item.id}>
                        <td className="py-3 align-top tabular-nums text-muted-foreground">
                          {index + 1}
                        </td>
                        <td className="min-w-0 break-words py-3 pr-2 align-top">
                          <span className="font-medium">#{item.id}</span>
                          <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                            {item.summary_raw || 'Ringkasan tidak tersedia'}
                          </span>
                        </td>
                        <td className="py-3 text-right align-top tabular-nums">
                          {method.name === 'like' ? 'Cocok' : item.score.toFixed(3)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  )
}
