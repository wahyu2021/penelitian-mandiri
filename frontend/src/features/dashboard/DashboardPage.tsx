import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Archive, CircleCheck, CircleSlash, FileText, RefreshCw, Search } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { ErrorStateCard, PageHeader } from '@/components/shared/PageLayout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { getDashboard, type Dashboard } from '@/lib/api/dashboard'
import { formatDateTimeId, formatNumber } from '@/lib/format'

export function DashboardPage() {
  const navigate = useNavigate()
  const [quickQuery, setQuickQuery] = useState('')
  const query = useQuery({ queryKey: ['dashboard'], queryFn: getDashboard })

  useUnauthorizedRedirect([query.error])

  function submitQuickSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = quickQuery.trim()
    navigate(trimmed ? `/app/search?q=${encodeURIComponent(trimmed)}` : '/app/search')
  }

  const subtitle = query.data?.latest_import
    ? `Pembaruan data terakhir: ${formatDateTimeId(query.data.latest_import.imported_at)} (${query.data.latest_import.source_filename})`
    : query.data
      ? 'Belum ada riwayat impor data.'
      : 'Angka langsung dari basis data lokal.'

  return (
    <main className="space-y-6 py-8 sm:py-10">
      <PageHeader
        eyebrow="Ikhtisar korpus"
        title="Dashboard arsip"
        description={subtitle}
        actions={
          <Button
            variant="outline"
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
          >
            <RefreshCw aria-hidden="true" /> Perbarui
          </Button>
        }
      />

      <Card>
        <CardContent>
          <form
            onSubmit={submitQuickSearch}
            className="flex flex-col gap-3 sm:flex-row sm:items-end"
          >
            <div className="min-w-0 flex-1 space-y-2">
              <Label htmlFor="dashboard-quick-search">Pencarian cepat arsip</Label>
              <Input
                id="dashboard-quick-search"
                type="search"
                value={quickQuery}
                onChange={(event) => setQuickQuery(event.target.value)}
                maxLength={200}
                placeholder="Cari nomor SPM, pekerjaan, atau nama pihak…"
                className="h-10"
              />
            </div>
            <Button type="submit" className="h-10 shrink-0">
              <Search aria-hidden="true" /> Cari arsip
            </Button>
          </form>
        </CardContent>
      </Card>

      {query.isPending ? (
        <DashboardLoading />
      ) : query.isError ? (
        <ErrorStateCard
          title="Ringkasan belum dapat dimuat."
          description="Periksa sambungan layanan lalu coba lagi."
          onRetry={() => void query.refetch()}
        />
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
                {formatNumber(value)}
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
                <li key={item.id}>
                  <Link
                    to={`/app/archives/${item.id}`}
                    className="-mx-2 flex flex-col gap-1 rounded-lg px-2 py-3 text-sm transition-colors hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary sm:flex-row sm:items-start sm:gap-4"
                  >
                    <span className="w-16 shrink-0 font-mono text-xs font-medium text-primary">
                      #{item.id}
                    </span>
                    <span className="min-w-0 flex-1 space-y-1">
                      <span className="block break-words text-foreground">
                        {item.summary_raw || 'Ringkasan tidak tersedia'}
                      </span>
                      {item.opd_name && (
                        <span className="block text-xs text-muted-foreground">{item.opd_name}</span>
                      )}
                    </span>
                    <span className="shrink-0 text-muted-foreground">
                      {item.year ?? 'Tahun tidak tersedia'}
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
