import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
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
import type { MetadataQualitySummary } from '@/lib/api/quality'
import { formatNumber } from '@/lib/format'

const ALL_SENTINEL = '__all__'
const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const

export interface QualityFilters {
  issueType?: string
  fieldName?: string
  spmConfidence?: string
}

export function QualityIssuesTable({
  summary,
  filters,
  perPage,
  onFiltersChange,
  onPageChange,
  onPerPageChange,
}: {
  summary: MetadataQualitySummary
  filters: QualityFilters
  perPage: number
  onFiltersChange: (next: QualityFilters) => void
  onPageChange: (page: number) => void
  onPerPageChange: (perPage: number) => void
}) {
  const { issues, issue_categories: categories, filters: available } = summary
  const startRow = issues.total === 0 ? 0 : (issues.page - 1) * issues.per_page + 1
  const endRow = Math.min(issues.page * issues.per_page, issues.total)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Daftar masalah kualitas data</CardTitle>
        <CardDescription>
          Catatan isu impor dan inkonsistensi dari tabel <code>data_issue</code> (
          {formatNumber(summary.total_issues)} total isu).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {categories.length > 0 && (
          <div aria-label="Ringkasan kategori isu" className="flex flex-wrap gap-2">
            {categories.map((cat) => (
              <Badge key={`${cat.issue_type}-${cat.field_name}`} variant="outline">
                {cat.issue_type} ({cat.field_name}): {formatNumber(cat.count)}
              </Badge>
            ))}
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="space-y-1.5">
            <Label htmlFor="quality-filter-type">Jenis masalah</Label>
            <Select
              value={filters.issueType ?? ALL_SENTINEL}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  issueType: value === ALL_SENTINEL ? undefined : value,
                })
              }
            >
              <SelectTrigger id="quality-filter-type" aria-label="Filter jenis masalah">
                <SelectValue placeholder="Semua masalah" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_SENTINEL}>Semua masalah</SelectItem>
                {available.issue_types.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="quality-filter-field">Field</Label>
            <Select
              value={filters.fieldName ?? ALL_SENTINEL}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  fieldName: value === ALL_SENTINEL ? undefined : value,
                })
              }
            >
              <SelectTrigger id="quality-filter-field" aria-label="Filter field">
                <SelectValue placeholder="Semua field" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_SENTINEL}>Semua field</SelectItem>
                {available.field_names.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="quality-filter-spm">Status kode SPM</Label>
            <Select
              value={filters.spmConfidence ?? ALL_SENTINEL}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  spmConfidence: value === ALL_SENTINEL ? undefined : value,
                })
              }
            >
              <SelectTrigger id="quality-filter-spm" aria-label="Filter status kode SPM">
                <SelectValue placeholder="Semua status SPM" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_SENTINEL}>Semua status SPM</SelectItem>
                <SelectItem value="dugaan">Dugaan</SelectItem>
                <SelectItem value="terkonfirmasi">Terkonfirmasi</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Arsip</TableHead>
                <TableHead>Jenis masalah</TableHead>
                <TableHead>Field</TableHead>
                <TableHead>Nilai mentah</TableHead>
                <TableHead>Status SPM</TableHead>
                <TableHead>Keterangan</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {issues.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    Tidak ada masalah kualitas yang tercatat untuk filter ini.
                  </TableCell>
                </TableRow>
              ) : (
                issues.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="whitespace-nowrap">
                      <Link
                        to={`/app/archives/${item.archive_id}`}
                        className="font-medium text-primary underline"
                      >
                        Arsip #{item.archive_id}
                      </Link>
                      {item.year && (
                        <span className="block text-xs text-muted-foreground">{item.year}</span>
                      )}
                    </TableCell>
                    <TableCell className="font-medium">{item.issue_type}</TableCell>
                    <TableCell>{item.field_name}</TableCell>
                    <TableCell className="font-mono text-xs">{item.raw_value ?? '—'}</TableCell>
                    <TableCell>
                      {item.spm_type_code ? (
                        <Badge
                          variant={
                            item.spm_confidence === 'terkonfirmasi' ? 'outline' : 'secondary'
                          }
                        >
                          {item.spm_type_code} · {item.spm_confidence ?? 'dugaan'}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">Tanpa kode</span>
                      )}
                    </TableCell>
                    <TableCell className="max-w-xs text-xs text-muted-foreground">
                      {item.detail ?? item.summary_preview}
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
              {issues.total === 0
                ? '0 baris'
                : `Menampilkan ${formatNumber(startRow)}–${formatNumber(endRow)} dari ${formatNumber(issues.total)} baris`}
            </span>
            <div className="flex items-center gap-2">
              <Label htmlFor="quality-per-page" className="text-xs text-muted-foreground">
                Baris per halaman
              </Label>
              <Select
                value={String(perPage)}
                onValueChange={(value) => onPerPageChange(Number(value))}
              >
                <SelectTrigger
                  id="quality-per-page"
                  aria-label="Baris per halaman"
                  className="w-20"
                >
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
              Halaman {formatNumber(issues.page)} dari {formatNumber(issues.pages)}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={issues.page <= 1}
              onClick={() => onPageChange(Math.max(1, issues.page - 1))}
            >
              <ChevronLeft aria-hidden="true" /> Sebelumnya
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={issues.page >= issues.pages}
              onClick={() => onPageChange(Math.min(issues.pages, issues.page + 1))}
            >
              Berikutnya <ChevronRight aria-hidden="true" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
