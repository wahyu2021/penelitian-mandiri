import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { saveAuditField, type AuditField, type Verdict } from '@/lib/api/extractionAudit'
import { ApiError } from '@/lib/api/session'

const UNRATED_VALUE = '__none__'

export const auditFieldLabels: Record<AuditField, string> = {
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

export function AuditFieldCard({
  field,
  value,
  archiveId,
  fingerprint,
  savedVerdict,
  savedNote,
  csrfToken,
  readOnly = false,
  saveFn,
  onSaved,
}: {
  field: AuditField
  value: string
  archiveId: number
  fingerprint: string
  savedVerdict: Verdict | null
  savedNote: string
  csrfToken: string
  readOnly?: boolean
  saveFn?: (verdict: Verdict | null, note: string) => Promise<void>
  onSaved: () => Promise<unknown>
}) {
  const [verdict, setVerdict] = useState<Verdict | ''>(savedVerdict ?? '')
  const [note, setNote] = useState(savedNote)
  const mutation = useMutation({
    mutationFn: () =>
      saveFn
        ? saveFn(verdict || null, note)
        : saveAuditField(archiveId, field, verdict || null, note, fingerprint, csrfToken),
    onSuccess: onSaved,
  })
  const dirty = verdict !== (savedVerdict ?? '') || note !== savedNote

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h3 className="text-base">{auditFieldLabels[field]}</h3>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="rounded-md bg-muted/40 p-3">
          <span className="text-muted-foreground">Hasil ekstraksi</span>
          <p className="mt-1 break-words font-medium">{value || 'Kosong'}</p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor={`verdict-${field}`}>Penilaian {auditFieldLabels[field]}</Label>
          <Select
            disabled={readOnly}
            value={verdict || UNRATED_VALUE}
            onValueChange={(next) => setVerdict(next === UNRATED_VALUE ? '' : (next as Verdict))}
          >
            <SelectTrigger id={`verdict-${field}`} className="w-full">
              <SelectValue placeholder="Belum dinilai" />
            </SelectTrigger>
            <SelectContent position="popper">
              <SelectItem value={UNRATED_VALUE}>Belum dinilai</SelectItem>
              {Object.entries(verdictLabels).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor={`note-${field}`}>Catatan (opsional)</Label>
          <Input
            id={`note-${field}`}
            disabled={readOnly}
            value={note}
            maxLength={1000}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Alasan penilaian bila perlu"
          />
        </div>
        {!readOnly && (
          <Button
            size="sm"
            disabled={!dirty || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            Simpan {auditFieldLabels[field]}
          </Button>
        )}
        {mutation.isError && (
          <Alert variant="destructive">
            <AlertDescription>
              {mutation.error instanceof ApiError
                ? mutation.error.message
                : 'Gagal menyimpan penilaian.'}
            </AlertDescription>
          </Alert>
        )}
        {mutation.isSuccess && !dirty && (
          <Alert role="status">
            <AlertDescription>Tersimpan.</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}
