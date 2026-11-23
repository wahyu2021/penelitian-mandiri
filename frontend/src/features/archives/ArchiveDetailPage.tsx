import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, FileText, Info, MapPin } from 'lucide-react'
import { Link, useLocation, useParams } from 'react-router'
import { ErrorStateCard } from '@/components/shared/PageLayout'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { getArchiveDetail, type ArchiveDetail } from '@/lib/api/archives'
import { ApiError } from '@/lib/api/session'
import { formatCurrencyIdr } from '@/lib/format'

const statusLabels: Record<number, string> = { 1: 'Aktif', 2: 'Nonaktif', 3: 'Lainnya' }
const searchKeys = ['q', 'opd_id', 'year', 'status', 'method', 'limit', 'offset'] as const

function display(value: string | number | null) {
  return value === null || value === '' ? 'Tidak tersedia' : String(value)
}

function Fact({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="grid gap-1 border-t border-border py-3 first:border-t-0 sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-4">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words text-sm font-medium">{display(value)}</dd>
    </div>
  )
}

export function ArchiveDetailPage() {
  const { id: rawId } = useParams()
  const id =
    rawId && /^\d+$/.test(rawId) && Number.isSafeInteger(Number(rawId)) && Number(rawId) > 0
      ? Number(rawId)
      : null
  const location = useLocation()
  const sourceParams = new URLSearchParams(location.search)
  const returnParams = new URLSearchParams()
  for (const key of searchKeys) {
    const value = sourceParams.get(key)
    if (value) returnParams.set(key, value)
  }
  const backToSearch = { pathname: '/app/search', search: returnParams.toString() }
  const query = useQuery({
    queryKey: ['archive', id],
    queryFn: () => getArchiveDetail(id!),
    enabled: id !== null,
  })

  useUnauthorizedRedirect([query.error])

  return (
    <main className="space-y-6 py-8 sm:py-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Detail arsip</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
            {id === null ? 'Arsip tidak ditemukan' : `Arsip #${id}`}
          </h1>
          {query.data && (
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <span>
                {display(query.data.opd_name)} · {query.data.year ?? 'Tahun tidak tersedia'}
              </span>
              <Badge variant="outline">
                Status: {statusLabels[query.data.status] ?? `Kode ${query.data.status}`}
              </Badge>
              <Badge variant="outline">
                {query.data.has_document ? 'Ada berkas digital' : 'Tanpa berkas digital'}
              </Badge>
            </div>
          )}
        </div>
        <Button asChild variant="outline">
          <Link to={backToSearch}>
            <ArrowLeft aria-hidden="true" /> Kembali ke pencarian
          </Link>
        </Button>
      </div>

      {id === null ? (
        <Message text="ID arsip pada alamat tidak valid." />
      ) : query.isPending ? (
        <div role="status" aria-label="Memuat detail arsip" className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : query.isError ? (
        query.error instanceof ApiError && query.error.status === 404 ? (
          <Message text="Arsip ini tidak ditemukan dalam salinan data." />
        ) : (
          <ErrorStateCard
            title="Detail arsip belum dapat dimuat."
            description="Periksa sambungan layanan lalu coba lagi."
            onRetry={() => void query.refetch()}
          />
        )
      ) : (
        <ArchiveContent archive={query.data} />
      )}
    </main>
  )
}

function Message({ text }: { text: string }) {
  return (
    <Card>
      <CardContent>
        <p role="alert" className="text-sm">
          {text}
        </p>
      </CardContent>
    </Card>
  )
}

function LocationCell({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-lg border border-border bg-stone-50/70 px-3 py-2.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-words text-sm font-semibold">{display(value)}</dd>
    </div>
  )
}

function ArchiveContent({ archive }: { archive: ArchiveDetail }) {
  const type = archive.extraction.spm_type
  return (
    <div className="grid items-start gap-4 lg:grid-cols-2">
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>
              <h2 className="flex items-center gap-2">
                <FileText aria-hidden="true" className="size-4" /> Ringkasan asli
              </h2>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap break-words text-sm leading-7">
              {archive.summary_raw || 'Ringkasan tidak tersedia'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>
              <h2 className="flex items-center gap-2">
                <MapPin aria-hidden="true" className="size-4" /> Lokasi fisik
              </h2>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <LocationCell label="Blok" value={archive.location.block} />
              <LocationCell label="Rak" value={archive.location.rack} />
              <LocationCell label="Baris" value={archive.location.row} />
              <LocationCell label="Nomor boks" value={archive.location.box_number} />
            </dl>
            <p className="mt-3 text-xs text-muted-foreground">
              Lokasi mengikuti data yang tersedia pada salinan arsip.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>
              <h2>Data arsip</h2>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl>
              <Fact
                label="Status"
                value={statusLabels[archive.status] ?? `Kode ${archive.status}`}
              />
              <Fact label="OPD" value={archive.opd_name} />
              <Fact label="Tahun" value={archive.year} />
              <Fact label="Klasifikasi" value={archive.classification_label} />
              <Fact label="Nomor berkas" value={archive.file_number} />
              <Fact label="Indeks" value={archive.index_label} />
              <Fact label="Berkas digital" value={archive.has_document ? 'Ada' : 'Tidak ada'} />
            </dl>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Metadata hasil ekstraksi</h2>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <dl>
            <Fact label="Nomor SPM" value={archive.extraction.spm_number} />
            <Fact
              label="Jenis SPM"
              value={type ? `${type.code}${type.label ? ` · ${type.label}` : ''}` : null}
            />
            <Fact label="Status jenis SPM" value={type?.confidence ?? null} />
            <Fact label="Nomor SP2D" value={archive.extraction.sp2d_number} />
            <Fact label="Tanggal dokumen" value={archive.extraction.document_date} />
            <Fact
              label="Nominal"
              value={
                archive.extraction.amount_rp === null
                  ? null
                  : formatCurrencyIdr(archive.extraction.amount_rp)
              }
            />
            <Fact label="Pihak" value={archive.extraction.party_name} />
          </dl>
          {type?.confidence === 'dugaan' && (
            <Alert role="note" className="mt-3 border-amber-200 bg-amber-50 text-amber-950">
              <AlertDescription className="text-amber-950">
                Jenis SPM masih dugaan. Cocokkan dengan ringkasan asli.
              </AlertDescription>
            </Alert>
          )}
          <p className="mt-4 flex items-start gap-2 text-xs leading-5 text-muted-foreground">
            <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            Nilai ini dibuat oleh ekstraktor. Bandingkan dengan ringkasan asli sebelum dipakai
            sebagai bukti.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
