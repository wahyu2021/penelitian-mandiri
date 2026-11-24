import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { EvaluationStatusBadge } from '@/features/evaluation/EvaluationStatusBadge'
import type { EvaluationRun } from '@/lib/api/evaluation'
import { formatDateTimeId, formatNumber } from '@/lib/format'

function shortHash(value: string): string {
  return value.length > 12 ? `${value.slice(0, 12)}…` : value || '—'
}

export function EvaluationProvenanceCard({ run }: { run: EvaluationRun }) {
  const prov = run.provenance
  const counts = run.split_counts
  const noLeakage = counts.split_leakage_count === 0

  return (
    <Card>
      <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle>Bukti keterulangan &amp; integritas run</CardTitle>
          <CardDescription>
            {prov
              ? `Diekspor ${formatDateTimeId(prov.exported_at)} · Ekstraktor ${prov.extractor_version || '—'}`
              : 'Metadata run belum tersedia.'}
          </CardDescription>
        </div>
        <EvaluationStatusBadge status={run.status} />
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {prov && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Card size="sm">
              <CardHeader className="pb-1">
                <CardDescription className="text-xs">Commit Git</CardDescription>
              </CardHeader>
              <CardContent className="font-mono text-xs font-medium">
                {shortHash(prov.commit_sha)} ({prov.tree_clean ? 'bersih' : 'tree kotor'})
              </CardContent>
            </Card>
            <Card size="sm">
              <CardHeader className="pb-1">
                <CardDescription className="text-xs">Hash basis data</CardDescription>
              </CardHeader>
              <CardContent className="font-mono text-xs font-medium">
                {shortHash(prov.data_hash)}
              </CardContent>
            </Card>
            <Card size="sm">
              <CardHeader className="pb-1">
                <CardDescription className="text-xs">Hash set uji</CardDescription>
              </CardHeader>
              <CardContent className="font-mono text-xs font-medium">
                {shortHash(prov.testset_hash)}
              </CardContent>
            </Card>
            <Card size="sm">
              <CardHeader className="pb-1">
                <CardDescription className="text-xs">
                  Manifest &amp; pemisahan split
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-1.5">
                <Badge variant={run.manifest.valid ? 'outline' : 'secondary'}>
                  {run.manifest.valid ? 'Manifest SHA-256 valid' : 'Manifest tak valid'}
                </Badge>
                <Badge variant={noLeakage ? 'outline' : 'destructive'}>
                  {noLeakage
                    ? 'Tuning/test terpisah'
                    : `${formatNumber(counts.split_leakage_count)} kebocoran`}
                </Badge>
              </CardContent>
            </Card>
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Total {formatNumber(counts.n_queries)} varian kueri ({formatNumber(counts.n_base_queries)}{' '}
          kueri dasar): {formatNumber(counts.n_test_queries)} uji (
          {formatNumber(counts.n_test_base_queries)} dasar) &amp;{' '}
          {formatNumber(counts.n_tuning_queries)} tuning (
          {formatNumber(counts.n_tuning_base_queries)} dasar). Seed: {prov?.seed ?? '—'}.
        </p>

        {run.status_reasons.length > 0 && (
          <Alert role="note">
            <AlertTitle>Penjelasan status artefak</AlertTitle>
            <AlertDescription>
              <ul className="list-disc space-y-1 pl-4">
                {run.status_reasons.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}
