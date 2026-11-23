import { EmptyState } from '@/components/shared/EmptyState'
import { Alert, AlertDescription } from '@/components/ui/alert'
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
import type { CompareResults } from '@/lib/api/compare'

export function ComparisonResults({ data }: { data: CompareResults }) {
  return (
    <section aria-labelledby="comparison-title" className="space-y-4">
      <div>
        <h2 id="comparison-title" className="text-lg font-semibold">
          Hasil per metode
        </h2>
        <p className="text-sm text-muted-foreground">
          Kueri: “{data.query}” · Maksimal {data.limit} arsip per metode
        </p>
      </div>
      <Alert role="note" className="bg-muted/50">
        <AlertDescription className="text-foreground">
          {data.score_note} Bandingkan urutan dan arsip yang ditemukan, bukan nilai skor lintas
          metode.
        </AlertDescription>
      </Alert>
      <div className="grid items-start gap-4 lg:grid-cols-2">
        {data.methods.map((method) => (
          <Card key={method.name}>
            <CardHeader className="border-b border-border">
              <CardTitle>
                <h3>{method.label}</h3>
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                {method.items.length} hasil dalam daftar metode ini
              </p>
            </CardHeader>
            <CardContent>
              {method.items.length === 0 ? (
                <EmptyState message="Tidak ada arsip yang cocok untuk metode ini." />
              ) : (
                <Table className="table-fixed">
                  <TableCaption className="sr-only">Urutan hasil {method.label}</TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead scope="col" className="w-10">
                        No.
                      </TableHead>
                      <TableHead scope="col">Arsip dan ringkasan</TableHead>
                      <TableHead scope="col" className="w-20 text-right">
                        {method.name === 'like' ? 'Status' : 'Skor'}
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {method.items.map((item, index) => (
                      <TableRow key={item.id} className="align-top">
                        <TableCell className="align-top tabular-nums text-muted-foreground">
                          {index + 1}
                        </TableCell>
                        <TableCell className="min-w-0 whitespace-normal break-words align-top">
                          <span className="font-medium">#{item.id}</span>
                          <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                            {item.summary_raw || 'Ringkasan tidak tersedia'}
                          </span>
                        </TableCell>
                        <TableCell className="text-right align-top tabular-nums">
                          {method.name === 'like' ? (
                            <Badge variant="secondary">Cocok</Badge>
                          ) : (
                            item.score.toFixed(3)
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  )
}
