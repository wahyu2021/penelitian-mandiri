import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, FileUp, LockKeyhole } from 'lucide-react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Skeleton } from '@/components/ui/skeleton'
import { sessionKey, useSession } from '@/features/auth/useSession'
import { ApiError } from '@/lib/api/session'
import {
  getTestset,
  getTestsets,
  lockTestset,
  saveTestset,
  testsetExportUrl,
  type TestsetDetail,
  type TestsetSummary,
} from '@/lib/api/testsets'

const queryKey = ['testsets'] as const
const originLabels = { sintetis: 'Sintetis', arsiparis: 'Nyata (arsiparis)' } as const
const pageSize = 25

function UploadForm({
  draft,
  busy,
  onSave,
}: {
  draft?: TestsetSummary
  busy: boolean
  onSave: (file: File, draft?: TestsetSummary) => void
}) {
  const [file, setFile] = useState<File>()
  const id = draft ? 'draft-testset-file' : 'new-testset-file'
  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(event) => {
        event.preventDefault()
        if (file) onSave(file, draft)
      }}
    >
      <div className="min-w-0 flex-1 space-y-1.5">
        <label htmlFor={id} className="block text-sm font-medium">
          {draft ? 'JSON pengganti untuk versi ini' : 'Berkas JSON set uji baru'}
        </label>
        <Input
          id={id}
          type="file"
          accept=".json,application/json"
          onChange={(event) => setFile(event.target.files?.[0])}
        />
      </div>
      <Button type="submit" variant={draft ? 'outline' : 'default'} disabled={!file || busy}>
        <FileUp aria-hidden="true" /> {draft ? 'Ganti isi draf' : 'Daftarkan versi'}
      </Button>
    </form>
  )
}

function QueryTable({ queries }: { queries: TestsetDetail['queries'] }) {
  const [split, setSplit] = useState('')
  const [source, setSource] = useState('')
  const [page, setPage] = useState(0)
  const matching = queries.filter(
    (query) => (!split || query.split === split) && (!source || query.source === source),
  )
  const start = page * pageSize
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>Daftar kueri</h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-4 text-sm">
          <label className="space-y-1.5">
            <span className="block">Split</span>
            <NativeSelect
              value={split}
              onChange={(event) => {
                setSplit(event.target.value)
                setPage(0)
              }}
            >
              <NativeSelectOption value="">Semua split</NativeSelectOption>
              <NativeSelectOption value="tuning">Tuning</NativeSelectOption>
              <NativeSelectOption value="test">Test</NativeSelectOption>
            </NativeSelect>
          </label>
          <label className="space-y-1.5">
            <span className="block">Asal kueri</span>
            <NativeSelect
              value={source}
              onChange={(event) => {
                setSource(event.target.value)
                setPage(0)
              }}
            >
              <NativeSelectOption value="">Semua asal</NativeSelectOption>
              <NativeSelectOption value="sintetis">Sintetis</NativeSelectOption>
              <NativeSelectOption value="arsiparis">Nyata (arsiparis)</NativeSelectOption>
            </NativeSelect>
          </label>
        </div>
        {matching.length === 0 ? (
          <p className="text-sm text-muted-foreground">Tidak ada kueri yang cocok dengan filter.</p>
        ) : (
          <>
            <ul className="divide-y divide-border rounded-lg border">
              {matching.slice(start, start + pageSize).map((query) => (
                <li key={query.query_id} className="space-y-1 px-3 py-3">
                  <p className="text-xs text-muted-foreground">
                    {query.query_id} · {query.base_query_id} ·{' '}
                    {query.split === 'tuning' ? 'Tuning' : 'Test'}
                  </p>
                  <p className="text-sm font-medium break-words whitespace-pre-wrap">
                    {query.query_text}
                  </p>
                  <p className="text-xs break-words text-muted-foreground">
                    {originLabels[query.source]} · {query.query_type.replaceAll('_', ' ')} ·{' '}
                    {query.noise_type.replaceAll('_', ' ')}
                  </p>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <p aria-live="polite">
                {start + 1}–{Math.min(start + pageSize, matching.length)} dari {matching.length}{' '}
                kueri
              </p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page === 0}
                  onClick={() => setPage(page - 1)}
                >
                  Sebelumnya
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={start + pageSize >= matching.length}
                  onClick={() => setPage(page + 1)}
                >
                  Berikutnya
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function VersionPanel({
  data,
  busy,
  onSave,
  onLock,
}: {
  data: TestsetDetail
  busy: boolean
  onSave: (file: File, draft?: TestsetSummary) => void
  onLock: (draft: TestsetSummary) => void
}) {
  const [confirmed, setConfirmed] = useState(false)
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>
            <h2 className="break-all">
              {data.version} · {data.locked_at ? 'Terkunci' : 'Terbuka'}
            </h2>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <dl className="grid gap-3 sm:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Kueri</dt>
              <dd>
                {data.n_queries} varian dari {data.n_base_queries} kueri dasar
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Tuning</dt>
              <dd>
                {data.n_tuning} varian dari {data.n_tuning_base_queries} kueri dasar
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Test</dt>
              <dd>
                {data.n_test} varian dari {data.n_test_base_queries} kueri dasar
              </dd>
            </div>
          </dl>
          <p>
            {data.sources.sintetis} sintetis · {data.sources.arsiparis} nyata (arsiparis)
          </p>
          <p className="break-all text-xs text-muted-foreground">
            SHA-256 <code>{data.content_sha256}</code>
          </p>
          {data.locked_at ? (
            <div className="flex flex-wrap items-center gap-3 border-t pt-4">
              <Button asChild variant="outline">
                <a href={testsetExportUrl(data.version)}>
                  <Download aria-hidden="true" /> Unduh JSON
                </a>
              </Button>
              <p className="text-muted-foreground">
                Dikunci {new Date(data.locked_at).toLocaleString('id-ID')}
              </p>
            </div>
          ) : (
            <>
              <div className="border-t pt-4">
                <UploadForm draft={data} busy={busy} onSave={onSave} />
              </div>
              <div className="space-y-3 border-t pt-4">
                <label className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    className="mt-0.5 size-4 shrink-0 accent-primary"
                    checked={confirmed}
                    onChange={(event) => setConfirmed(event.target.checked)}
                  />
                  <span>
                    Saya sudah memeriksa kueri dan split. Setelah dikunci, perubahan harus memakai
                    versi baru.
                  </span>
                </label>
                <Button
                  disabled={busy || !confirmed || !data.n_tuning || !data.n_test}
                  onClick={() => onLock(data)}
                >
                  <LockKeyhole aria-hidden="true" /> Kunci versi
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
      <QueryTable queries={data.queries} />
    </>
  )
}

export function TestsetsPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === 'admin'
  const csrf = session?.csrf_token ?? ''
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [selection, setSelection] = useState('')
  const versions = useQuery({ queryKey, queryFn: getTestsets, enabled: isAdmin })
  const selected = selection || versions.data?.[0]?.version || ''
  const version = useQuery({
    queryKey: [...queryKey, selected],
    queryFn: () => getTestset(selected),
    enabled: isAdmin && Boolean(selected),
  })
  const change = useMutation({
    mutationFn: ({ draft, file }: { draft?: TestsetSummary; file?: File }) => {
      if (file) return saveTestset(file, csrf, draft)
      if (draft) return lockTestset(draft, csrf)
      throw new Error('Operasi set uji belum dipilih.')
    },
    onSuccess: async (data) => {
      setSelection(data.version)
      await queryClient.invalidateQueries({ queryKey })
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409)
        void queryClient.invalidateQueries({ queryKey })
    },
  })
  const expired = [versions.error, version.error, change.error].some(
    (error) => error instanceof ApiError && error.status === 401,
  )
  useEffect(() => {
    if (expired) {
      queryClient.removeQueries({ queryKey: sessionKey })
      navigate('/login', { replace: true })
    }
  }, [expired, navigate, queryClient])

  if (!isAdmin)
    return (
      <main className="py-8">
        <h1 className="text-xl font-semibold">403 · Akses ditolak</h1>
        <p className="mt-2 text-sm">Set uji hanya tersedia untuk admin.</p>
      </main>
    )

  const save = (file: File, draft?: TestsetSummary) => change.mutate({ file, draft })
  return (
    <main className="space-y-6 py-8 sm:py-10">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Set uji kueri</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Tinjau asal kueri dan pembagian tuning serta test sebelum mengunci versi.
        </p>
      </header>
      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Versi set uji</h2>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {versions.isPending && <Skeleton className="h-10 w-full" />}
          {versions.isError && (
            <p role="alert" className="text-sm text-destructive">
              Daftar versi gagal dimuat.{' '}
              <Button size="sm" variant="outline" onClick={() => void versions.refetch()}>
                Coba lagi
              </Button>
            </p>
          )}
          {versions.data?.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Belum ada versi. Pilih berkas JSON untuk mendaftarkan set uji.
            </p>
          )}
          {Boolean(versions.data?.length) && (
            <div className="space-y-1.5">
              <label htmlFor="testset-version" className="block text-sm font-medium">
                Pilih versi
              </label>
              <NativeSelect
                id="testset-version"
                value={selected}
                disabled={change.isPending}
                onChange={(event) => {
                  change.reset()
                  setSelection(event.target.value)
                }}
              >
                {versions.data?.map((item) => (
                  <NativeSelectOption key={item.version} value={item.version}>
                    {item.version} · {item.locked_at ? 'Terkunci' : 'Terbuka'}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </div>
          )}
          <UploadForm
            key={change.isSuccess ? change.submittedAt : 'new'}
            busy={change.isPending}
            onSave={save}
          />
          {change.isPending && (
            <p role="status" className="text-sm">
              Menyimpan versi…
            </p>
          )}
          {change.isError && (
            <p role="alert" className="text-sm text-destructive">
              {change.error instanceof ApiError ? change.error.message : 'Versi gagal disimpan.'}
            </p>
          )}
          {change.isSuccess && (
            <p role="status" className="text-sm">
              Versi {change.data.version} {change.data.locked_at ? 'dikunci.' : 'disimpan.'}
            </p>
          )}
        </CardContent>
      </Card>
      {selected && version.isPending && <Skeleton className="h-40 w-full" />}
      {version.isError && (
        <p role="alert" className="text-sm text-destructive">
          Isi versi gagal dimuat.{' '}
          <Button size="sm" variant="outline" onClick={() => void version.refetch()}>
            Coba lagi
          </Button>
        </p>
      )}
      {version.data && (
        <VersionPanel
          key={`${selected}-${version.data.content_sha256}`}
          data={version.data}
          busy={change.isPending}
          onSave={save}
          onLock={(draft) => change.mutate({ draft })}
        />
      )}
    </main>
  )
}
