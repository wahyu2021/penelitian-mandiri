import { useQuery } from '@tanstack/react-query'
import { Archive, CircleCheck, CircleSlash, FileText, RefreshCw } from 'lucide-react'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { QuickSearchCard } from '@/features/dashboard/QuickSearchCard'
import { RecentArchivesCard } from '@/features/dashboard/RecentArchivesCard'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { getDashboard, type Dashboard } from '@/lib/api/dashboard'
import { formatDateTimeId, formatNumber } from '@/lib/format'

export function DashboardPage() {
  const query = useQuery({ queryKey: ['dashboard'], queryFn: getDashboard })

  useUnauthorizedRedirect([query.error])

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

      <QuickSearchCard />

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
      <RecentArchivesCard items={data.recent} />
    </div>
  )
}
