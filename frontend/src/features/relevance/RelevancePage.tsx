import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useSession } from '@/features/auth/useSession'
import { RelevanceReviewPanel } from '@/features/relevance/RelevanceReviewPanel'
import { reviewError, useReviewExpiry } from '@/features/relevance/useReviewSession'
import { getReviewAssignments, getReviewItem, type RelevanceState } from '@/lib/api/relevance'

function AssignedReview({
  version,
  userId,
  csrf,
}: {
  version: string
  userId: number
  csrf: string
}) {
  const [position, setPosition] = useState<number | null>(null)
  const client = useQueryClient()
  const key = ['relevance-item', userId, version, position] as const
  const review = useQuery({
    queryKey: key,
    queryFn: () => getReviewItem(version, position),
    gcTime: 0,
    refetchOnWindowFocus: false,
  })
  useReviewExpiry(review.error)
  if (review.isPending) {
    return <LoadingState label="Memuat pasangan penilaian" rows={1} rowClassName="h-60 w-full" />
  }
  if (review.isError) {
    return (
      <ErrorStateCard
        title={reviewError(review.error, 'Pasangan gagal dimuat.')}
        onRetry={() => void review.refetch()}
      />
    )
  }
  const state = review.data
  const onPosition = (next: number | null) => {
    if (next === position) void review.refetch()
    else setPosition(next)
  }
  return (
    <RelevanceReviewPanel
      key={`${state.item.id}-${state.item.revision}`}
      state={state}
      version={version}
      csrf={csrf}
      onPosition={onPosition}
      onRefresh={async () => {
        if (position === null) setPosition(state.index)
        else await review.refetch()
      }}
      onSaved={(answer, progress) => {
        client.setQueryData<RelevanceState>(key, {
          ...state,
          rated: progress.rated,
          item: { ...state.item, ...answer, revision: progress.revision },
        })
      }}
      onSubmitted={(timestamp) =>
        client.setQueryData<RelevanceState>(key, { ...state, submitted_at: timestamp })
      }
    />
  )
}

export function RelevancePage() {
  const { data: session } = useSession()
  const id = session?.user?.id
  const [selection, setSelection] = useState('')
  const assignments = useQuery({
    queryKey: ['relevance-assignments', id],
    queryFn: getReviewAssignments,
    enabled: id !== undefined,
  })
  useReviewExpiry(assignments.error)
  const version = selection || assignments.data?.[0]?.version || ''

  return (
    <main className="space-y-5 py-5 sm:py-6">
      <PageHeader
        eyebrow="Evaluasi relevansi"
        title="Penilaian relevansi"
        description="Nilai kecocokan kebutuhan informasi dengan ringkasan asli arsip."
      />
      {assignments.isPending && (
        <LoadingState label="Memuat penugasan" rows={1} rowClassName="h-28 w-full" />
      )}
      {assignments.isError && (
        <ErrorStateCard
          title={reviewError(assignments.error, 'Penugasan gagal dimuat.')}
          onRetry={() => void assignments.refetch()}
        />
      )}
      {assignments.data?.length === 0 && (
        <EmptyState asCard message="Belum ada penugasan untuk akun ini." />
      )}
      {assignments.data && assignments.data.length > 1 && (
        <div className="max-w-xs space-y-1.5">
          <Label htmlFor="relevance-version">Versi set uji</Label>
          <Select value={version} onValueChange={setSelection}>
            <SelectTrigger id="relevance-version" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent position="popper">
              {assignments.data.map((item) => (
                <SelectItem key={item.version} value={item.version}>
                  {item.version}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      {version && id !== undefined && session && (
        <AssignedReview
          key={`${id}-${version}`}
          version={version}
          userId={id}
          csrf={session.csrf_token}
        />
      )}
    </main>
  )
}
