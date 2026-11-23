import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatDecimal, formatMethodName } from '@/features/evaluation/formatters'
import type { EvaluationRun } from '@/lib/api/evaluation'
import { formatNumber } from '@/lib/format'

const ALL_SENTINEL = '__all__'
const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const

export interface PerQueryFilters {
  method?: string
  config?: string
  queryType?: string
  noiseType?: string
}

export function EvaluationPerQueryTable({
  run,
  filters,
  perPage,
  onFiltersChange,
  onPageChange,
  onPerPageChange,
}: {
  run: EvaluationRun
  filters: PerQueryFilters
  perPage: number
  onFiltersChange: (next: PerQueryFilters) => void
  onPageChange: (page: number) => void
  onPerPageChange: (perPage: number) => void
}) {
  const { per_query, filters: available } = run
  const startRow = per_query.total === 0 ? 0 : (per_query.page - 1) * per_query.per_page + 1
  const endRow = Math.min(per_query.page * per_query.per_page, per_query.total)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Rincian per kueri (teranonimkan)</CardTitle>
        <CardDescription>
          Menampilkan {formatNumber(per_query.total)} baris hasil pada split {run.split} tanpa teks
          mentah arsip atau kueri.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-1.5">
            <Label htmlFor="eval-filter-method">Metode</Label>
            <Select
              value={filters.method ?? ALL_SENTINEL}
              onValueChange={(value) =>
                onFiltersChange({ ...filters, method: value === ALL_SENTINEL ? undefined : value })
              }
            >
              <SelectTrigger id="eval-filter-method" aria-label="Filter metode">
                <SelectValue placeholder="Semua metode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_SENTINEL}>Semua metode</SelectItem>
                {available.methods.map((m) => (
                  <SelectItem key={m} value={m}>
                    {formatMethodName(m)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="eval-filter-config">Konfigurasi</Label>
            <Select
              value={filters.config ?? ALL_SENTINEL}
              onValueChange={(value) =>
                onFiltersChange({ ...filters, config: value === ALL_SENTINEL ? undefined : value })
              }
            >
              <SelectTrigger id="eval-filter-config" aria-label="Filter konfigurasi">
                <SelectValue placeholder="Semua konfigurasi" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_SENTINEL}>Semua konfigurasi</SelectItem>
                {available.configs.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="eval-filter-qtype">Jenis kueri</Label>
            <Select
              value={filters.queryType ?? ALL_SENTINEL}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  queryType: value === ALL_SENTINEL ? undefined : value,
                })
              }
            >
              <SelectTrigger id="eval-filter-qtype" aria-label="Filter jenis kueri">
                <SelectValue placeholder="Semua jenis" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_SENTINEL}>Semua jenis</SelectItem>
                {available.query_types.map((qt) => (
                  <SelectItem key={qt} value={qt}>
                    {qt}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="eval-filter-noise">Gangguan</Label>
            <Select
              value={filters.noiseType ?? ALL_SENTINEL}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  noiseType: value === ALL_SENTINEL ? undefined : value,
                })
              }
            >
              <SelectTrigger id="eval-filter-noise" aria-label="Filter gangguan">
                <SelectValue placeholder="Semua gangguan" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_SENTINEL}>Semua gangguan</SelectItem>
                {available.noise_types.map((nt) => (
                  <SelectItem key={nt} value={nt}>
                    {nt}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID Kueri</TableHead>
                <TableHead>Metode</TableHead>
                <TableHead>Konfigurasi</TableHead>
                <TableHead>Jenis</TableHead>
                <TableHead>Gangguan</TableHead>
                <TableHead className="text-right">Relevan</TableHead>
                <TableHead className="text-right">P@5</TableHead>
                <TableHead className="text-right">R@10</TableHead>
                <TableHead className="text-right">RR@10</TableHead>
                <TableHead className="text-right">Latensi (ms)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {per_query.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="text-center text-muted-foreground">
                    Tidak ada baris hasil untuk filter terpilih.
                  </TableCell>
                </TableRow>
              ) : (
                per_query.items.map((row) => (
                  <TableRow key={`${row.query_id}-${row.method}-${row.config}`}>
                    <TableCell className="font-mono text-xs">{row.query_id}</TableCell>
                    <TableCell>{formatMethodName(row.method)}</TableCell>
                    <TableCell>{row.config}</TableCell>
                    <TableCell>{row.query_type}</TableCell>
                    <TableCell>{row.noise_type}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatNumber(row.n_relevant)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatDecimal(row.p5, 4)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatDecimal(row.r10, 4)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatDecimal(row.rr10, 4)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatDecimal(row.latency_ms, 1)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-3 text-sm">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs text-muted-foreground tabular-nums">
              {per_query.total === 0
                ? '0 baris'
                : `Menampilkan ${formatNumber(startRow)}–${formatNumber(endRow)} dari ${formatNumber(per_query.total)} baris`}
            </span>
            <div className="flex items-center gap-2">
              <Label htmlFor="eval-per-page" className="text-xs text-muted-foreground">
                Baris per halaman
              </Label>
              <Select
                value={String(perPage)}
                onValueChange={(value) => onPerPageChange(Number(value))}
              >
                <SelectTrigger id="eval-per-page" aria-label="Baris per halaman" className="w-20">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZE_OPTIONS.map((size) => (
                    <SelectItem key={size} value={String(size)}>
                      {size}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground tabular-nums">
              Halaman {formatNumber(per_query.page)} dari {formatNumber(per_query.pages)}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={per_query.page <= 1}
              onClick={() => onPageChange(Math.max(1, per_query.page - 1))}
            >
              <ChevronLeft aria-hidden="true" /> Sebelumnya
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={per_query.page >= per_query.pages}
              onClick={() => onPageChange(Math.min(per_query.pages, per_query.page + 1))}
            >
              Berikutnya <ChevronRight aria-hidden="true" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
