import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { TuningBestItem } from '@/lib/api/evaluation'
import { formatNumber } from '@/lib/format'

export function EvaluationTuningCard({ items }: { items: TuningBestItem[] }) {
  if (items.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bobot optimal hasil grid search (split tuning)</CardTitle>
        <CardDescription>
          Dipilih dari kombinasi bobot pada split tuning sebelum pengujian pada split test.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Matcher</TableHead>
                <TableHead className="text-right">Ringkasan</TableHead>
                <TableHead className="text-right">No. SPM</TableHead>
                <TableHead className="text-right">Pihak</TableHead>
                <TableHead className="text-right">MRR@10 (tuning)</TableHead>
                <TableHead className="text-right">P@5 (tuning)</TableHead>
                <TableHead className="text-right">Kombinasi diuji</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.matcher}>
                  <TableCell className="font-medium">{item.matcher}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {item.summary_weight.toFixed(1).replace('.', ',')}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {item.spm_weight.toFixed(1).replace('.', ',')}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {item.party_weight.toFixed(1).replace('.', ',')}
                  </TableCell>
                  <TableCell className="text-right font-semibold tabular-nums">
                    {item.mrr_at_10.toFixed(4).replace('.', ',')}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {item.precision_at_5.toFixed(4).replace('.', ',')}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatNumber(item.grid_size)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
