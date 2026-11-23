import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Database, HelpCircle } from 'lucide-react'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useSession } from '@/features/auth/useSession'
import { QualityCoverageCard } from '@/features/quality/QualityCoverageCard'
import { QualityIssuesTable, type QualityFilters } from '@/features/quality/QualityIssuesTable'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { fetchMetadataQuality } from '@/lib/api/quality'
import { ApiError } from '@/lib/api/session'
import { formatNumber } from '@/lib/format'

export function QualityPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === 'admin'
  const [filters, setFilters] = useState<QualityFilters>({})
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(25)

  const query = useQuery({
    queryKey: [
      'research-quality',
      filters.issueType ?? null,
      filters.fieldName ?? null,
      filters.spmConfidence ?? null,
      page,
      perPage,
    ],
    queryFn: () =>
      fetchMetadataQuality({
        issueType: filters.issueType,
        fieldName: filters.fieldName,
        spmConfidence: filters.spmConfidence,
        page,
        perPage,
      }),
    placeholderData: keepPreviousData,
    enabled: isAdmin,
  })

  useUnauthorizedRedirect([query.error])

  if (!isAdmin) {
    return <ForbiddenCard message="Tinjauan kualitas metadata hanya tersedia untuk admin." />
  }

  const errorMessage =
    query.error instanceof ApiError
      ? query.error.message
      : 'Data kualitas metadata belum dapat dimuat.'

  const summary = query.data

  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Validasi data"
        title="Tinjauan kualitas metadata"
        description="Cakupan ekstraksi metadata 5 field, status konfirmasi kode SPM, dan rincian isu impor dari basis data lokal."
      />

      {query.isPending && (
        <LoadingState label="Memuat kualitas metadata" rows={2} rowClassName="h-44 w-full" />
      )}

      {query.isError && (
        <ErrorStateCard title={errorMessage} onRetry={() => void query.refetch()} />
      )}

      {summary && (
        <div className="space-y-6">
          <section
            aria-label="Ringkasan kualitas metadata"
            className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
          >
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1.5">
                  <Database aria-hidden="true" className="size-3.5 text-primary" />
                  Total arsip
                </CardDescription>
                <CardTitle className="text-2xl tabular-nums">
                  {formatNumber(summary.total_archives)}
                </CardTitle>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1.5">
                  <AlertTriangle aria-hidden="true" className="size-3.5 text-primary" />
                  Total isu tercatat
                </CardDescription>
                <CardTitle className="text-2xl tabular-nums">
                  {formatNumber(summary.total_issues)}
                </CardTitle>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1.5">
                  <HelpCircle aria-hidden="true" className="size-3.5 text-primary" />
                  Kode SPM dugaan
                </CardDescription>
                <CardTitle className="text-2xl tabular-nums">
                  {formatNumber(summary.spm_confidence_summary.dugaan)}
                </CardTitle>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1.5">
                  <CheckCircle2 aria-hidden="true" className="size-3.5 text-primary" />
                  Kode SPM terkonfirmasi
                </CardDescription>
                <CardTitle className="text-2xl tabular-nums">
                  {formatNumber(summary.spm_confidence_summary.terkonfirmasi)}
                </CardTitle>
              </CardHeader>
            </Card>
          </section>

          <QualityCoverageCard
            coverage={summary.metadata_coverage}
            totalArchives={summary.total_archives}
            suspectCount={summary.spm_confidence_summary.dugaan}
          />

          <QualityIssuesTable
            summary={summary}
            filters={filters}
            perPage={perPage}
            onFiltersChange={(next) => {
              setFilters(next)
              setPage(1)
            }}
            onPageChange={setPage}
            onPerPageChange={(nextPerPage) => {
              setPerPage(nextPerPage)
              setPage(1)
            }}
          />
        </div>
      )}
    </main>
  )
}
