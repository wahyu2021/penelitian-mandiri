import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Lock } from 'lucide-react'
import { useParams } from 'react-router'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { RelevanceReviewPanel } from '@/features/relevance/RelevanceReviewPanel'
import {
  fetchPublicRelevance,
  type PublicRelevanceData,
  savePublicRelevanceAnswer,
  submitPublicRelevance,
} from '@/lib/api/publicTasks'
import { ApiError } from '@/lib/api/session'
import { formatDateTimeId } from '@/lib/format'

export function PublicRelevancePage() {
  const { token = '' } = useParams()
  const [position, setPosition] = useState<number | null>(null)
  const queryClient = useQueryClient()

  const queryKey = ['public-relevance', token, position] as const
  const reviewQuery = useQuery({
    queryKey,
    queryFn: () => fetchPublicRelevance(token, position),
    enabled: Boolean(token),
    gcTime: 0,
    refetchOnWindowFocus: false,
    retry: false,
  })

  const data = reviewQuery.data
  const state = data?.review
  const linkInfo = data?.link
  const submittedAt = state?.submitted_at ?? linkInfo?.submitted_at ?? null

  const onPosition = (next: number | null) => {
    if (next === position) void reviewQuery.refetch()
    else setPosition(next)
  }

  return (
    <div className="min-h-svh bg-stone-50 px-4 py-6 sm:py-10">
      <main className="mx-auto max-w-4xl space-y-5">
        <header className="space-y-1">
          <p className="text-xs font-medium tracking-wide text-primary uppercase">
            SIMANIS · Penilaian Relevansi Tanpa Login
          </p>
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
            {linkInfo ? linkInfo.label || 'Penilaian Relevansi Arsip' : 'Penilaian Relevansi'}
          </h1>
          <p className="text-sm text-muted-foreground">
            Nilai kecocokan kebutuhan informasi dengan ringkasan asli arsip. Isian tersimpan saat
            Anda menekan tombol simpan.
          </p>
        </header>

        {reviewQuery.isPending && (
          <LoadingState label="Membuka tautan penilaian" rows={2} rowClassName="h-36 w-full" />
        )}

        {reviewQuery.isError &&
          (reviewQuery.error instanceof ApiError &&
          (reviewQuery.error.status === 403 ||
            reviewQuery.error.status === 404 ||
            reviewQuery.error.status === 410) ? (
            <Alert variant="destructive">
              <AlertTitle>Tautan tidak dapat diakses</AlertTitle>
              <AlertDescription>{reviewQuery.error.message}</AlertDescription>
            </Alert>
          ) : (
            <ErrorStateCard
              title={
                reviewQuery.error instanceof ApiError
                  ? reviewQuery.error.message
                  : 'Tautan penilaian tidak dapat dibuka.'
              }
              onRetry={() => void reviewQuery.refetch()}
            />
          ))}

        {data && linkInfo && state && (
          <>
            <Card size="sm">
              <CardContent className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">Penilai: {linkInfo.target_username}</Badge>
                  {linkInfo.target_slot && (
                    <Badge variant="secondary">Slot Penilai {linkInfo.target_slot}</Badge>
                  )}
                </div>
                {linkInfo.lock_single_device && (
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <Lock aria-hidden="true" className="size-3.5" /> Terkunci pada perangkat ini
                  </span>
                )}
              </CardContent>
            </Card>

            {submittedAt ? (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-primary">
                    <CheckCircle2 aria-hidden="true" className="size-5" />
                    Penilaian relevansi telah diserahkan
                  </CardTitle>
                  <CardDescription>
                    Diserahkan pada {formatDateTimeId(submittedAt)} · {state.rated} dari{' '}
                    {state.total} pasangan telah dinilai.
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Tautan ini otomatis terkunci setelah penyerahan final. Anda dapat menutup halaman
                  ini.
                </CardContent>
              </Card>
            ) : (
              <RelevanceReviewPanel
                key={`${state.item.id}-${state.item.revision}`}
                state={state}
                version={linkInfo.target_version ?? ''}
                csrf=""
                publicMode
                saveAnswerFn={(pairId, value) => savePublicRelevanceAnswer(token, pairId, value)}
                submitReviewFn={() => submitPublicRelevance(token)}
                onPosition={onPosition}
                onRefresh={async () => {
                  if (position === null) setPosition(state.index)
                  else await reviewQuery.refetch()
                }}
                onSaved={(answer, progress) => {
                  queryClient.setQueryData<PublicRelevanceData>(queryKey, {
                    ...data,
                    review: {
                      ...state,
                      rated: progress.rated,
                      item: { ...state.item, ...answer, revision: progress.revision },
                    },
                  })
                }}
                onSubmitted={(timestamp) => {
                  queryClient.setQueryData<PublicRelevanceData>(queryKey, {
                    link: { ...linkInfo, submitted_at: timestamp },
                    review: { ...state, submitted_at: timestamp },
                  })
                }}
              />
            )}
          </>
        )}
      </main>
    </div>
  )
}
