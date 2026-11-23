import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/button'
import { useSession } from '@/features/auth/useSession'
import { EvaluationMetricsChart } from '@/features/evaluation/EvaluationMetricsChart'
import {
  EvaluationPerQueryTable,
  type PerQueryFilters,
} from '@/features/evaluation/EvaluationPerQueryTable'
import { EvaluationProvenanceCard } from '@/features/evaluation/EvaluationProvenanceCard'
import { EvaluationTuningCard } from '@/features/evaluation/EvaluationTuningCard'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { type EvaluationSplit, evaluationExportUrl, fetchEvaluationRun } from '@/lib/api/evaluation'
import { ApiError } from '@/lib/api/session'

export function EvaluationPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === 'admin'
  const [split, setSplit] = useState<EvaluationSplit>('test')
  const [filters, setFilters] = useState<PerQueryFilters>({})
  const [page, setPage] = useState(1)

  const query = useQuery({
    queryKey: [
      'research-evaluation',
      split,
      filters.method ?? null,
      filters.config ?? null,
      filters.queryType ?? null,
      filters.noiseType ?? null,
      page,
    ],
    queryFn: () =>
      fetchEvaluationRun({
        split,
        method: filters.method,
        config: filters.config,
        queryType: filters.queryType,
        noiseType: filters.noiseType,
        page,
        perPage: 25,
      }),
    enabled: isAdmin,
  })

  useUnauthorizedRedirect([query.error])

  if (!isAdmin) {
    return <ForbiddenCard message="Hasil evaluasi dan bukti run hanya tersedia untuk admin." />
  }

  const errorMessage =
    query.error instanceof ApiError ? query.error.message : 'Data evaluasi run belum dapat dimuat.'

  const handleSplitChange = (nextSplit: EvaluationSplit) => {
    setSplit(nextSplit)
    setPage(1)
  }

  const handleFiltersChange = (next: PerQueryFilters) => {
    setFilters(next)
    setPage(1)
  }

  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Evaluasi eksperimen"
        title="Hasil evaluasi & bukti run"
        description="Metrik per metode dan bukti keterulangan dari artefak bundle resmi, dengan pemisahan split tuning dan test."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div
              className="inline-flex rounded-md border bg-background p-0.5"
              role="group"
              aria-label="Pilih split evaluasi"
            >
              <Button
                type="button"
                size="sm"
                variant={split === 'test' ? 'default' : 'ghost'}
                onClick={() => handleSplitChange('test')}
              >
                Split Test
              </Button>
              <Button
                type="button"
                size="sm"
                variant={split === 'tuning' ? 'default' : 'ghost'}
                onClick={() => handleSplitChange('tuning')}
              >
                Split Tuning
              </Button>
            </div>
            {query.data?.available && (
              <>
                <Button asChild variant="outline">
                  <a href={evaluationExportUrl(split, 'csv')}>
                    <Download aria-hidden="true" /> Ekspor CSV
                  </a>
                </Button>
                <Button asChild variant="outline">
                  <a href={evaluationExportUrl(split, 'json')}>
                    <Download aria-hidden="true" /> Ekspor JSON
                  </a>
                </Button>
              </>
            )}
          </div>
        }
      />

      {query.isPending && (
        <LoadingState label="Memuat hasil evaluasi" rows={2} rowClassName="h-44 w-full" />
      )}

      {query.isError && (
        <ErrorStateCard title={errorMessage} onRetry={() => void query.refetch()} />
      )}

      {query.data && !query.data.available && (
        <EmptyState
          asCard
          message={query.data.status_reasons[0] ?? 'Artefak run belum tersedia.'}
        />
      )}

      {query.data && query.data.available && (
        <div className="space-y-6">
          <EvaluationProvenanceCard run={query.data} />
          <EvaluationMetricsChart items={query.data.method_summary} split={query.data.split} />
          <EvaluationTuningCard items={query.data.tuning_best} />
          <EvaluationPerQueryTable
            run={query.data}
            filters={filters}
            onFiltersChange={handleFiltersChange}
            onPageChange={setPage}
          />
        </div>
      )}
    </main>
  )
}
