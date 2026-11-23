import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, Save, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Skeleton } from '@/components/ui/skeleton'
import { useSession } from '@/features/auth/useSession'
import {
  getReviewAssignments,
  getReviewItem,
  saveReviewAnswer,
  submitReview,
  type Answer,
  type RelevanceState,
} from '@/lib/api/relevance'
import { ApiError } from '@/lib/api/session'
import { reviewError, useReviewExpiry } from '@/features/relevance/useReviewSession'

const criteria: Record<string, string> = {
  nomor_spm: 'Cocokkan nomor SPM, termasuk variasi penulisan yang wajar.',
  topik:
    'Cocokkan pekerjaan atau transaksi yang dimaksud. Periksa termin bila kueri menyebutkannya.',
  pihak: 'Cocokkan pihak yang dimaksud dalam kueri.',
  campuran: 'Periksa bahwa kedua unsur dalam kueri terpenuhi.',
}

function Panel({
  state,
  version,
  csrf,
  onPosition,
  onRefresh,
  onSaved,
  onSubmitted,
}: {
  state: RelevanceState
  version: string
  csrf: string
  onPosition: (position: number | null) => void
  onRefresh: () => Promise<unknown>
  onSaved: (answer: Answer, progress: { rated: number; revision: number }) => void
  onSubmitted: (timestamp: string) => void
}) {
  const item = state.item
  const [decision, setDecision] = useState(item.is_relevant)
  const [doubt, setDoubt] = useState(item.ragu)
  const [notes, setNotes] = useState(item.notes)
  const [confirmSubmit, setConfirmSubmit] = useState(false)
  const dirty = decision !== item.is_relevant || doubt !== item.ragu || notes.trim() !== item.notes
  const answer: Answer = {
    is_relevant: decision,
    ragu: doubt,
    notes: notes.trim(),
    revision: item.revision,
  }
  const save = useMutation({
    mutationFn: () => saveReviewAnswer(version, item.id, answer, csrf),
    onSuccess: (result) => onSaved(answer, result),
  })
  const submit = useMutation({
    mutationFn: () => submitReview(version, csrf),
    onSuccess: (result) => onSubmitted(result.submitted_at),
  })
  useReviewExpiry(save.error, submit.error)
  useEffect(() => {
    if (!dirty) return
    const confirmLeave = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', confirmLeave)
    return () => window.removeEventListener('beforeunload', confirmLeave)
  }, [dirty])
  const busy = save.isPending || submit.isPending
  const stale = save.error instanceof ApiError && save.error.status === 409
  const readOnly = Boolean(state.submitted_at)
  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <p className="text-sm" aria-live="polite">
          {state.rated} dari {state.total} pasangan dinilai{readOnly && ' · Sudah diserahkan'}
        </p>
        <progress
          aria-label="Progres penilaian"
          className="h-2 w-full accent-primary"
          value={state.rated}
          max={state.total}
        />
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,0.65fr)]">
        <Card>
          <CardHeader>
            <CardTitle>
              <h2>
                Pasangan {state.index + 1} dari {state.total}
              </h2>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h3 className="text-xs font-medium text-muted-foreground">Kebutuhan informasi</h3>
              <p className="mt-1 font-semibold break-words whitespace-pre-wrap">
                {item.base_query_text}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {criteria[item.query_type] ??
                  'Bandingkan kebutuhan informasi dengan isi ringkasan.'}
              </p>
            </div>
            <div className="rounded-lg border bg-muted/25 p-4">
              <h3 className="mb-2 text-xs font-medium text-muted-foreground">
                Ringkasan asli arsip
              </h3>
              <p className="text-sm leading-relaxed wrap-anywhere whitespace-pre-wrap">
                {item.summary_raw}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                className="min-h-11"
                disabled={busy || dirty || state.index === 0}
                onClick={() => onPosition(state.index - 1)}
              >
                <ArrowLeft aria-hidden="true" /> Sebelumnya
              </Button>
              <Button
                variant="outline"
                className="min-h-11"
                disabled={busy || dirty || state.index + 1 === state.total}
                onClick={() => onPosition(state.index + 1)}
              >
                Berikutnya <ArrowRight aria-hidden="true" />
              </Button>
              {state.rated < state.total && (
                <Button
                  variant="ghost"
                  className="min-h-11"
                  disabled={busy || dirty}
                  onClick={() => onPosition(null)}
                >
                  Ke yang belum dinilai
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>
              <h2>Keputusan Anda</h2>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <fieldset disabled={busy || readOnly} className="grid gap-1">
              <legend className="sr-only">Relevansi arsip</legend>
              {(
                [
                  ['Relevan', 1],
                  ['Tidak relevan', 0],
                  ['Belum dinilai', null],
                ] as const
              ).map(([label, value]) => (
                <label
                  key={label}
                  className="flex min-h-11 items-center gap-2 rounded-md border px-3 has-checked:border-primary has-checked:bg-primary/5"
                >
                  <input
                    type="radio"
                    name="decision"
                    checked={decision === value}
                    onChange={() => setDecision(value)}
                    className="size-4 accent-primary"
                  />
                  {label}
                </label>
              ))}
            </fieldset>
            <label className="flex min-h-11 items-center gap-2">
              <input
                type="checkbox"
                className="size-4 accent-primary"
                checked={doubt}
                disabled={busy || readOnly}
                onChange={(event) => setDoubt(event.target.checked)}
              />
              Tandai ragu
            </label>
            <label className="block space-y-1">
              <span>Catatan (opsional)</span>
              <textarea
                className="min-h-20 w-full rounded-lg border border-input p-2"
                value={notes}
                maxLength={1000}
                disabled={busy || readOnly}
                onChange={(event) => setNotes(event.target.value)}
              />
            </label>
            {!readOnly && (
              <div className="flex flex-wrap gap-2">
                <Button
                  className="min-h-11"
                  disabled={!dirty || busy || stale}
                  onClick={() => save.mutate()}
                >
                  <Save aria-hidden="true" /> {save.isPending ? 'Menyimpan…' : 'Simpan jawaban'}
                </Button>
                {dirty && !stale && (
                  <Button
                    variant="ghost"
                    className="min-h-11"
                    disabled={busy}
                    onClick={() => {
                      setDecision(item.is_relevant)
                      setDoubt(item.ragu)
                      setNotes(item.notes)
                      save.reset()
                    }}
                  >
                    Batalkan perubahan
                  </Button>
                )}
              </div>
            )}
            {dirty && !save.error && !busy && (
              <p role="status" className="text-muted-foreground">
                Perubahan belum disimpan.
              </p>
            )}
            {!dirty && item.revision > 0 && (
              <p role="status" className="text-muted-foreground">
                Jawaban tersimpan.
              </p>
            )}
            {save.error && (
              <p role="alert" className="text-destructive">
                {reviewError(save.error, 'Jawaban gagal disimpan.')}
              </p>
            )}
            {stale && (
              <Button
                variant="outline"
                className="min-h-11"
                onClick={() => {
                  setDecision(item.is_relevant)
                  setDoubt(item.ragu)
                  setNotes(item.notes)
                  save.reset()
                  void onRefresh()
                }}
              >
                Muat isian terbaru
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
      {!readOnly && state.rated === state.total && (
        <Card>
          <CardContent className="space-y-3 text-sm">
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                className="mt-1 size-4 accent-primary"
                checked={confirmSubmit}
                onChange={(event) => setConfirmSubmit(event.target.checked)}
              />
              Saya sudah memeriksa jawaban. Penyerahan mengunci jawaban saya.
            </label>
            <Button
              className="min-h-11"
              disabled={busy || dirty || !confirmSubmit}
              onClick={() => submit.mutate()}
            >
              <Send aria-hidden="true" /> Serahkan jawaban
            </Button>
            {submit.error && (
              <p role="alert" className="text-destructive">
                {reviewError(submit.error, 'Jawaban gagal diserahkan.')}
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

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
  if (review.isPending) return <Skeleton className="h-60" />
  if (review.isError)
    return (
      <p role="alert" className="text-sm text-destructive">
        {reviewError(review.error, 'Pasangan gagal dimuat.')}{' '}
        <Button variant="outline" onClick={() => void review.refetch()}>
          Coba lagi
        </Button>
      </p>
    )
  const state = review.data
  const onPosition = (next: number | null) => {
    if (next === position) void review.refetch()
    else setPosition(next)
  }
  return (
    <Panel
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
    <main className="space-y-5 py-7 sm:py-9">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Penilaian relevansi</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Nilai kecocokan kebutuhan informasi dengan ringkasan asli arsip.
        </p>
      </header>
      {assignments.isPending && <Skeleton className="h-28" />}
      {assignments.isError && (
        <p role="alert" className="text-sm text-destructive">
          {reviewError(assignments.error, 'Penugasan gagal dimuat.')}{' '}
          <Button variant="outline" onClick={() => void assignments.refetch()}>
            Coba lagi
          </Button>
        </p>
      )}
      {assignments.data?.length === 0 && (
        <Card>
          <CardContent>Belum ada penugasan untuk akun ini.</CardContent>
        </Card>
      )}
      {assignments.data && assignments.data.length > 1 && (
        <div className="space-y-1">
          <label htmlFor="relevance-version" className="block text-sm font-medium">
            Versi set uji
          </label>
          <NativeSelect
            id="relevance-version"
            value={version}
            onChange={(event) => setSelection(event.target.value)}
          >
            {assignments.data.map(({ version }) => (
              <NativeSelectOption key={version} value={version}>
                {version}
              </NativeSelectOption>
            ))}
          </NativeSelect>
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
