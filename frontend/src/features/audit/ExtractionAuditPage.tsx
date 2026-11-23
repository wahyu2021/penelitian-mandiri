import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, Download } from 'lucide-react'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AuditFieldCard, auditFieldLabels } from '@/features/audit/AuditFieldCard'
import { AuditReviewersCard } from '@/features/audit/AuditReviewersCard'
import { useSession } from '@/features/auth/useSession'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { fields, getAuditState } from '@/lib/api/extractionAudit'
import { ApiError } from '@/lib/api/session'

const formatPercent = (value: number | null) =>
  value === null ? '—' : `${(value * 100).toLocaleString('id-ID', { maximumFractionDigits: 1 })}%`

export function ExtractionAuditPage() {
  const session = useSession()
  const [index, setIndex] = useState(0)
  const queryClient = useQueryClient()
  const audit = useQuery({
    queryKey: ['extraction-audit', index],
    queryFn: () => getAuditState(index),
    enabled: Boolean(session.data?.authenticated),
  })

  useUnauthorizedRedirect([audit.error])

  const state = audit.data
  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Evaluasi ekstraksi"
        title="Audit ekstraksi arsip"
        description="Nilai setiap hasil ekstraksi berdasarkan ringkasan mentah. Keputusan dari CSV sumber tidak disalin ke akun ini."
      />
      {session.data?.user?.role === 'admin' && (
        <AuditReviewersCard csrfToken={session.data.csrf_token} />
      )}
      {audit.isPending && (
        <LoadingState label="Memuat sampel audit" rows={2} rowClassName="h-44 w-full" />
      )}
      {audit.isError && (
        <ErrorStateCard
          title={
            audit.error instanceof ApiError
              ? audit.error.message
              : 'Sampel audit belum dapat dimuat.'
          }
          onRetry={() => void audit.refetch()}
        />
      )}
      {state && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-base">Progres penilai</h2>
                <Badge variant={state.final ? 'outline' : 'secondary'}>
                  {state.final ? 'Final' : 'Sementara'}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p>
                {state.completed_samples} dari {state.total_samples} sampel lengkap ·{' '}
                {state.completed_cells} dari {state.total_cells} sel dinilai
              </p>
              <progress
                className="h-2 w-full accent-primary"
                value={state.completed_cells}
                max={state.total_cells}
                aria-label="Progres audit"
              />
              <p className="text-muted-foreground">
                Status:{' '}
                {state.final
                  ? 'Final — seluruh sel sudah dinilai'
                  : 'Sementara — ada sel yang belum dinilai'}
                . Sumber: {state.source_filename} · ekstraktor {state.extractor_version}.
              </p>
              {state.final && (
                <Button variant="outline" asChild>
                  <a href="/api/v1/extraction-audit/export">
                    <Download aria-hidden="true" /> Unduh CSV hasil penilai
                  </a>
                </Button>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>
                <h2 className="text-base">
                  Sampel {state.index + 1} dari {state.total_samples}
                </h2>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={index === 0}
                  onClick={() => setIndex(index - 1)}
                >
                  <ArrowLeft aria-hidden="true" /> Sebelumnya
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={index + 1 >= state.total_samples}
                  onClick={() => setIndex(index + 1)}
                >
                  Berikutnya <ArrowRight aria-hidden="true" />
                </Button>
                <Label htmlFor="audit-jump" className="ml-auto">
                  Ke sampel
                </Label>
                <Input
                  id="audit-jump"
                  className="w-20"
                  type="number"
                  min={1}
                  max={state.total_samples}
                  defaultValue={state.index + 1}
                  key={state.index}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      const value = Number(event.currentTarget.value)
                      if (Number.isInteger(value) && value >= 1 && value <= state.total_samples)
                        setIndex(value - 1)
                    }
                  }}
                />
              </div>
              <p>
                ID arsip: {state.sample.archive_id} · Status: {state.sample.archive_status}
              </p>
              <div className="rounded-md border bg-muted/30 p-4">
                <p className="font-medium">Ringkasan mentah</p>
                <p className="mt-2 whitespace-pre-wrap break-words">{state.sample.summary_raw}</p>
              </div>
            </CardContent>
          </Card>
          <div className="grid gap-4 md:grid-cols-2">
            {fields.map((field) => (
              <AuditFieldCard
                key={`${state.sample.archive_id}-${field}-${state.judgments[field].verdict}-${state.judgments[field].note}`}
                field={field}
                value={state.sample[`extracted_${field}`]}
                archiveId={state.sample.archive_id}
                fingerprint={state.fingerprint}
                savedVerdict={state.judgments[field].verdict}
                savedNote={state.judgments[field].note}
                csrfToken={session.data!.csrf_token}
                onSaved={() => queryClient.invalidateQueries({ queryKey: ['extraction-audit'] })}
              />
            ))}
          </div>
          <Card>
            <CardHeader>
              <CardTitle>
                <h2 className="text-base">Ringkasan penilaian Anda</h2>
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
              {fields.map((field) => {
                const result = state.results[field]
                return (
                  <div key={field} className="rounded-md border p-3">
                    <p className="font-medium">{auditFieldLabels[field]}</p>
                    <p className="text-muted-foreground">
                      {result.rated}/{result.total} · {result.status}
                    </p>
                    <p>
                      Ketepatan {formatPercent(result.metrics?.ketepatan ?? null)} · Keterambilan{' '}
                      {formatPercent(result.metrics?.keterambilan ?? null)}
                    </p>
                  </div>
                )
              })}
            </CardContent>
          </Card>
        </>
      )}
    </main>
  )
}
