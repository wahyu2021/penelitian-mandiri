import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Badge } from '@/components/ui/badge'
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
import { formatDecimal, formatMethodLabel, formatPercent } from '@/features/evaluation/formatters'
import type { EvaluationSplit, MethodSummaryItem } from '@/lib/api/evaluation'
import { formatNumber } from '@/lib/format'

type ChartFocus = 'primary' | 'all'
type ChartMetric = 'accuracy' | 'latency'

interface ChartTooltipProps {
  active?: boolean
  label?: string
  metricMode: ChartMetric
  payload?: Array<{
    name?: string
    value?: number
    color?: string
  }>
}

function EvaluationChartTooltip({ active, label, payload, metricMode }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <p className="mb-1.5 font-semibold">{label}</p>
      <ul className="space-y-1">
        {payload.map((entry, idx) => {
          const val = typeof entry.value === 'number' ? entry.value : 0
          const formatted =
            metricMode === 'latency' ? `${formatDecimal(val, 1)} ms` : formatDecimal(val, 4)
          return (
            <li key={idx} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span
                  aria-hidden="true"
                  className="inline-block size-2 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                {entry.name}
              </span>
              <span className="font-medium tabular-nums">{formatted}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export function EvaluationMetricsChart({
  items,
  split,
}: {
  items: MethodSummaryItem[]
  split: EvaluationSplit
}) {
  const [focus, setFocus] = useState<ChartFocus>('primary')
  const [metricMode, setMetricMode] = useState<ChartMetric>('accuracy')

  if (items.length === 0) return null

  const primaryItems = items.filter((item) => item.config === 'tuned' || item.config === 'baseline')
  const visibleItems = focus === 'primary' && primaryItems.length > 0 ? primaryItems : items
  const hasMultipleConfigs = primaryItems.length > 0 && primaryItems.length < items.length
  const bestMrrValue = Math.max(...items.map((item) => item.mrr_at_10))

  const chartData = visibleItems.map((item) => ({
    name: formatMethodLabel(item.method, item.config),
    mrr_at_10: item.mrr_at_10,
    mean_p5: item.mean_p5,
    mean_r10: item.mean_r10,
    median_latency_ms: item.median_latency_ms,
  }))

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-1">
          <CardTitle>
            Perbandingan metrik metode · Split {split === 'test' ? 'Test' : 'Tuning'}
          </CardTitle>
          <CardDescription>
            Grafik dan tabel alternatif dari data nyata pada split {split} (tuning dan test tetap
            dipisahkan).
          </CardDescription>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {hasMultipleConfigs && (
            <div
              role="group"
              aria-label="Fokus konfigurasi grafik"
              className="inline-flex rounded-md border bg-background p-0.5"
            >
              <Button
                type="button"
                size="sm"
                variant={focus === 'primary' ? 'default' : 'ghost'}
                onClick={() => setFocus('primary')}
              >
                Tuned vs Baseline
              </Button>
              <Button
                type="button"
                size="sm"
                variant={focus === 'all' ? 'default' : 'ghost'}
                onClick={() => setFocus('all')}
              >
                Semua konfigurasi
              </Button>
            </div>
          )}

          <div
            role="group"
            aria-label="Pilih metrik grafik"
            className="inline-flex rounded-md border bg-background p-0.5"
          >
            <Button
              type="button"
              size="sm"
              variant={metricMode === 'accuracy' ? 'default' : 'ghost'}
              onClick={() => setMetricMode('accuracy')}
            >
              Akurasi
            </Button>
            <Button
              type="button"
              size="sm"
              variant={metricMode === 'latency' ? 'default' : 'ghost'}
              onClick={() => setMetricMode('latency')}
            >
              Latensi (ms)
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        <div
          aria-label={`Grafik perbandingan ${metricMode === 'accuracy' ? 'MRR@10, Precision@5, dan Recall@10' : 'Median latensi (ms)'} pada split ${split}`}
          className="h-80 w-full"
        >
          <ResponsiveContainer width="100%" height={320} minWidth={280}>
            <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 32 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="name"
                angle={-16}
                textAnchor="end"
                height={60}
                interval={0}
                tick={{ fontSize: 12 }}
              />
              <YAxis domain={metricMode === 'accuracy' ? [0, 1] : [0, 'auto']} />
              <Tooltip content={<EvaluationChartTooltip metricMode={metricMode} />} />
              <Legend />
              {metricMode === 'accuracy' ? (
                <>
                  <Bar dataKey="mrr_at_10" name="MRR@10" fill="#1e40af" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="mean_p5" name="Precision@5" fill="#0f766e" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="mean_r10" name="Recall@10" fill="#d97706" radius={[4, 4, 0, 0]} />
                </>
              ) : (
                <Bar
                  dataKey="median_latency_ms"
                  name="Median latensi (ms)"
                  fill="#0284c7"
                  radius={[4, 4, 0, 0]}
                />
              )}
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="space-y-2">
          <h3 className="text-sm font-medium">Tabel metrik lengkap per metode</h3>
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Metode &amp; konfigurasi</TableHead>
                  <TableHead className="text-right">Kueri</TableHead>
                  <TableHead className="text-right">MRR@10</TableHead>
                  <TableHead className="text-right">P@5</TableHead>
                  <TableHead className="text-right">R@10</TableHead>
                  <TableHead className="text-right">Hit@5</TableHead>
                  <TableHead className="text-right">Hit@10</TableHead>
                  <TableHead className="text-right">Hasil kosong</TableHead>
                  <TableHead className="text-right">Median (ms)</TableHead>
                  <TableHead className="text-right">Unjudged@10</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => {
                  const isBest = item.mrr_at_10 === bestMrrValue
                  return (
                    <TableRow key={item.label} className={isBest ? 'bg-primary/5' : undefined}>
                      <TableCell className="font-medium">
                        <span className="flex flex-wrap items-center gap-2">
                          <span>{formatMethodLabel(item.method, item.config)}</span>
                          {isBest && <Badge variant="default">Terbaik</Badge>}
                        </span>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatNumber(item.n_queries)}
                      </TableCell>
                      <TableCell className="text-right font-semibold tabular-nums">
                        {formatDecimal(item.mrr_at_10, 4)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatDecimal(item.mean_p5, 4)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatDecimal(item.mean_r10, 4)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatPercent(item.hit_at_5_rate)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatPercent(item.hit_at_10_rate)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatPercent(item.zero_result_rate)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatDecimal(item.median_latency_ms, 1)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatDecimal(item.mean_unjudged_top10, 2)}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
