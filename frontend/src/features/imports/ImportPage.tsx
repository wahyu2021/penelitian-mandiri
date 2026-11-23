import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileInput } from 'lucide-react'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useSession } from '@/features/auth/useSession'
import { ImportHistoryCard } from '@/features/imports/ImportHistoryCard'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { getImportOverview, getImportPreview, runImport } from '@/lib/api/imports'
import { ApiError } from '@/lib/api/session'
import { formatNumber } from '@/lib/format'

export function ImportPage() {
  const session = useSession()
  const isAdmin = session.data?.user?.role === 'admin'
  const [source, setSource] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const queryClient = useQueryClient()
  const overview = useQuery({ queryKey: ['imports'], queryFn: getImportOverview, enabled: isAdmin })
  const preview = useQuery({
    queryKey: ['import-preview', source],
    queryFn: () => getImportPreview(source),
    enabled: isAdmin && Boolean(source),
  })
  const mutation = useMutation({
    mutationFn: () => runImport(source, preview.data!.source_sha256, session.data!.csrf_token),
    onSuccess: async () => {
      setConfirmed(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['imports'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['search-filters'] }),
        queryClient.invalidateQueries({ queryKey: ['search'] }),
        queryClient.invalidateQueries({ queryKey: ['search-compare'] }),
      ])
    },
  })

  useUnauthorizedRedirect([overview.error, preview.error, mutation.error])

  if (!isAdmin) {
    return <ForbiddenCard message="Impor hanya tersedia untuk admin." />
  }

  const strictMismatch =
    overview.data?.verify_reference_counts && preview.data && !preview.data.reference_total_matches
  const canImport = Boolean(preview.data && confirmed && !strictMismatch && !mutation.isPending)

  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Pengelolaan data"
        title="Impor salinan arsip"
        description="Pilih dump SQL yang telah ditempatkan pengelola di direktori impor server."
      />
      {overview.isPending ? (
        <LoadingState label="Memuat data impor" rows={1} rowClassName="h-48 w-full" />
      ) : overview.isError ? (
        <ErrorStateCard
          title="Daftar impor belum dapat dimuat."
          onRetry={() => void overview.refetch()}
        />
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>
                <h2>Pilih dan periksa dump</h2>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {!overview.data.configured ? (
                <Alert role="status">
                  <AlertDescription>
                    Direktori impor belum diatur. Minta pengelola mengisi PM_IMPORT_DIR.
                  </AlertDescription>
                </Alert>
              ) : overview.data.sources.length === 0 ? (
                <Alert role="status">
                  <AlertDescription>
                    Belum ada berkas .sql yang diizinkan dalam direktori impor.
                  </AlertDescription>
                </Alert>
              ) : (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="import-source">Berkas dump</Label>
                    <Select
                      value={source || '__none__'}
                      onValueChange={(value) => {
                        setSource(value === '__none__' ? '' : value)
                        setConfirmed(false)
                        mutation.reset()
                      }}
                    >
                      <SelectTrigger id="import-source" className="w-full max-w-md">
                        <SelectValue placeholder="Pilih berkas" />
                      </SelectTrigger>
                      <SelectContent position="popper">
                        <SelectItem value="__none__">Pilih berkas</SelectItem>
                        {overview.data.sources.map((item) => (
                          <SelectItem key={item.name} value={item.name}>
                            {item.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {source &&
                    (preview.isPending ? (
                      <LoadingState
                        label="Memuat pratinjau dump"
                        rows={1}
                        rowClassName="h-32 w-full"
                      />
                    ) : preview.isError ? (
                      <Alert variant="destructive">
                        <AlertDescription>
                          Pratinjau gagal. Berkas mungkin rusak atau tidak dapat dibaca.
                        </AlertDescription>
                      </Alert>
                    ) : preview.data ? (
                      <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-4 text-sm">
                        <h3 className="font-semibold">Pratinjau {preview.data.source}</h3>
                        <dl className="grid gap-3 sm:grid-cols-3">
                          <div>
                            <dt className="text-muted-foreground">Arsip</dt>
                            <dd>{formatNumber(preview.data.counts.archives)}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">OPD</dt>
                            <dd>{formatNumber(preview.data.counts.opds)}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Klasifikasi</dt>
                            <dd>{formatNumber(preview.data.counts.classifications)}</dd>
                          </div>
                        </dl>
                        <p className="break-all text-xs text-muted-foreground">
                          SHA-256: {preview.data.source_sha256}
                        </p>
                        {strictMismatch && (
                          <Alert variant="destructive">
                            <AlertDescription>
                              Jumlah arsip tidak cocok dengan acuan{' '}
                              {formatNumber(preview.data.reference_archive_count)}. Impor diblokir
                              dalam mode verifikasi ketat.
                            </AlertDescription>
                          </Alert>
                        )}
                      </div>
                    ) : null)}
                  {preview.data && !strictMismatch && (
                    <>
                      <div className="flex items-start gap-3">
                        <Checkbox
                          id="import-confirm"
                          checked={confirmed}
                          onCheckedChange={(value) => setConfirmed(value === true)}
                          className="mt-0.5"
                        />
                        <Label htmlFor="import-confirm" className="font-normal leading-5">
                          Saya memahami bahwa data arsip pada salinan lokal akan diganti. Sistem
                          membuat cadangan SQLite sebelum impor ulang.
                        </Label>
                      </div>
                      <Button disabled={!canImport} onClick={() => mutation.mutate()}>
                        <FileInput aria-hidden="true" />{' '}
                        {mutation.isPending ? 'Mengimpor…' : 'Impor salinan'}
                      </Button>
                    </>
                  )}
                  {mutation.isError && (
                    <Alert variant="destructive">
                      <AlertDescription>
                        {mutation.error instanceof ApiError
                          ? mutation.error.message
                          : 'Impor gagal. Coba periksa berkas dan sambungan layanan.'}
                      </AlertDescription>
                    </Alert>
                  )}
                  {mutation.isSuccess && (
                    <Alert role="status">
                      <AlertTitle>Impor selesai · batch #{mutation.data.batch_id}</AlertTitle>
                      <AlertDescription>
                        <p>
                          {formatNumber(mutation.data.clean_count)} arsip tersimpan;{' '}
                          {formatNumber(mutation.data.issue_count)} isu data tercatat.
                        </p>
                        <p>
                          Cadangan:{' '}
                          {mutation.data.backup_filename ?? 'Tidak ada basis data sebelumnya'}
                        </p>
                      </AlertDescription>
                    </Alert>
                  )}
                </>
              )}
            </CardContent>
          </Card>
          <ImportHistoryCard history={overview.data.history} />
        </>
      )}
    </main>
  )
}
