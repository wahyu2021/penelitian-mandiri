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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { EvaluationSplit, MethodSummaryItem } from '@/lib/api/evaluation'
import { formatNumber } from '@/lib/format'

function formatMetric(value: number): string {
  return value.toFixed(4).replace('.', ',')
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1).replace('.', ',')}%`
}

export function EvaluationMetricsChart({
  items,
  split,
}: {
  items: MethodSummaryItem[]
  split: EvaluationSplit
}) {
  if (items.length === 0) return null

  const chartData = items.map((item) => ({
    name: item.label,
    mrr_at_10: item.mrr_at_10,
    mean_p5: item.mean_p5,
    mean_r10: item.mean_r10,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Perbandingan metrik metode · Split {split === 'test' ? 'Test' : 'Tuning'}
        </CardTitle>
        <CardDescription>
          Grafik dan tabel alternatif dari data nyata pada split {split} (tuning dan test tetap
          dipisahkan).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div
          aria-label={`Grafik perbandingan MRR@10, Precision@5, dan Recall@10 pada split ${split}`}
          className="h-80 w-full"
        >
          <ResponsiveContainer width="100%" height={320} minWidth={280}>
            <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 32 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" angle={-18} textAnchor="end" height={60} interval={0} />
              <YAxis domain={[0, 1]} />
              <Tooltip />
              <Legend />
              <Bar dataKey="mrr_at_10" name="MRR@10" fill="#1e40af" radius={[4, 4, 0, 0]} />
              <Bar dataKey="mean_p5" name="Precision@5" fill="#0f766e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="mean_r10" name="Recall@10" fill="#d97706" radius={[4, 4, 0, 0]} />
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
                {items.map((item) => (
                  <TableRow key={item.label}>
                    <TableCell className="font-medium">{item.label}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatNumber(item.n_queries)}
                    </TableCell>
                    <TableCell className="text-right font-semibold tabular-nums">
                      {formatMetric(item.mrr_at_10)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMetric(item.mean_p5)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMetric(item.mean_r10)}
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
                      {item.median_latency_ms.toFixed(1).replace('.', ',')}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {item.mean_unjudged_top10.toFixed(2).replace('.', ',')}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
