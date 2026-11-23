import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { DatabaseBackup, FileInput, RefreshCw } from 'lucide-react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Skeleton } from '@/components/ui/skeleton'
import { sessionKey, useSession } from '@/features/auth/useSession'
import { getImportOverview, getImportPreview, runImport } from '@/lib/api/imports'
import { ApiError } from '@/lib/api/session'

const count = new Intl.NumberFormat('id-ID')

export function ImportPage() {
  const session = useSession()
  const isAdmin = session.data?.user?.role === 'admin'
  const [source, setSource] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
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

  useEffect(() => {
    if (
      [overview.error, preview.error, mutation.error].some(
        (error) => error instanceof ApiError && error.status === 401,
      )
    ) {
      queryClient.removeQueries({ queryKey: sessionKey })
      navigate('/login', { replace: true })
    }
  }, [overview.error, preview.error, mutation.error, queryClient, navigate])

  if (!isAdmin)
    return (
      <main className="py-8 sm:py-10">
        <Card role="alert">
          <CardContent>
            <h1 className="text-xl font-semibold">403 · Akses ditolak</h1>
            <p className="mt-2 text-sm text-muted-foreground">Impor hanya tersedia untuk admin.</p>
          </CardContent>
        </Card>
      </main>
    )

  const strictMismatch =
    overview.data?.verify_reference_counts && preview.data && !preview.data.reference_total_matches
  const canImport = Boolean(preview.data && confirmed && !strictMismatch && !mutation.isPending)

  return (
    <main className="space-y-6 py-8 sm:py-10">
      <header>
        <p className="text-sm font-medium text-muted-foreground">Pengelolaan data</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
          Impor salinan arsip
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Pilih dump SQL yang telah ditempatkan pengelola di direktori impor server.
        </p>
      </header>
      {overview.isPending ? (
        <Skeleton className="h-48 w-full" />
      ) : overview.isError ? (
        <Card role="alert">
          <CardContent className="space-y-3">
            <p>Daftar impor belum dapat dimuat.</p>
            <Button variant="outline" onClick={() => void overview.refetch()}>
              <RefreshCw aria-hidden="true" /> Coba lagi
            </Button>
          </CardContent>
        </Card>
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
                <p role="status" className="text-sm text-muted-foreground">
                  Direktori impor belum diatur. Minta pengelola mengisi PM_IMPORT_DIR.
                </p>
              ) : overview.data.sources.length === 0 ? (
                <p role="status" className="text-sm text-muted-foreground">
                  Belum ada berkas .sql yang diizinkan dalam direktori impor.
                </p>
              ) : (
                <>
                  <label htmlFor="import-source" className="block text-sm font-medium">
                    Berkas dump
                  </label>
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
                  {source &&
                    (preview.isPending ? (
                      <Skeleton className="h-32 w-full" />
                    ) : preview.isError ? (
                      <p role="alert" className="text-sm text-destructive">
                        Pratinjau gagal. Berkas mungkin rusak atau tidak dapat dibaca.
                      </p>
                    ) : preview.data ? (
                      <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-4 text-sm">
                        <h3 className="font-semibold">Pratinjau {preview.data.source}</h3>
                        <dl className="grid gap-3 sm:grid-cols-3">
                          <div>
                            <dt className="text-muted-foreground">Arsip</dt>
                            <dd>{count.format(preview.data.counts.archives)}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">OPD</dt>
                            <dd>{count.format(preview.data.counts.opds)}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Klasifikasi</dt>
                            <dd>{count.format(preview.data.counts.classifications)}</dd>
                          </div>
                        </dl>
                        <p className="break-all text-xs text-muted-foreground">
                          SHA-256: {preview.data.source_sha256}
                        </p>
                        {strictMismatch && (
                          <p role="alert" className="text-destructive">
                            Jumlah arsip tidak cocok dengan acuan{' '}
                            {count.format(preview.data.reference_archive_count)}. Impor diblokir
                            dalam mode verifikasi ketat.
                          </p>
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
                    <p role="alert" className="text-sm text-destructive">
                      {mutation.error instanceof ApiError
                        ? mutation.error.message
                        : 'Impor gagal. Coba periksa berkas dan sambungan layanan.'}
                    </p>
                  )}
                  {mutation.isSuccess && (
                    <div role="status" className="rounded-lg border border-border p-4 text-sm">
                      <p className="font-semibold">
                        Impor selesai · batch #{mutation.data.batch_id}
                      </p>
                      <p>
                        {count.format(mutation.data.clean_count)} arsip tersimpan;{' '}
                        {count.format(mutation.data.issue_count)} isu data tercatat.
                      </p>
                      <p className="mt-1 text-muted-foreground">
                        Cadangan:{' '}
                        {mutation.data.backup_filename ?? 'Tidak ada basis data sebelumnya'}
                      </p>
                    </div>
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
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[600px] text-left text-sm">
                    <caption className="sr-only">Riwayat 20 batch impor terakhir</caption>
                    <thead>
                      <tr className="border-b border-border text-muted-foreground">
                        <th scope="col" className="py-2 pr-3">
                          Waktu
                        </th>
                        <th scope="col" className="py-2 pr-3">
                          Berkas
                        </th>
                        <th scope="col" className="py-2 pr-3">
                          Arsip
                        </th>
                        <th scope="col" className="py-2 pr-3">
                          Status
                        </th>
                        <th scope="col" className="py-2">
                          Pengimpor
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.data.history.map((row) => (
                        <tr key={row.id} className="border-b border-border/70">
                          <td className="py-3 pr-3 tabular-nums">{row.imported_at}</td>
                          <td className="py-3 pr-3 break-all">{row.source_filename}</td>
                          <td className="py-3 pr-3 tabular-nums">
                            {count.format(row.clean_count)}
                          </td>
                          <td className="py-3 pr-3">{row.status}</td>
                          <td className="py-3">{row.imported_by}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </main>
  )
}
