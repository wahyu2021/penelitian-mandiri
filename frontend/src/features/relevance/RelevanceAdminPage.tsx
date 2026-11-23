import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, FileUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Skeleton } from '@/components/ui/skeleton'
import { useSession } from '@/features/auth/useSession'
import { reviewError, useReviewExpiry } from '@/features/relevance/useReviewSession'
import {
  createReview,
  getRelevanceAdmin,
  migrateReview,
  relevanceExportUrl,
  type RelevanceAdmin,
} from '@/lib/api/relevance'

function Setup({
  data,
  csrf,
  refresh,
}: {
  data: RelevanceAdmin
  csrf: string
  refresh: () => Promise<unknown>
}) {
  const [selection, setSelection] = useState('')
  const version = data.available_versions.includes(selection) ? selection : ''
  const [first, setFirst] = useState('')
  const [second, setSecond] = useState('')
  const [file, setFile] = useState<File>()
  const mutation = useMutation({
    mutationFn: (selectedFile: File) => createReview(version, first, second, selectedFile, csrf),
    onSuccess: () => {
      setFile(undefined)
      return refresh()
    },
  })
  useReviewExpiry(mutation.error)

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>Siapkan penugasan</h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {data.available_versions.length === 0 ? (
          <p className="text-muted-foreground">Belum ada versi terkunci yang siap ditugaskan.</p>
        ) : (
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault()
              if (file && version && first && second && first !== second) mutation.mutate(file)
            }}
          >
            <p>
              Pilih set uji terkunci dan unggah sampel verifikasi CSV. Pastikan akun penilai tepat
              sebelum menyimpan.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <label htmlFor="review-version" className="block font-medium">
                  Versi terkunci
                </label>
                <NativeSelect
                  id="review-version"
                  className="w-full"
                  value={version}
                  onChange={(event) => setSelection(event.target.value)}
                >
                  <NativeSelectOption value="">Pilih versi</NativeSelectOption>
                  {data.available_versions.map((name) => (
                    <NativeSelectOption value={name} key={name}>
                      {name}
                    </NativeSelectOption>
                  ))}
                </NativeSelect>
              </div>
              <div className="space-y-1">
                <label htmlFor="review-sample" className="block font-medium">
                  Sampel verifikasi CSV
                </label>
                <Input
                  key={mutation.isSuccess ? mutation.submittedAt : 'sample'}
                  id="review-sample"
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(event) => setFile(event.target.files?.[0])}
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="review-first" className="block font-medium">
                  Penilai pertama
                </label>
                <NativeSelect
                  id="review-first"
                  className="w-full"
                  value={first}
                  onChange={(event) => setFirst(event.target.value)}
                >
                  <NativeSelectOption value="">Pilih akun</NativeSelectOption>
                  {data.accounts.map((account) => (
                    <NativeSelectOption key={account.id} value={account.id}>
                      {account.username}
                    </NativeSelectOption>
                  ))}
                </NativeSelect>
              </div>
              <div className="space-y-1">
                <label htmlFor="review-second" className="block font-medium">
                  Penilai kedua (Petugas)
                </label>
                <NativeSelect
                  id="review-second"
                  className="w-full"
                  value={second}
                  onChange={(event) => setSecond(event.target.value)}
                >
                  <NativeSelectOption value="">Pilih akun</NativeSelectOption>
                  {data.accounts
                    .filter((account) => account.role === 'petugas')
                    .map((account) => (
                      <NativeSelectOption
                        key={account.id}
                        value={account.id}
                        disabled={first === String(account.id)}
                      >
                        {account.username}
                      </NativeSelectOption>
                    ))}
                </NativeSelect>
              </div>
            </div>
            <Button
              type="submit"
              className="min-h-11"
              disabled={
                !version || !file || !first || !second || first === second || mutation.isPending
              }
            >
              <FileUp aria-hidden="true" /> {mutation.isPending ? 'Menyiapkan…' : 'Buat penugasan'}
            </Button>
          </form>
        )}
        {mutation.isSuccess && (
          <p role="status">
            Penugasan dibuat. {mutation.data.pairs} pasangan unik dari {mutation.data.sample_rows}{' '}
            baris.
          </p>
        )}
        {mutation.error && (
          <p role="alert" className="text-destructive">
            {reviewError(mutation.error, 'Penugasan gagal dibuat.')}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function LegacyImport({
  version,
  slot,
  csrf,
  refresh,
}: {
  version: string
  slot: 1 | 2
  csrf: string
  refresh: () => Promise<unknown>
}) {
  const [file, setFile] = useState<File>()
  const inputId = `legacy-${version}-${slot}`
  const mutation = useMutation({
    mutationFn: (selectedFile: File) => migrateReview(version, slot, selectedFile, csrf),
    onSuccess: refresh,
  })
  useReviewExpiry(mutation.error)
  return (
    <form
      className="space-y-2"
      onSubmit={(event) => {
        event.preventDefault()
        if (file) mutation.mutate(file)
      }}
    >
      <label htmlFor={inputId} className="block text-sm">
        CSV jawaban lama · Penilai {slot}
      </label>
      <div className="flex flex-wrap items-end gap-2">
        <Input
          id={inputId}
          type="file"
          accept=".csv,text/csv"
          className="w-auto max-w-full"
          onChange={(event) => {
            mutation.reset()
            setFile(event.target.files?.[0])
          }}
        />
        <Button
          type="submit"
          variant="outline"
          className="min-h-11"
          disabled={!file || mutation.isPending}
        >
          Impor jawaban
        </Button>
      </div>
      {mutation.isSuccess && (
        <p role="status">
          {mutation.data.inserted} dimigrasikan · {mutation.data.preserved} isian web dipertahankan
          · {mutation.data.outside_rows} baris di luar sampel.
        </p>
      )}
      {mutation.error && (
        <p role="alert" className="text-destructive">
          {reviewError(mutation.error, 'Jawaban lama gagal diimpor.')}
        </p>
      )}
    </form>
  )
}

export function RelevanceAdminPage() {
  const { data: session } = useSession()
  const client = useQueryClient()
  const admin = session?.user?.role === 'admin'
  const key = ['relevance-admin', session?.user?.id] as const
  const overview = useQuery({ queryKey: key, queryFn: getRelevanceAdmin, enabled: admin })
  useReviewExpiry(overview.error)
  if (!admin || !session)
    return (
      <main className="py-8">
        <h1 className="text-xl font-semibold">403 · Akses ditolak</h1>
        <p>Kelola penilaian hanya tersedia untuk admin.</p>
      </main>
    )
  const refresh = () => client.invalidateQueries({ queryKey: key })
  return (
    <main className="space-y-6 py-7 sm:py-9">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Kelola penilaian relevansi
        </h1>
      </header>
      {overview.isPending && <Skeleton className="h-40" />}
      {overview.isError && (
        <p role="alert" className="text-sm text-destructive">
          {reviewError(overview.error, 'Daftar penugasan gagal dimuat.')}{' '}
          <Button variant="outline" onClick={() => void overview.refetch()}>
            Coba lagi
          </Button>
        </p>
      )}
      {overview.data && (
        <>
          <Setup data={overview.data} csrf={session.csrf_token} refresh={refresh} />
          {overview.data.reviews.map((review) => {
            const exportReady = review.reviewers.every((person) => person.submitted_at)
            return (
              <Card key={review.version}>
                <CardHeader>
                  <CardTitle>
                    <h2 className="break-all">{review.version}</h2>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <p>
                    {review.reviewers[0]?.total ?? 0} pasangan unik · {review.sample_rows} baris
                    pada CSV sampel
                  </p>
                  {review.reviewers.map((person) => (
                    <section key={person.slot} className="space-y-2 border-t pt-3">
                      <h3 className="font-medium">
                        Penilai {person.slot} · {person.username}
                      </h3>
                      <p>
                        {person.rated}/{person.total} dinilai ·{' '}
                        {person.submitted_at ? 'Sudah diserahkan' : 'Belum diserahkan'}
                      </p>
                      {!person.submitted_at && (
                        <LegacyImport
                          version={review.version}
                          slot={person.slot}
                          csrf={session.csrf_token}
                          refresh={refresh}
                        />
                      )}
                      {exportReady && (
                        <Button asChild variant="outline">
                          <a href={relevanceExportUrl(review.version, person.slot)}>
                            <Download aria-hidden="true" /> Unduh CSV penilai {person.slot}
                          </a>
                        </Button>
                      )}
                    </section>
                  ))}
                  {!exportReady && (
                    <p className="text-muted-foreground">
                      CSV tersedia setelah kedua akun menyerahkan jawaban.
                    </p>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </>
      )}
    </main>
  )
}
