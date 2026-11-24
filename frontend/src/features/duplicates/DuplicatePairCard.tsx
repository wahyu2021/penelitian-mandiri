import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  type DuplicateArchiveSide,
  type DuplicateCandidate,
  type DuplicateDecision,
  saveDuplicateDecision,
} from '@/lib/api/duplicates'
import { ApiError } from '@/lib/api/session'
import { formatCurrencyIdr, formatDateTimeId } from '@/lib/format'

const REASON_LABELS: Record<string, string> = {
  same_spm: 'Nomor SPM sama',
  same_summary: 'Ringkasan identik',
  same_amount_opd_year: 'OPD, tahun, nominal sama & teks mirip',
}

const DECISION_LABELS: Record<DuplicateDecision, string> = {
  duplikat: 'Duplikat',
  bukan_duplikat: 'Bukan duplikat',
  perlu_cek: 'Perlu cek fisik',
}

function formatLocation(loc: DuplicateArchiveSide['location']): string {
  const parts = [
    loc.block ? `Blok ${loc.block}` : null,
    loc.rack ? `Rak ${loc.rack}` : null,
    loc.row ? `Baris ${loc.row}` : null,
    loc.box ? `Boks ${loc.box}` : null,
  ].filter(Boolean)
  return parts.length > 0 ? parts.join(' · ') : 'Belum dicatat'
}

function ArchiveSideColumn({ title, side }: { title: string; side: DuplicateArchiveSide }) {
  return (
    <Card size="sm" className="justify-between bg-muted/20">
      <CardHeader className="border-b">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>
            {title} ·{' '}
            <Link to={`/app/archives/${side.id}`} className="text-primary underline">
              Arsip #{side.id}
            </Link>
          </CardTitle>
          <CardDescription className="text-xs">
            {side.year ?? 'Tahun kosong'} {side.opd_name ? `· ${side.opd_name}` : ''}
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent>
        <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
          <div>
            <dt className="text-muted-foreground">Nomor SPM</dt>
            <dd className="font-mono font-medium">{side.spm_number ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Nomor SP2D</dt>
            <dd className="font-mono font-medium">{side.sp2d_number ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Tanggal dokumen</dt>
            <dd className="font-medium">{side.document_date ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Nominal</dt>
            <dd className="font-medium tabular-nums">
              {side.amount_rp !== null ? formatCurrencyIdr(side.amount_rp) : '—'}
            </dd>
          </div>
          <div className="col-span-2">
            <dt className="text-muted-foreground">Nama pihak</dt>
            <dd className="font-medium">{side.party_name ?? '—'}</dd>
          </div>
          <div className="col-span-2">
            <dt className="text-muted-foreground">Lokasi fisik</dt>
            <dd>{formatLocation(side.location)}</dd>
          </div>
        </dl>
      </CardContent>

      <CardFooter className="flex-col items-start gap-1">
        <p className="text-xs font-medium text-muted-foreground">Ringkasan asli</p>
        <p className="text-xs leading-relaxed whitespace-pre-wrap">{side.summary_raw}</p>
      </CardFooter>
    </Card>
  )
}

export function DuplicatePairCard({
  candidate,
  csrfToken,
  onSaved,
}: {
  candidate: DuplicateCandidate
  csrfToken: string
  onSaved: () => void
}) {
  const [decision, setDecision] = useState<DuplicateDecision>(candidate.decision ?? 'perlu_cek')
  const [notes, setNotes] = useState(candidate.notes)
  const [savedFlag, setSavedFlag] = useState(false)

  const mutation = useMutation({
    mutationFn: () =>
      saveDuplicateDecision(
        candidate.archive_a_id,
        candidate.archive_b_id,
        decision,
        notes,
        csrfToken,
      ),
    onSuccess: () => {
      setSavedFlag(true)
      onSaved()
    },
  })

  const pairKey = `${candidate.archive_a_id}-${candidate.archive_b_id}`
  const similarityPct = `${(candidate.similarity * 100).toFixed(0)}%`

  return (
    <Card>
      <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle className="text-base">
            Pasangan #{candidate.archive_a_id} &amp; #{candidate.archive_b_id}
          </CardTitle>
          <CardDescription>
            Indikasi: {REASON_LABELS[candidate.reason] ?? candidate.reason} (kemiripan{' '}
            {similarityPct})
          </CardDescription>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={candidate.decision ? 'default' : 'secondary'}>
            {candidate.decision ? DECISION_LABELS[candidate.decision] : 'Belum ditinjau'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        <div className="grid gap-4 md:grid-cols-2">
          <ArchiveSideColumn title="Arsip A" side={candidate.archive_a} />
          <ArchiveSideColumn title="Arsip B" side={candidate.archive_b} />
        </div>

        <Card size="sm">
          <CardContent>
            <form
              className="space-y-3"
              onSubmit={(event) => {
                event.preventDefault()
                setSavedFlag(false)
                mutation.mutate()
              }}
            >
              <div
                className="flex flex-wrap items-center gap-2"
                role="group"
                aria-label={`Keputusan pasangan ${pairKey}`}
              >
                {(['duplikat', 'bukan_duplikat', 'perlu_cek'] as const).map((option) => (
                  <Button
                    key={option}
                    type="button"
                    size="sm"
                    variant={decision === option ? 'default' : 'outline'}
                    onClick={() => {
                      setDecision(option)
                      setSavedFlag(false)
                    }}
                  >
                    {DECISION_LABELS[option]}
                  </Button>
                ))}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor={`dup-notes-${pairKey}`}>Catatan penilai (opsional)</Label>
                <Textarea
                  id={`dup-notes-${pairKey}`}
                  rows={2}
                  value={notes}
                  onChange={(event) => {
                    setNotes(event.target.value)
                    setSavedFlag(false)
                  }}
                  placeholder="Catat alasan apakah arsip ini duplikat atau berkas berbeda."
                />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Button type="submit" size="sm" disabled={mutation.isPending}>
                  {mutation.isPending ? 'Menyimpan…' : 'Simpan keputusan'}
                </Button>
                {savedFlag && !mutation.isPending && (
                  <span role="status" className="text-xs font-medium text-primary">
                    Keputusan tersimpan tanpa mengubah arsip sumber.
                  </span>
                )}
                {mutation.isError && (
                  <span role="alert" className="text-xs text-destructive">
                    {mutation.error instanceof ApiError
                      ? mutation.error.message
                      : 'Keputusan belum dapat disimpan.'}
                  </span>
                )}
              </div>
            </form>
          </CardContent>
        </Card>

        {(candidate.reviewed_by || candidate.history.length > 0) && (
          <div className="space-y-1 text-xs text-muted-foreground">
            {candidate.reviewed_by && candidate.reviewed_at && (
              <p>
                Terakhir ditinjau oleh <strong>{candidate.reviewed_by}</strong> pada{' '}
                {formatDateTimeId(candidate.reviewed_at)}.
              </p>
            )}
            {candidate.history.length > 0 && (
              <p>
                Jejak koreksi ({candidate.history.length} catatan terakhir):{' '}
                {candidate.history
                  .map(
                    (h) => `${h.old_decision ?? 'awal'} → ${h.new_decision} (${h.actor_username})`,
                  )
                  .join(' · ')}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
