import { useQuery } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { getHealth } from '@/lib/api/health'

export function StatusPage() {
  const { data, isPending, isError, isFetching, refetch } = useQuery({
    queryKey: ['service-health'],
    queryFn: getHealth,
  })

  const message = isPending
    ? 'Memeriksa sambungan layanan…'
    : isError
      ? 'Layanan belum tersambung.'
      : data === 'ok'
        ? 'Layanan tersambung.'
        : 'Status belum tersedia.'

  return (
    <main className="py-8 text-foreground sm:py-10">
      <div className="mx-auto max-w-3xl">
        <section
          aria-labelledby="status-title"
          className="rounded-2xl border border-border bg-card p-6 shadow-xs sm:p-8"
        >
          <p className="text-sm font-medium text-muted-foreground">Status aplikasi</p>
          <h1 id="status-title" className="mt-2 text-2xl font-semibold tracking-tight">
            Sambungan ke layanan arsip
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
            Halaman ini memeriksa apakah layanan aplikasi dapat dihubungi. Data arsip tetap berada
            pada salinan penelitian.
          </p>

          <div className="mt-7 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-stone-50 px-4 py-3">
            <p
              role="status"
              aria-live="polite"
              className="flex items-center gap-3 text-sm font-medium"
            >
              <span
                aria-hidden="true"
                className={`size-2.5 rounded-full ${isError ? 'bg-rose-600' : isPending ? 'bg-amber-500' : 'bg-emerald-600'}`}
              />
              {message}
            </p>
            <Button
              type="button"
              variant="outline"
              onClick={() => void refetch()}
              disabled={isFetching}
            >
              <RefreshCw aria-hidden="true" />
              Periksa ulang
            </Button>
          </div>
        </section>
      </div>
    </main>
  )
}
