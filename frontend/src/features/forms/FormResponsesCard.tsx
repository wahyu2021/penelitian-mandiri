import { Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { type FormDetail, formExportUrl } from '@/lib/api/publicForms'
import { formatDateTimeId, formatNumber } from '@/lib/format'

export function FormResponsesCard({ detail }: { detail: FormDetail }) {
  const { form, responses, sus_summary: sus } = detail

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle>Rekap jawaban ({formatNumber(responses.length)})</CardTitle>
          <CardDescription>
            Seluruh respons dikaitkan ke kode peserta anonim tanpa login.
          </CardDescription>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline" size="sm">
            <a href={formExportUrl(form.id, 'csv')}>
              <Download aria-hidden="true" /> Ekspor CSV
            </a>
          </Button>
          <Button asChild variant="outline" size="sm">
            <a href={formExportUrl(form.id, 'json')}>
              <Download aria-hidden="true" /> Ekspor JSON
            </a>
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {sus && (
          <div className="grid gap-3 sm:grid-cols-3">
            <Card size="sm">
              <CardHeader className="pb-1">
                <CardDescription className="text-xs">Responden SUS</CardDescription>
                <CardTitle className="text-xl tabular-nums">
                  {formatNumber(sus.n_respondents)}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card size="sm">
              <CardHeader className="pb-1">
                <CardDescription className="text-xs">Rata-rata skor SUS</CardDescription>
                <CardTitle className="text-xl tabular-nums">
                  {sus.mean_sus === null ? '—' : sus.mean_sus.toFixed(2).replace('.', ',')}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card size="sm">
              <CardHeader className="pb-1">
                <CardDescription className="text-xs">Median skor SUS</CardDescription>
                <CardTitle className="text-xl tabular-nums">
                  {sus.median_sus === null ? '—' : sus.median_sus.toFixed(2).replace('.', ',')}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>
        )}

        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Kode peserta</TableHead>
                <TableHead>Peran</TableHead>
                {form.form_kind === 'sus' && <TableHead className="text-right">Skor SUS</TableHead>}
                <TableHead>Ringkasan / catatan</TableHead>
                <TableHead>Waktu kirim</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {responses.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={form.form_kind === 'sus' ? 5 : 4}
                    className="text-center text-muted-foreground"
                  >
                    Belum ada jawaban yang masuk untuk formulir ini.
                  </TableCell>
                </TableRow>
              ) : (
                responses.map((resp) => (
                  <TableRow key={resp.id}>
                    <TableCell className="font-medium">{resp.participant_code}</TableCell>
                    <TableCell>{resp.participant_role}</TableCell>
                    {form.form_kind === 'sus' && (
                      <TableCell className="text-right font-semibold tabular-nums">
                        {resp.sus_score === null
                          ? '—'
                          : resp.sus_score.toFixed(1).replace('.', ',')}
                      </TableCell>
                    )}
                    <TableCell className="max-w-xs text-xs text-muted-foreground">
                      {form.form_kind === 'sus'
                        ? String(resp.answers.notes || '—')
                        : Object.entries(resp.answers)
                            .map(([k, v]) => `${k}: ${String(v)}`)
                            .join(' | ')}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDateTimeId(resp.submitted_at)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
