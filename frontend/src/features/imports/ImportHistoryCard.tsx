import { DatabaseBackup } from 'lucide-react'
import { EmptyState } from '@/components/shared/EmptyState'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { ImportOverview } from '@/lib/api/imports'
import { formatNumber } from '@/lib/format'

export function ImportHistoryCard({ history }: { history: ImportOverview['history'] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2 className="flex items-center gap-2">
            <DatabaseBackup aria-hidden="true" className="size-4" /> Riwayat impor
          </h2>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {history.length === 0 ? (
          <EmptyState message="Belum ada impor." />
        ) : (
          <Table className="min-w-[600px]">
            <TableCaption className="sr-only">Riwayat 20 batch impor terakhir</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Waktu</TableHead>
                <TableHead scope="col">Berkas</TableHead>
                <TableHead scope="col">Arsip</TableHead>
                <TableHead scope="col">Status</TableHead>
                <TableHead scope="col">Pengimpor</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {history.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="tabular-nums">{row.imported_at}</TableCell>
                  <TableCell className="whitespace-normal break-all">
                    {row.source_filename}
                  </TableCell>
                  <TableCell className="tabular-nums">{formatNumber(row.clean_count)}</TableCell>
                  <TableCell>
                    <Badge variant={row.status === 'completed' ? 'outline' : 'secondary'}>
                      {row.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{row.imported_by}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
