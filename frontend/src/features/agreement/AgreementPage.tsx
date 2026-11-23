import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/button'
import { AuditAgreementCard } from '@/features/agreement/AuditAgreementCard'
import { RelevanceAgreementCard } from '@/features/agreement/RelevanceAgreementCard'
import { useSession } from '@/features/auth/useSession'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { agreementExportUrl, fetchAgreementSummary } from '@/lib/api/agreement'
import { ApiError } from '@/lib/api/session'

export function AgreementPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === 'admin'
  const [raters, setRaters] = useState<{ first?: number; second?: number }>({})

  const queryParams = {
    auditRater1: raters.first,
    auditRater2: raters.second,
  }

  const query = useQuery({
    queryKey: ['research-agreement', raters.first ?? null, raters.second ?? null],
    queryFn: () => fetchAgreementSummary(queryParams),
    enabled: isAdmin,
  })

  useUnauthorizedRedirect([query.error])

  if (!isAdmin) {
    return <ForbiddenCard message="Ringkasan kesepakatan penilai hanya tersedia untuk admin." />
  }

  const errorMessage =
    query.error instanceof ApiError
      ? query.error.message
      : 'Ringkasan kesepakatan belum dapat dimuat.'

  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Evaluasi penilai"
        title="Kesepakatan & status validasi"
        description="Ringkasan kesepakatan relevansi dua penilai dan audit ekstraksi dari data penilaian nyata."
        actions={
          <Button asChild variant="outline">
            <a href={agreementExportUrl(queryParams)}>
              <Download aria-hidden="true" /> Unduh laporan JSON
            </a>
          </Button>
        }
      />

      {query.isPending && (
        <LoadingState label="Menghitung kesepakatan penilai" rows={2} rowClassName="h-44 w-full" />
      )}

      {query.isError && (
        <ErrorStateCard title={errorMessage} onRetry={() => void query.refetch()} />
      )}

      {query.data && (
        <div className="space-y-6">
          <section aria-label="Kesepakatan penilaian relevansi" className="space-y-4">
            <h2 className="text-base font-semibold">Penilaian relevansi dua penilai</h2>
            {query.data.relevance.length === 0 ? (
              <EmptyState message="Belum ada tugas penilaian relevansi yang dibuat di basis data web." />
            ) : (
              query.data.relevance.map((item) => (
                <RelevanceAgreementCard key={item.version} item={item} />
              ))
            )}
          </section>

          <section aria-label="Kesepakatan audit ekstraksi" className="space-y-4">
            <h2 className="text-base font-semibold">Audit ekstraksi lima field</h2>
            <AuditAgreementCard
              audit={query.data.audit}
              rater1={raters.first}
              rater2={raters.second}
              onRatersChange={(first, second) => setRaters({ first, second })}
            />
          </section>
        </div>
      )}
    </main>
  )
}
