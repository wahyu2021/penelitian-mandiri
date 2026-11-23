import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, FileText } from 'lucide-react'
import { Link, useLocation, useParams } from 'react-router'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArchiveLocationCard } from '@/features/archives/ArchiveLocationCard'
import { ArchiveMetadataCard } from '@/features/archives/ArchiveMetadataCard'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { getArchiveDetail, type ArchiveDetail } from '@/lib/api/archives'
import { ApiError } from '@/lib/api/session'

const statusLabels: Record<number, string> = { 1: 'Aktif', 2: 'Nonaktif', 3: 'Lainnya' }
const searchKeys = ['q', 'opd_id', 'year', 'status', 'method', 'limit', 'offset'] as const

function display(value: string | number | null) {
  return value === null || value === '' ? 'Tidak tersedia' : String(value)
}

function ArchiveInfoRow({ label, value }: { label: string; value: string | number | null }) {
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
        <InvalidArchiveCard text="ID arsip pada alamat tidak valid." />
      ) : query.isPending ? (
        <LoadingState label="Memuat detail arsip" rows={2} rowClassName="h-36 w-full" />
      ) : query.isError ? (
        query.error instanceof ApiError && query.error.status === 404 ? (
          <InvalidArchiveCard text="Arsip ini tidak ditemukan dalam salinan data." />
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

function InvalidArchiveCard({ text }: { text: string }) {
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
        <ArchiveLocationCard location={archive.location} />
        <Card>
          <CardHeader>
            <CardTitle>
              <h2>Data arsip</h2>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl>
              <ArchiveInfoRow
                label="Status"
                value={statusLabels[archive.status] ?? `Kode ${archive.status}`}
              />
              <ArchiveInfoRow label="OPD" value={archive.opd_name} />
              <ArchiveInfoRow label="Tahun" value={archive.year} />
              <ArchiveInfoRow label="Klasifikasi" value={archive.classification_label} />
              <ArchiveInfoRow label="Nomor berkas" value={archive.file_number} />
              <ArchiveInfoRow label="Indeks" value={archive.index_label} />
              <ArchiveInfoRow
                label="Berkas digital"
                value={archive.has_document ? 'Ada' : 'Tidak ada'}
              />
            </dl>
          </CardContent>
        </Card>
      </div>
      <ArchiveMetadataCard extraction={archive.extraction} />
    </div>
  )
}
