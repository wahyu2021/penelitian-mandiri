import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useSession } from '@/features/auth/useSession'
import { EvaluationKpiStrip } from '@/features/evaluation/EvaluationKpiStrip'
import { EvaluationMetricsChart } from '@/features/evaluation/EvaluationMetricsChart'
import {
  EvaluationPerQueryTable,
  type PerQueryFilters,
} from '@/features/evaluation/EvaluationPerQueryTable'
import { EvaluationProvenanceCard } from '@/features/evaluation/EvaluationProvenanceCard'
import { EvaluationStatusBadge } from '@/features/evaluation/EvaluationStatusBadge'
import { EvaluationTuningCard } from '@/features/evaluation/EvaluationTuningCard'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { type EvaluationSplit, evaluationExportUrl, fetchEvaluationRun } from '@/lib/api/evaluation'
import { ApiError } from '@/lib/api/session'
import { formatNumber } from '@/lib/format'

export function EvaluationPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === 'admin'
  const [split, setSplit] = useState<EvaluationSplit>('test')
  const [activeTab, setActiveTab] = useState('overview')
  const [filters, setFilters] = useState<PerQueryFilters>({})
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(25)

  const query = useQuery({
    queryKey: [
      'research-evaluation',
      split,
      filters.method ?? null,
      filters.config ?? null,
      filters.queryType ?? null,
      filters.noiseType ?? null,
      page,
      perPage,
    ],
    queryFn: () =>
      fetchEvaluationRun({
        split,
        method: filters.method,
        config: filters.config,
        queryType: filters.queryType,
        noiseType: filters.noiseType,
        page,
        perPage,
      }),
    placeholderData: keepPreviousData,
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

  const run = query.data
  const noLeakage = run ? run.split_counts.split_leakage_count === 0 : true

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
            {run?.available && (
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

      {run && !run.available && (
        <EmptyState asCard message={run.status_reasons[0] ?? 'Artefak run belum tersedia.'} />
      )}

      {run && run.available && (
        <div className="space-y-6">
          <Card size="sm" aria-label="Status validasi artefak run">
            <CardContent className="flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex flex-wrap items-center gap-2">
                <EvaluationStatusBadge status={run.status} />
                <Badge variant={run.manifest.valid ? 'outline' : 'secondary'}>
                  {run.manifest.valid ? 'Manifest SHA-256 valid' : 'Manifest tak valid'}
                </Badge>
                <Badge variant={noLeakage ? 'outline' : 'destructive'}>
                  {noLeakage
                    ? 'Tuning/test terpisah'
                    : `${formatNumber(run.split_counts.split_leakage_count)} kebocoran`}
                </Badge>
              </div>
              <p className="text-muted-foreground">
                {run.status_reasons[0] ?? 'Artefak evaluasi dimuat.'}
              </p>
            </CardContent>
          </Card>

          <EvaluationKpiStrip items={run.method_summary} />

          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
            <TabsList className="h-auto w-full flex-wrap justify-start gap-1">
              <TabsTrigger value="overview" className="flex-none px-3 py-1.5">
                Ringkasan &amp; Grafik
              </TabsTrigger>
              <TabsTrigger value="tuning" className="flex-none px-3 py-1.5">
                Bobot Tuning
              </TabsTrigger>
              <TabsTrigger value="queries" className="flex-none px-3 py-1.5">
                Rincian per Kueri ({formatNumber(run.per_query.total)})
              </TabsTrigger>
              <TabsTrigger value="provenance" className="flex-none px-3 py-1.5">
                Bukti &amp; Integritas
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview">
              <EvaluationMetricsChart items={run.method_summary} split={run.split} />
            </TabsContent>

            <TabsContent value="tuning">
              {run.tuning_best.length > 0 ? (
                <EvaluationTuningCard items={run.tuning_best} />
              ) : (
                <EmptyState
                  asCard
                  message="Data bobot grid search tidak tersedia pada bundle ini."
                />
              )}
            </TabsContent>

            <TabsContent value="queries">
              <EvaluationPerQueryTable
                run={run}
                filters={filters}
                perPage={perPage}
                onFiltersChange={handleFiltersChange}
                onPageChange={setPage}
                onPerPageChange={(nextPerPage) => {
                  setPerPage(nextPerPage)
                  setPage(1)
                }}
              />
            </TabsContent>

            <TabsContent value="provenance">
              <EvaluationProvenanceCard run={run} />
            </TabsContent>
          </Tabs>
        </div>
      )}
    </main>
  )
}
