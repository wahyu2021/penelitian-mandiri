import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, FileText, Info, MapPin, RefreshCw } from 'lucide-react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { sessionKey } from '@/features/auth/useSession'
import { getArchiveDetail, type ArchiveDetail } from '@/lib/api/archives'
import { ApiError } from '@/lib/api/session'

const rupiah = new Intl.NumberFormat('id-ID', {
  style: 'currency',
  currency: 'IDR',
  maximumFractionDigits: 0,
})
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
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  useEffect(() => {
    if (query.error instanceof ApiError && query.error.status === 401) {
      queryClient.removeQueries({ queryKey: sessionKey })
      navigate('/login', { replace: true })
    }
  }, [query.error, queryClient, navigate])

  return (
    <main className="space-y-6 py-8 sm:py-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Detail arsip</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
            {id === null ? 'Arsip tidak ditemukan' : `Arsip #${id}`}
          </h1>
          {query.data && (
            <p className="mt-2 text-sm text-muted-foreground">
              {display(query.data.opd_name)} · {query.data.year ?? 'Tahun tidak tersedia'}
            </p>
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
          <Card role="alert">
            <CardContent className="space-y-3">
              <p className="font-medium">Detail arsip belum dapat dimuat.</p>
              <p className="text-sm text-muted-foreground">
                Periksa sambungan layanan lalu coba lagi.
              </p>
              <Button variant="outline" onClick={() => void query.refetch()}>
                <RefreshCw aria-hidden="true" /> Coba lagi
              </Button>
            </CardContent>
          </Card>
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
        <Card>
          <CardHeader>
            <CardTitle>
              <h2 className="flex items-center gap-2">
                <MapPin aria-hidden="true" className="size-4" /> Lokasi fisik
              </h2>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl>
              <Fact label="Blok" value={archive.location.block} />
              <Fact label="Rak" value={archive.location.rack} />
              <Fact label="Baris" value={archive.location.row} />
              <Fact label="Nomor boks" value={archive.location.box_number} />
            </dl>
            <p className="mt-3 text-xs text-muted-foreground">
              Lokasi mengikuti data yang tersedia pada salinan arsip.
            </p>
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
                  : rupiah.format(archive.extraction.amount_rp)
              }
            />
            <Fact label="Pihak" value={archive.extraction.party_name} />
          </dl>
          {type?.confidence === 'dugaan' && (
            <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-950">
              Jenis SPM masih dugaan. Cocokkan dengan ringkasan asli.
            </p>
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
