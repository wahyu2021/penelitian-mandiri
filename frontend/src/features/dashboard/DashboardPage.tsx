import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, CircleCheck, FileText, RefreshCw, CircleSlash } from 'lucide-react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { sessionKey } from '@/features/auth/useSession'
import { getDashboard, type Dashboard } from '@/lib/api/dashboard'
import { ApiError } from '@/lib/api/session'

const numberFormat = new Intl.NumberFormat('id-ID')

export function DashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['dashboard'], queryFn: getDashboard })

  useEffect(() => {
    if (query.error instanceof ApiError && query.error.status === 401) {
      queryClient.removeQueries({ queryKey: sessionKey })
      navigate('/login', { replace: true })
    }
  }, [query.error, queryClient, navigate])

  return (
    <main className="py-8 sm:py-10">
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Ikhtisar korpus</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
            Dashboard arsip
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Angka langsung dari basis data lokal.
          </p>
        </div>
        <Button variant="outline" onClick={() => void query.refetch()} disabled={query.isFetching}>
          <RefreshCw aria-hidden="true" /> Perbarui
        </Button>
      </div>

      {query.isPending ? (
        <DashboardLoading />
      ) : query.isError ? (
        <Card role="alert">
          <CardContent className="space-y-3">
            <p className="font-medium">Ringkasan belum dapat dimuat.</p>
            <p className="text-sm text-muted-foreground">
              Periksa sambungan layanan lalu coba lagi.
            </p>
            <Button variant="outline" onClick={() => void query.refetch()}>
              Coba lagi
            </Button>
          </CardContent>
        </Card>
      ) : (
        <DashboardContent data={query.data} />
      )}
    </main>
  )
}

function DashboardLoading() {
  return (
    <div role="status" aria-label="Memuat ringkasan" className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((item) => (
          <Card key={item}>
            <CardContent className="space-y-4">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-9 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardContent>
          <Skeleton className="h-5 w-44" />
          <Skeleton className="mt-5 h-12 w-full" />
        </CardContent>
      </Card>
    </div>
  )
}

function DashboardContent({ data }: { data: Dashboard }) {
  const metrics = [
    { label: 'Jumlah arsip', value: data.counts.total, icon: Archive },
    { label: 'Status aktif', value: data.counts.active, icon: CircleCheck },
    { label: 'Status nonaktif', value: data.counts.inactive, icon: CircleSlash },
    { label: 'Ada berkas digital', value: data.counts.with_file, icon: FileText },
  ]

  return (
    <div className="space-y-6">
      <section aria-label="Statistik arsip" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between gap-2 text-sm text-muted-foreground">
                <span>{label}</span>
                <Icon aria-hidden="true" className="size-4" />
              </div>
              <strong className="block text-3xl font-semibold tabular-nums">
                {numberFormat.format(value)}
              </strong>
            </CardContent>
          </Card>
        ))}
      </section>
      <Card>
        <CardHeader className="border-b border-border">
          <CardTitle>
            <h2>Arsip terakhir dalam data</h2>
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Berdasarkan ID arsip, bukan tanggal dokumen.
          </p>
        </CardHeader>
        <CardContent>
          {data.recent.length === 0 ? (
            <p className="py-3 text-sm text-muted-foreground">
              Belum ada arsip dalam salinan data.
            </p>
          ) : (
            <ol className="divide-y divide-border">
              {data.recent.map((item) => (
                <li
                  key={item.id}
                  className="flex flex-col gap-1 py-3 text-sm sm:flex-row sm:items-start sm:gap-4"
                >
                  <span className="w-16 shrink-0 font-mono text-xs text-muted-foreground">
                    #{item.id}
                  </span>
                  <span className="min-w-0 flex-1 break-words">
                    {item.summary_raw || 'Ringkasan tidak tersedia'}
                  </span>
                  <span className="shrink-0 text-muted-foreground">
                    {item.year ?? 'Tahun tidak tersedia'}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
