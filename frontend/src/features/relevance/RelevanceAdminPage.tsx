import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RelevanceLegacyImportForm } from '@/features/relevance/RelevanceLegacyImportForm'
import { RelevanceSetupCard } from '@/features/relevance/RelevanceSetupCard'
import { TaskLinksManager } from '@/features/forms/TaskLinksManager'
import { useSession } from '@/features/auth/useSession'
import { reviewError, useReviewExpiry } from '@/features/relevance/useReviewSession'
import { getRelevanceAdmin, relevanceExportUrl } from '@/lib/api/relevance'

export function RelevanceAdminPage() {
  const { data: session } = useSession()
  const client = useQueryClient()
  const admin = session?.user?.role === 'admin'
  const key = ['relevance-admin', session?.user?.id] as const
  const overview = useQuery({ queryKey: key, queryFn: getRelevanceAdmin, enabled: admin })
  useReviewExpiry(overview.error)

  if (!admin || !session) {
    return <ForbiddenCard message="Kelola penilaian hanya tersedia untuk admin." />
  }

  const refresh = () => client.invalidateQueries({ queryKey: key })
  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Evaluasi relevansi"
        title="Kelola penilaian relevansi"
        description="Siapkan penugasan penilai dan migrasi jawaban lama tanpa menimpa isian web."
      />
      {overview.isPending && (
        <LoadingState label="Memuat data penugasan" rows={1} rowClassName="h-40 w-full" />
      )}
      {overview.isError && (
        <ErrorStateCard
          title={reviewError(overview.error, 'Daftar penugasan gagal dimuat.')}
          onRetry={() => void overview.refetch()}
        />
      )}
      {overview.data && (
        <>
          <RelevanceSetupCard data={overview.data} csrf={session.csrf_token} refresh={refresh} />
          {overview.data.reviews.map((review) => {
            const exportReady = review.reviewers.every((person) => person.submitted_at)
            return (
              <Card key={review.version}>
                <CardHeader>
                  <CardTitle>
                    <h2 className="break-all">{review.version}</h2>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <p>
                    {review.reviewers[0]?.total ?? 0} pasangan unik · {review.sample_rows} baris
                    pada CSV sampel
                  </p>
                  {review.reviewers.map((person) => (
                    <section key={person.slot} className="space-y-2 border-t pt-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-medium">
                          Penilai {person.slot} · {person.username}
                        </h3>
                        <Badge variant={person.submitted_at ? 'outline' : 'secondary'}>
                          {person.submitted_at ? 'Sudah diserahkan' : 'Belum diserahkan'}
                        </Badge>
                      </div>
                      <p>
                        {person.rated}/{person.total} dinilai
                      </p>
                      <TaskLinksManager
                        taskKind="relevance"
                        version={review.version}
                        slot={person.slot}
                        csrfToken={session.csrf_token}
                        disabled={Boolean(person.submitted_at)}
                      />
                      {!person.submitted_at && (
                        <RelevanceLegacyImportForm
                          version={review.version}
                          slot={person.slot}
                          csrf={session.csrf_token}
                          refresh={refresh}
                        />
                      )}
                      {exportReady && (
                        <Button asChild variant="outline">
                          <a href={relevanceExportUrl(review.version, person.slot)}>
                            <Download aria-hidden="true" /> Unduh CSV penilai {person.slot}
                          </a>
                        </Button>
                      )}
                    </section>
                  ))}
                  {!exportReady && (
                    <p className="text-muted-foreground">
                      CSV tersedia setelah kedua akun menyerahkan jawaban.
                    </p>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </>
      )}
    </main>
  )
}
