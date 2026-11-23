import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { CheckCircle2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { confirmSpmType, type SpmType } from '@/lib/api/extractionAudit'
import { ApiError } from '@/lib/api/session'

export function SpmTypeCard({
  entry,
  csrfToken,
  onConfirmed,
}: {
  entry: SpmType
  csrfToken: string
  onConfirmed: () => Promise<unknown>
}) {
  const [label, setLabel] = useState(entry.label ?? '')
  const [evidence, setEvidence] = useState('')
  const mutation = useMutation({
    mutationFn: () => confirmSpmType(entry.code, label, evidence, csrfToken),
    onSuccess: onConfirmed,
  })
  const confirmed = entry.confidence === 'terkonfirmasi'

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2 className="flex flex-wrap items-center gap-2 text-base">
            <span className="break-all">{entry.code}</span>
            {confirmed ? (
              <Badge
                variant="outline"
                className="border-emerald-200 bg-emerald-50 text-emerald-900"
              >
                <CheckCircle2 aria-label="Terkonfirmasi" className="size-3.5" />
                Terkonfirmasi
              </Badge>
            ) : (
              <Badge variant="secondary">Dugaan</Badge>
            )}
          </h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-muted-foreground">
          {entry.archive_count} arsip · {confirmed ? 'Terkonfirmasi' : 'Dugaan'}
        </p>
        {confirmed ? (
          <>
            <p>Label: {entry.label}</p>
            <p>Dasar: {entry.source_note}</p>
            <p className="text-muted-foreground">
              Oleh {entry.confirmed_by} · {entry.confirmed_at}
            </p>
          </>
        ) : (
          <>
            <div className="space-y-1.5">
              <Label htmlFor={`spm-label-${entry.code}`}>Label hasil konfirmasi</Label>
              <Input
                id={`spm-label-${entry.code}`}
                value={label}
                maxLength={120}
                onChange={(event) => setLabel(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`spm-evidence-${entry.code}`}>Sumber atau bukti konfirmasi</Label>
              <Textarea
                id={`spm-evidence-${entry.code}`}
                className="min-h-24"
                value={evidence}
                maxLength={1000}
                onChange={(event) => setEvidence(event.target.value)}
                placeholder="Tuliskan sumber yang diperiksa dan alasan label ini benar"
              />
            </div>
            <Button
              size="sm"
              disabled={
                mutation.isPending || label.trim().length < 2 || evidence.trim().length < 10
              }
              onClick={() => mutation.mutate()}
            >
              Konfirmasi kode
            </Button>
            {mutation.isError && (
              <Alert variant="destructive">
                <AlertDescription>
                  {mutation.error instanceof ApiError
                    ? mutation.error.message
                    : 'Konfirmasi gagal.'}
                </AlertDescription>
              </Alert>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
