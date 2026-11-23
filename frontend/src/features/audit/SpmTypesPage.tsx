import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2 } from 'lucide-react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { sessionKey, useSession } from '@/features/auth/useSession'
import { confirmSpmType, getSpmTypes, type SpmType } from '@/lib/api/extractionAudit'
import { ApiError } from '@/lib/api/session'

function SpmEntry({
  entry,
  csrfToken,
  onConfirmed,
}: {
  entry: SpmType
  csrfToken: string
  onConfirmed: () => Promise<unknown>
}) {
  const [label, setLabel] = useState(entry.label ?? '')
  const [evidence, setEvidence] = useState('')
  const mutation = useMutation({
    mutationFn: () => confirmSpmType(entry.code, label, evidence, csrfToken),
    onSuccess: onConfirmed,
  })
  const confirmed = entry.confidence === 'terkonfirmasi'
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2 className="flex flex-wrap items-center gap-2 text-base">
            <span className="break-all">{entry.code}</span>
            {confirmed && (
              <CheckCircle2 aria-label="Terkonfirmasi" className="size-4 text-emerald-700" />
            )}
          </h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-muted-foreground">
          {entry.archive_count} arsip · {confirmed ? 'Terkonfirmasi' : 'Dugaan'}
        </p>
        {confirmed ? (
          <>
            <p>Label: {entry.label}</p>
            <p>Dasar: {entry.source_note}</p>
            <p className="text-muted-foreground">
              Oleh {entry.confirmed_by} · {entry.confirmed_at}
            </p>
          </>
        ) : (
          <>
            <label className="block font-medium" htmlFor={`spm-label-${entry.code}`}>
              Label hasil konfirmasi
            </label>
            <Input
              id={`spm-label-${entry.code}`}
              value={label}
              maxLength={120}
              onChange={(event) => setLabel(event.target.value)}
            />
            <label className="block font-medium" htmlFor={`spm-evidence-${entry.code}`}>
              Sumber atau bukti konfirmasi
            </label>
            <textarea
              id={`spm-evidence-${entry.code}`}
              className="min-h-24 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              value={evidence}
              maxLength={1000}
              onChange={(event) => setEvidence(event.target.value)}
              placeholder="Tuliskan sumber yang diperiksa dan alasan label ini benar"
            />
            <Button
              size="sm"
              disabled={
                mutation.isPending || label.trim().length < 2 || evidence.trim().length < 10
              }
              onClick={() => mutation.mutate()}
            >
              Konfirmasi kode
            </Button>
            {mutation.isError && (
              <p role="alert" className="text-destructive">
                {mutation.error instanceof ApiError ? mutation.error.message : 'Konfirmasi gagal.'}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

export function SpmTypesPage() {
  const session = useSession()
  const admin = session.data?.user?.role === 'admin'
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const types = useQuery({ queryKey: ['spm-types'], queryFn: getSpmTypes, enabled: admin })
  useEffect(() => {
    if (types.error instanceof ApiError && types.error.status === 401) {
      queryClient.removeQueries({ queryKey: sessionKey })
      navigate('/login', { replace: true })
    }
  }, [types.error, navigate, queryClient])
  if (!admin)
    return (
      <main className="py-8">
        <Card role="alert">
          <CardContent>
            <h1 className="text-xl font-semibold">403 · Akses ditolak</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Kamus SPM hanya tersedia untuk admin.
            </p>
          </CardContent>
        </Card>
      </main>
    )
  return (
    <main className="space-y-6 py-8 sm:py-10">
      <header>
        <p className="text-sm font-medium text-muted-foreground">Validasi metadata</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Kamus jenis SPM</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Kode berstatus dugaan hanya boleh dikonfirmasi setelah label dan sumbernya diperiksa.
          Konfirmasi tercatat atas nama admin.
        </p>
      </header>
      {types.isPending && <Skeleton className="h-48" />}
      {types.isError && (
        <Card role="alert">
          <CardContent>Daftar kode SPM belum dapat dimuat.</CardContent>
        </Card>
      )}
      {types.data && (
        <>
          <p className="text-sm text-muted-foreground">
            {types.data.filter((item) => item.confidence === 'dugaan').length} dugaan ·{' '}
            {types.data.filter((item) => item.confidence === 'terkonfirmasi').length} terkonfirmasi
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            {types.data.map((entry) => (
              <SpmEntry
                key={entry.code}
                entry={entry}
                csrfToken={session.data!.csrf_token}
                onConfirmed={() => queryClient.invalidateQueries({ queryKey: ['spm-types'] })}
              />
            ))}
          </div>
        </>
      )}
    </main>
  )
}
