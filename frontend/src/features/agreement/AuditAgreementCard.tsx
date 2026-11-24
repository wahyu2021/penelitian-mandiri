import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { AgreementStatusBadge } from '@/features/agreement/AgreementStatusBadge'
import type { AuditAgreement } from '@/lib/api/agreement'
import { formatNumber } from '@/lib/format'

const FIELD_LABELS: Record<string, string> = {
  spm: 'Nomor SPM',
  sp2d: 'Nomor SP2D',
  date: 'Tanggal',
  amount: 'Nominal',
  party: 'Nama Pihak',
}

function formatPercent(value: number | null): string {
  if (value === null) return '—'
  return `${(value * 100).toFixed(1).replace('.', ',')}%`
}

function formatKappa(value: number | null, status: AuditAgreement['status']): string {
  if (status === 'pending') return 'Tertunda'
  if (value === null) return 'Tidak terdefinisi'
  return value.toFixed(3).replace('.', ',')
}

export function AuditAgreementCard({
  audit,
  rater1,
  rater2,
  onRatersChange,
}: {
  audit: AuditAgreement
  rater1?: number
  rater2?: number
  onRatersChange: (nextRater1: number, nextRater2: number) => void
}) {
  const activeRater1 = rater1 ?? audit.selected_raters[0]?.user_id
  const activeRater2 = rater2 ?? audit.selected_raters[1]?.user_id

  return (
    <Card>
      <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle>Kesepakatan audit ekstraksi</CardTitle>
          <CardDescription>
            {audit.dataset
              ? `${formatNumber(audit.dataset.sample_count)} arsip (${formatNumber(audit.dataset.total_cells)} sel) · Berkas ${audit.dataset.source_filename}`
              : 'Sampel audit ekstraksi belum dimuat.'}
          </CardDescription>
        </div>
        <AgreementStatusBadge status={audit.status} />
      </CardHeader>
      <CardContent className="space-y-5 text-sm">
        {audit.reviewers.length >= 2 &&
          activeRater1 !== undefined &&
          activeRater2 !== undefined && (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="audit-rater-1">Penilai audit pertama</Label>
                <Select
                  value={String(activeRater1)}
                  onValueChange={(value) => onRatersChange(Number(value), activeRater2)}
                >
                  <SelectTrigger id="audit-rater-1" aria-label="Penilai audit pertama">
                    <SelectValue placeholder="Pilih penilai pertama" />
                  </SelectTrigger>
                  <SelectContent>
                    {audit.reviewers.map((person) => (
                      <SelectItem
                        key={person.user_id}
                        value={String(person.user_id)}
                        disabled={person.user_id === activeRater2}
                      >
                        {person.username} ({formatNumber(person.rated_cells)} sel)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="audit-rater-2">Penilai audit kedua</Label>
                <Select
                  value={String(activeRater2)}
                  onValueChange={(value) => onRatersChange(activeRater1, Number(value))}
                >
                  <SelectTrigger id="audit-rater-2" aria-label="Penilai audit kedua">
                    <SelectValue placeholder="Pilih penilai kedua" />
                  </SelectTrigger>
                  <SelectContent>
                    {audit.reviewers.map((person) => (
                      <SelectItem
                        key={person.user_id}
                        value={String(person.user_id)}
                        disabled={person.user_id === activeRater1}
                      >
                        {person.username} ({formatNumber(person.rated_cells)} sel)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

        {audit.overall && (
          <div className="grid gap-3 sm:grid-cols-3">
            <Card size="sm">
              <CardHeader className="pb-1">
                <CardDescription className="text-xs">Sel berpasangan</CardDescription>
                <CardTitle className="text-base tabular-nums">
                  {formatNumber(audit.overall.n_paired)} / {formatNumber(audit.overall.n_total)}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card size="sm">
              <CardHeader className="pb-1">
                <CardDescription className="text-xs">Kesepakatan keseluruhan</CardDescription>
                <CardTitle className="text-base tabular-nums">
                  {audit.overall.percentage_agreement === null
                    ? 'Tertunda'
                    : `${formatPercent(audit.overall.percentage_agreement)} (${formatNumber(audit.overall.n_agreed ?? 0)}/${formatNumber(audit.overall.n_paired)})`}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card size="sm">
              <CardHeader className="pb-1">
                <CardDescription className="text-xs">
                  Cohen&apos;s kappa keseluruhan
                </CardDescription>
                <CardTitle className="text-base tabular-nums">
                  {formatKappa(audit.overall.cohen_kappa, audit.overall.status)}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>
        )}

        {audit.fields.length > 0 && (
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Field ekstraksi</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Berpasangan</TableHead>
                  <TableHead className="text-right">Sepakat</TableHead>
                  <TableHead className="text-right">Persentase</TableHead>
                  <TableHead className="text-right">Cohen&apos;s kappa</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {audit.fields.map((fieldItem) => (
                  <TableRow key={fieldItem.field}>
                    <TableCell className="font-medium">
                      {FIELD_LABELS[fieldItem.field] ?? fieldItem.field}
                    </TableCell>
                    <TableCell>
                      <AgreementStatusBadge status={fieldItem.status} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatNumber(fieldItem.n_paired)} / {formatNumber(fieldItem.n_total)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {fieldItem.n_agreed === null ? '—' : formatNumber(fieldItem.n_agreed)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatPercent(fieldItem.percentage_agreement)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatKappa(fieldItem.cohen_kappa, fieldItem.status)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {audit.limitations.length > 0 && (
          <Alert role="note">
            <AlertTitle>Keterbatasan &amp; catatan audit</AlertTitle>
            <AlertDescription>
              <ul className="list-disc space-y-1 pl-4">
                {audit.limitations.map((note, idx) => (
                  <li key={idx}>{note}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}
