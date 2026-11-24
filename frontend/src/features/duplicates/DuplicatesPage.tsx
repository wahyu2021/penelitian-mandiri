import { useState } from 'react'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, CopyCheck, HelpCircle, Layers, ShieldCheck } from 'lucide-react'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useSession } from '@/features/auth/useSession'
import { DuplicatePairCard } from '@/features/duplicates/DuplicatePairCard'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { fetchDuplicateCandidates } from '@/lib/api/duplicates'
import { ApiError } from '@/lib/api/session'
import { formatNumber } from '@/lib/format'

const ALL_SENTINEL = '__all__'
const PAGE_SIZE_OPTIONS = [10, 20, 50] as const

export function DuplicatesPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === 'admin'
  const queryClient = useQueryClient()

  const [reason, setReason] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState<string | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)

  const query = useQuery({
    queryKey: ['research-duplicates', reason ?? null, status ?? null, page, perPage],
    queryFn: () => fetchDuplicateCandidates({ reason, status, page, perPage }),
    placeholderData: keepPreviousData,
    enabled: isAdmin,
  })

  useUnauthorizedRedirect([query.error])

  if (!isAdmin || !session) {
    return <ForbiddenCard message="Tinjauan kandidat duplikat hanya tersedia untuk admin." />
  }

  const errorMessage =
    query.error instanceof ApiError
      ? query.error.message
      : 'Daftar kandidat duplikat belum dapat dimuat.'

  const data = query.data

  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Validasi data"
        title="Tinjauan kandidat duplikat"
        description="Bandingkan pasangan arsip berindikasi duplikat secara berdampingan dan catat keputusan penilai."
      />

      <Alert role="note">
        <AlertTitle>Hanya peninjauan manual tanpa penghapusan otomatis</AlertTitle>
        <AlertDescription>
          Keputusan yang Anda simpan hanya dicatat pada log tinjauan duplikat. Aplikasi tidak pernah
          menghapus atau menggabungkan baris arsip sumber secara otomatis.
        </AlertDescription>
      </Alert>

      {query.isPending && (
        <LoadingState label="Memuat kandidat duplikat" rows={2} rowClassName="h-44 w-full" />
      )}

      {query.isError && (
        <ErrorStateCard title={errorMessage} onRetry={() => void query.refetch()} />
      )}

      {data && (
        <div className="space-y-6">
          <section
            aria-label="Ringkasan kandidat duplikat"
            className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
          >
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1.5">
                  <Layers aria-hidden="true" className="size-3.5 text-primary" />
                  Total pasangan kandidat
                </CardDescription>
                <CardTitle className="text-2xl tabular-nums">
                  {formatNumber(data.summary.total_candidates)}
                </CardTitle>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1.5">
                  <HelpCircle aria-hidden="true" className="size-3.5 text-primary" />
                  Belum ditinjau
                </CardDescription>
                <CardTitle className="text-2xl tabular-nums">
                  {formatNumber(data.summary.unreviewed)}
                </CardTitle>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1.5">
                  <CopyCheck aria-hidden="true" className="size-3.5 text-primary" />
                  Ditandai duplikat
                </CardDescription>
                <CardTitle className="text-2xl tabular-nums">
                  {formatNumber(data.summary.duplikat)}
                </CardTitle>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1.5">
                  <ShieldCheck aria-hidden="true" className="size-3.5 text-primary" />
                  Bukan duplikat
                </CardDescription>
                <CardTitle className="text-2xl tabular-nums">
                  {formatNumber(data.summary.bukan_duplikat)}
                </CardTitle>
              </CardHeader>
            </Card>
          </section>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="dup-filter-reason">Indikasi kemiripan</Label>
              <Select
                value={reason ?? ALL_SENTINEL}
                onValueChange={(value) => {
                  setReason(value === ALL_SENTINEL ? undefined : value)
                  setPage(1)
                }}
              >
                <SelectTrigger id="dup-filter-reason" aria-label="Filter indikasi">
                  <SelectValue placeholder="Semua indikasi" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_SENTINEL}>Semua indikasi</SelectItem>
                  <SelectItem value="same_spm">Nomor SPM sama</SelectItem>
                  <SelectItem value="same_summary">Ringkasan identik</SelectItem>
                  <SelectItem value="same_amount_opd_year">OPD, tahun, nominal sama</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="dup-filter-status">Status tinjauan</Label>
              <Select
                value={status ?? ALL_SENTINEL}
                onValueChange={(value) => {
                  setStatus(value === ALL_SENTINEL ? undefined : value)
                  setPage(1)
                }}
              >
                <SelectTrigger id="dup-filter-status" aria-label="Filter status tinjauan">
                  <SelectValue placeholder="Semua status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_SENTINEL}>Semua status</SelectItem>
                  <SelectItem value="unreviewed">Belum ditinjau</SelectItem>
                  <SelectItem value="duplikat">Duplikat</SelectItem>
                  <SelectItem value="bukan_duplikat">Bukan duplikat</SelectItem>
                  <SelectItem value="perlu_cek">Perlu cek fisik</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="dup-per-page">Pasangan per halaman</Label>
              <Select
                value={String(perPage)}
                onValueChange={(value) => {
                  setPerPage(Number(value))
                  setPage(1)
                }}
              >
                <SelectTrigger id="dup-per-page" aria-label="Pasangan per halaman">
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

          {data.items.length === 0 ? (
            <EmptyState
              asCard
              message="Tidak ada pasangan kandidat duplikat yang sesuai dengan filter saat ini."
            />
          ) : (
            <div className="space-y-4">
              {data.items.map((cand) => (
                <DuplicatePairCard
                  key={`${cand.archive_a_id}-${cand.archive_b_id}`}
                  candidate={cand}
                  csrfToken={session.csrf_token}
                  onSaved={() =>
                    void queryClient.invalidateQueries({ queryKey: ['research-duplicates'] })
                  }
                />
              ))}
            </div>
          )}

          {data.pages > 1 && (
            <div className="flex items-center justify-end gap-2">
              <span className="text-xs text-muted-foreground tabular-nums">
                Halaman {formatNumber(data.page)} dari {formatNumber(data.pages)}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={data.page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft aria-hidden="true" /> Sebelumnya
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={data.page >= data.pages}
                onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
              >
                Berikutnya <ChevronRight aria-hidden="true" />
              </Button>
            </div>
          )}
        </div>
      )}
    </main>
  )
}
