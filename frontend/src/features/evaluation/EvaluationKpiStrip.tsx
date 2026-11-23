import { Award, Gauge, Sparkles, Target } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDecimal, formatMethodLabel, formatPercent } from '@/features/evaluation/formatters'
import type { MethodSummaryItem } from '@/lib/api/evaluation'

export function EvaluationKpiStrip({ items }: { items: MethodSummaryItem[] }) {
  if (items.length === 0) return null

  const bestMrr = items.reduce((best, item) => (item.mrr_at_10 > best.mrr_at_10 ? item : best))
  const baseline = items.find(
    (item) => item.method === 'like_baseline' || item.config === 'baseline',
  )
  const bestRecall = items.reduce((best, item) => (item.mean_r10 > best.mean_r10 ? item : best))
  const fastest = items.reduce((fast, item) =>
    item.median_latency_ms < fast.median_latency_ms ? item : fast,
  )

  const mrrDelta = baseline ? bestMrr.mrr_at_10 - baseline.mrr_at_10 : null

  return (
    <section aria-label="Sorotan metrik utama" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card>
        <CardHeader className="pb-2">
          <CardDescription className="flex items-center gap-1.5">
            <Award aria-hidden="true" className="size-3.5 text-primary" />
            MRR@10 tertinggi
          </CardDescription>
          <CardTitle className="text-2xl tabular-nums">
            {formatDecimal(bestMrr.mrr_at_10, 4)}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground">
          {formatMethodLabel(bestMrr.method, bestMrr.config)} · P@5{' '}
          {formatDecimal(bestMrr.mean_p5, 4)}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardDescription className="flex items-center gap-1.5">
            <Sparkles aria-hidden="true" className="size-3.5 text-primary" />
            Selisih vs LIKE Baseline
          </CardDescription>
          <CardTitle className="text-2xl tabular-nums">
            {mrrDelta === null ? '—' : `${mrrDelta >= 0 ? '+' : ''}${formatDecimal(mrrDelta, 4)}`}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground">
          {baseline
            ? `Baseline LIKE MRR@10: ${formatDecimal(baseline.mrr_at_10, 4)}`
            : 'Pembanding LIKE tidak ada di filter ini'}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardDescription className="flex items-center gap-1.5">
            <Target aria-hidden="true" className="size-3.5 text-primary" />
            Recall@10 tertinggi
          </CardDescription>
          <CardTitle className="text-2xl tabular-nums">
            {formatPercent(bestRecall.mean_r10)}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground">
          {formatMethodLabel(bestRecall.method, bestRecall.config)} · Hit@10{' '}
          {formatPercent(bestRecall.hit_at_10_rate)}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardDescription className="flex items-center gap-1.5">
            <Gauge aria-hidden="true" className="size-3.5 text-primary" />
            Median latensi tercepat
          </CardDescription>
          <CardTitle className="text-2xl tabular-nums">
            {formatDecimal(fastest.median_latency_ms, 1)} ms
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground">
          {formatMethodLabel(fastest.method, fastest.config)}
        </CardContent>
      </Card>
    </section>
  )
}
