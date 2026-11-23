import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { DatabaseBackup, FileInput } from 'lucide-react'
import { ErrorStateCard, ForbiddenCard, PageHeader } from '@/components/shared/PageLayout'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useSession } from '@/features/auth/useSession'
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
    <main className="space-y-6 py-8 sm:py-10">
      <PageHeader
        eyebrow="Pengelolaan data"
        title="Impor salinan arsip"
        description="Pilih dump SQL yang telah ditempatkan pengelola di direktori impor server."
      />
      {overview.isPending ? (
        <Skeleton className="h-48 w-full" />
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
                    <NativeSelect
                      className="w-full max-w-md"
                      id="import-source"
                      value={source}
                      onChange={(event) => {
                        setSource(event.target.value)
                        setConfirmed(false)
                        mutation.reset()
                      }}
                    >
                      <NativeSelectOption value="">Pilih berkas</NativeSelectOption>
                      {overview.data.sources.map((item) => (
                        <NativeSelectOption key={item.name} value={item.name}>
                          {item.name}
                        </NativeSelectOption>
                      ))}
                    </NativeSelect>
                  </div>
                  {source &&
                    (preview.isPending ? (
                      <Skeleton className="h-32 w-full" />
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
                      <label className="flex items-start gap-3 text-sm">
                        <input
                          type="checkbox"
                          checked={confirmed}
                          onChange={(event) => setConfirmed(event.target.checked)}
                          className="mt-1 size-4 accent-primary"
                        />
                        <span>
                          Saya memahami bahwa data arsip pada salinan lokal akan diganti. Sistem
                          membuat cadangan SQLite sebelum impor ulang.
                        </span>
                      </label>
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
          <Card>
            <CardHeader>
              <CardTitle>
                <h2 className="flex items-center gap-2">
                  <DatabaseBackup aria-hidden="true" className="size-4" /> Riwayat impor
                </h2>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {overview.data.history.length === 0 ? (
                <p className="text-sm text-muted-foreground">Belum ada impor.</p>
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
                    {overview.data.history.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell className="tabular-nums">{row.imported_at}</TableCell>
                        <TableCell className="whitespace-normal break-all">
                          {row.source_filename}
                        </TableCell>
                        <TableCell className="tabular-nums">
                          {formatNumber(row.clean_count)}
                        </TableCell>
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
        </>
      )}
    </main>
  )
}
