import { Link } from 'react-router'
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
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { MetadataCoverageItem } from '@/lib/api/quality'
import { formatNumber } from '@/lib/format'

function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(1).replace('.', ',')}%`
}

export function QualityCoverageCard({
  coverage,
  totalArchives,
  suspectCount,
}: {
  coverage: MetadataCoverageItem[]
  totalArchives: number
  suspectCount: number
}) {
  const chartData = coverage.map((item) => ({
    name: item.label,
    Terisi: item.filled,
    Kosong: item.missing,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cakupan ekstraksi metadata (5 field)</CardTitle>
        <CardDescription>
          Proporsi arsip yang memiliki nilai ekstraksi terisi vs kosong dari total{' '}
          {formatNumber(totalArchives)} arsip.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {totalArchives > 0 && (
          <div aria-label="Grafik cakupan ekstraksi metadata" className="h-72 w-full">
            <ResponsiveContainer width="100%" height={288} minWidth={280}>
              <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 16 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="Terisi" stackId="a" fill="#0f766e" radius={[0, 0, 0, 0]} />
                <Bar dataKey="Kosong" stackId="a" fill="#cbd5e1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="space-y-2">
          <h3 className="text-sm font-medium">Tabel cakupan metadata per field</h3>
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Field metadata</TableHead>
                  <TableHead className="text-right">Terisi</TableHead>
                  <TableHead className="text-right">Kosong</TableHead>
                  <TableHead className="text-right">Cakupan</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {coverage.map((item) => (
                  <TableRow key={item.field}>
                    <TableCell className="font-medium">{item.label}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatNumber(item.filled)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatNumber(item.missing)}
                    </TableCell>
                    <TableCell className="text-right font-semibold tabular-nums">
                      {formatPercent(item.fill_rate)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        <Alert role="note">
          <AlertTitle>Status kode SPM dugaan tetap dipisahkan</AlertTitle>
          <AlertDescription>
            Saat ini terdapat {formatNumber(suspectCount)} arsip dengan kode jenis SPM berstatus{' '}
            <strong>dugaan</strong>. Arti kode tersebut baru dianggap resmi setelah dikonfirmasi di{' '}
            <Link to="/app/research/spm-types" className="font-medium underline">
              Kamus SPM
            </Link>
            .
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  )
}
