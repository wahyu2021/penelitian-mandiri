import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, Download, RefreshCw } from 'lucide-react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Skeleton } from '@/components/ui/skeleton'
import { sessionKey, useSession } from '@/features/auth/useSession'
import {
  fields,
  getAuditReviewers,
  getAuditState,
  saveAuditField,
  setAuditReviewer,
  type AuditField,
  type Verdict,
} from '@/lib/api/extractionAudit'
import { ApiError } from '@/lib/api/session'

const labels: Record<AuditField, string> = {
  spm: 'Nomor SPM',
  sp2d: 'Nomor SP2D',
  date: 'Tanggal',
  amount: 'Nominal',
  party: 'Pihak',
}
const verdictLabels: Record<Verdict, string> = {
  benar: 'Benar',
  salah: 'Salah',
  terlewat: 'Terlewat',
  tidak_ada_di_teks: 'Tidak ada di teks',
}
const formatPercent = (value: number | null) =>
  value === null ? '—' : `${(value * 100).toLocaleString('id-ID', { maximumFractionDigits: 1 })}%`

function FieldCard({
  field,
  value,
  archiveId,
  fingerprint,
  savedVerdict,
  savedNote,
  csrfToken,
  onSaved,
}: {
  field: AuditField
  value: string
  archiveId: number
  fingerprint: string
  savedVerdict: Verdict | null
  savedNote: string
  csrfToken: string
  onSaved: () => Promise<unknown>
}) {
  const [verdict, setVerdict] = useState<Verdict | ''>(savedVerdict ?? '')
  const [note, setNote] = useState(savedNote)
  const mutation = useMutation({
    mutationFn: () =>
      saveAuditField(archiveId, field, verdict || null, note, fingerprint, csrfToken),
    onSuccess: onSaved,
  })
  const dirty = verdict !== (savedVerdict ?? '') || note !== savedNote
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h3 className="text-base">{labels[field]}</h3>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="rounded-md bg-muted/40 p-3">
          <span className="text-muted-foreground">Hasil ekstraksi</span>
          <p className="mt-1 break-words font-medium">{value || 'Kosong'}</p>
        </div>
        <label className="block font-medium" htmlFor={`verdict-${field}`}>
          Penilaian {labels[field]}
        </label>
        <NativeSelect
          id={`verdict-${field}`}
          value={verdict}
          onChange={(event) => setVerdict(event.target.value as Verdict | '')}
        >
          <NativeSelectOption value="">Belum dinilai</NativeSelectOption>
          {Object.entries(verdictLabels).map(([key, label]) => (
            <NativeSelectOption key={key} value={key}>
              {label}
            </NativeSelectOption>
          ))}
        </NativeSelect>
        <label className="block font-medium" htmlFor={`note-${field}`}>
          Catatan (opsional)
        </label>
        <Input
          id={`note-${field}`}
          value={note}
          maxLength={1000}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Alasan penilaian bila perlu"
        />
        <Button size="sm" disabled={!dirty || mutation.isPending} onClick={() => mutation.mutate()}>
          Simpan {labels[field]}
        </Button>
        {mutation.isError && (
          <p role="alert" className="text-destructive">
            {mutation.error instanceof ApiError
              ? mutation.error.message
              : 'Gagal menyimpan penilaian.'}
          </p>
        )}
        {mutation.isSuccess && !dirty && (
          <p role="status" className="text-muted-foreground">
            Tersimpan.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function ReviewerAssignments({ csrfToken }: { csrfToken: string }) {
  const queryClient = useQueryClient()
  const reviewers = useQuery({ queryKey: ['audit-reviewers'], queryFn: getAuditReviewers })
  const mutation = useMutation({
    mutationFn: ({ id, assigned }: { id: number; assigned: boolean }) =>
      setAuditReviewer(id, assigned, csrfToken),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['audit-reviewers'] }),
  })
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2 className="text-base">Petugas penilai</h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-muted-foreground">
          Tugaskan petugas sebelum mereka membuka sampel. Setiap akun memiliki penilaian sendiri.
        </p>
        {reviewers.isPending && <Skeleton className="h-12" />}
        {reviewers.isError && <p role="alert">Daftar petugas belum dapat dimuat.</p>}
        {reviewers.data?.map((person) => (
          <div
            key={person.id}
            className="flex flex-wrap items-center justify-between gap-3 border-t pt-3"
          >
            <span>
              {person.username} {!person.is_active && '(nonaktif)'} ·{' '}
              {person.assigned_at ? 'ditugaskan' : 'belum ditugaskan'}
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={!person.is_active || mutation.isPending}
              onClick={() => mutation.mutate({ id: person.id, assigned: !person.assigned_at })}
            >
              {person.assigned_at ? 'Cabut tugas' : 'Tugaskan'}
            </Button>
          </div>
        ))}
        {mutation.isError && (
          <p role="alert" className="text-destructive">
            Penugasan gagal disimpan.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

export function ExtractionAuditPage() {
  const session = useSession()
  const [index, setIndex] = useState(0)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const audit = useQuery({
    queryKey: ['extraction-audit', index],
    queryFn: () => getAuditState(index),
    enabled: Boolean(session.data?.authenticated),
  })
  useEffect(() => {
    if (audit.error instanceof ApiError && audit.error.status === 401) {
      queryClient.removeQueries({ queryKey: sessionKey })
      navigate('/login', { replace: true })
    }
  }, [audit.error, navigate, queryClient])
  const state = audit.data
  return (
    <main className="space-y-6 py-8 sm:py-10">
      <header>
        <p className="text-sm font-medium text-muted-foreground">Evaluasi ekstraksi</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
          Audit ekstraksi arsip
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Nilai setiap hasil ekstraksi berdasarkan ringkasan mentah. Keputusan dari CSV sumber tidak
          disalin ke akun ini.
        </p>
      </header>
      {session.data?.user?.role === 'admin' && (
        <ReviewerAssignments csrfToken={session.data.csrf_token} />
      )}
      {audit.isPending && <Skeleton className="h-72 w-full" />}
      {audit.isError && (
        <Card role="alert">
          <CardContent className="space-y-3">
            <p>
              {audit.error instanceof ApiError
                ? audit.error.message
                : 'Sampel audit belum dapat dimuat.'}
            </p>
            <Button variant="outline" onClick={() => void audit.refetch()}>
              <RefreshCw aria-hidden="true" /> Coba lagi
            </Button>
          </CardContent>
        </Card>
      )}
      {state && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>
                <h2 className="text-base">Progres penilai</h2>
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
                <label htmlFor="audit-jump" className="ml-auto">
                  Ke sampel
                </label>
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
              <FieldCard
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
                    <p className="font-medium">{labels[field]}</p>
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
