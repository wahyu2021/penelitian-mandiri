import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { AgreementStatusBadge } from '@/features/agreement/AgreementStatusBadge'
import type { RelevanceAgreement } from '@/lib/api/agreement'
import { formatDateTimeId, formatNumber } from '@/lib/format'

function formatPercent(value: number | null): string {
  if (value === null) return '—'
  return `${(value * 100).toFixed(1).replace('.', ',')}%`
}

function formatKappa(value: number | null): string {
  if (value === null) return 'Tidak terdefinisi'
  return value.toFixed(3).replace('.', ',')
}

export function RelevanceAgreementCard({ item }: { item: RelevanceAgreement }) {
  const matrix = item.confusion_matrix
  const queryTypeEntries = Object.entries(item.agreement_by_query_type).sort(([a], [b]) =>
    a.localeCompare(b),
  )

  return (
    <Card>
      <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle className="break-all">Relevansi · {item.version}</CardTitle>
          <CardDescription>
            {formatNumber(item.n_total)} pasangan unik ({formatNumber(item.n_sample_rows)} baris
            sampel) · Dibuat {formatDateTimeId(item.created_at)}
          </CardDescription>
        </div>
        <AgreementStatusBadge status={item.status} />
      </CardHeader>
      <CardContent className="space-y-5 text-sm">
        <div className="grid gap-3 sm:grid-cols-2">
          {item.reviewers.map((person) => (
            <Card key={person.slot} size="sm">
              <CardContent className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium">
                    Penilai {person.slot} · {person.username}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatNumber(person.rated)} dari {formatNumber(person.total)} pasangan dinilai
                  </p>
                </div>
                <Badge variant={person.submitted_at ? 'outline' : 'secondary'}>
                  {person.submitted_at ? 'Sudah diserahkan' : 'Belum diserahkan'}
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Card size="sm">
            <CardHeader className="pb-1">
              <CardDescription className="text-xs">Pasangan berpasangan</CardDescription>
              <CardTitle className="text-base tabular-nums">
                {formatNumber(item.n_paired)} / {formatNumber(item.n_total)}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card size="sm">
            <CardHeader className="pb-1">
              <CardDescription className="text-xs">Kesepakatan keseluruhan</CardDescription>
              <CardTitle className="text-base tabular-nums">
                {item.percentage_agreement === null
                  ? 'Tertunda'
                  : `${formatPercent(item.percentage_agreement)} (${formatNumber(item.n_agreed ?? 0)}/${formatNumber(item.n_paired)})`}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card size="sm">
            <CardHeader className="pb-1">
              <CardDescription className="text-xs">Kesepakatan kelas relevan</CardDescription>
              <CardTitle className="text-base tabular-nums">
                {item.status === 'pending'
                  ? 'Tertunda'
                  : item.relevant_class_agreement === null
                    ? 'Tidak terdefinisi'
                    : formatPercent(item.relevant_class_agreement)}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card size="sm">
            <CardHeader className="pb-1">
              <CardDescription className="text-xs">Cohen&apos;s kappa</CardDescription>
              <CardTitle className="text-base tabular-nums">
                {item.status === 'pending' ? 'Tertunda' : formatKappa(item.cohen_kappa)}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>

        {matrix && (
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Matriks kesepakatan 2×2</h3>
              <div className="overflow-x-auto rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Penilai 1 \ Penilai 2</TableHead>
                      <TableHead className="text-right">Relevan (1)</TableHead>
                      <TableHead className="text-right">Tidak relevan (0)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell className="font-medium">Relevan (1)</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatNumber(matrix.both_relevant)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatNumber(matrix.rater1_only_relevant)}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-medium">Tidak relevan (0)</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatNumber(matrix.rater2_only_relevant)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatNumber(matrix.both_irrelevant)}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </div>

            {queryTypeEntries.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-medium">Rincian per jenis kueri</h3>
                <div className="overflow-x-auto rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Jenis kueri</TableHead>
                        <TableHead className="text-right">Sepakat / Sampel</TableHead>
                        <TableHead className="text-right">Persentase</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {queryTypeEntries.map(([queryType, detail]) => (
                        <TableRow key={queryType}>
                          <TableCell className="font-medium">{queryType}</TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatNumber(detail.n_agreed)} / {formatNumber(detail.n_samples)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatPercent(detail.agreement)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </div>
        )}

        {item.limitations.length > 0 && (
          <Alert role="note">
            <AlertTitle>Keterbatasan &amp; catatan interpretasi</AlertTitle>
            <AlertDescription>
              <ul className="list-disc space-y-1 pl-4">
                {item.limitations.map((note, idx) => (
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
