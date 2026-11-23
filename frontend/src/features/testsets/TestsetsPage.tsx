import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useSession } from '@/features/auth/useSession'
import { TestsetUploadForm } from '@/features/testsets/TestsetUploadForm'
import { TestsetVersionPanel } from '@/features/testsets/TestsetVersionPanel'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { ApiError } from '@/lib/api/session'
import {
  getTestset,
  getTestsets,
  lockTestset,
  saveTestset,
  type TestsetSummary,
} from '@/lib/api/testsets'

const queryKey = ['testsets'] as const

export function TestsetsPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === 'admin'
  const csrf = session?.csrf_token ?? ''
  const queryClient = useQueryClient()
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

  useUnauthorizedRedirect([versions.error, version.error, change.error])

  if (!isAdmin) {
    return <ForbiddenCard message="Set uji hanya tersedia untuk admin." />
  }

  const save = (file: File, draft?: TestsetSummary) => change.mutate({ file, draft })
  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Evaluasi"
        title="Set uji kueri"
        description="Tinjau asal kueri dan pembagian tuning serta test sebelum mengunci versi."
      />
      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Versi set uji</h2>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {versions.isPending && (
            <LoadingState label="Memuat daftar versi" rows={1} rowClassName="h-10 w-full" />
          )}
          {versions.isError && (
            <ErrorStateCard
              title="Daftar versi gagal dimuat."
              onRetry={() => void versions.refetch()}
            />
          )}
          {versions.data?.length === 0 && (
            <EmptyState message="Belum ada versi. Pilih berkas JSON untuk mendaftarkan set uji." />
          )}
          {Boolean(versions.data?.length) && (
            <div className="max-w-sm space-y-1.5">
              <Label htmlFor="testset-version">Pilih versi</Label>
              <Select
                value={selected}
                disabled={change.isPending}
                onValueChange={(nextVersion) => {
                  change.reset()
                  setSelection(nextVersion)
                }}
              >
                <SelectTrigger id="testset-version" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent position="popper">
                  {versions.data?.map((item) => (
                    <SelectItem key={item.version} value={item.version}>
                      {item.version} · {item.locked_at ? 'Terkunci' : 'Terbuka'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <TestsetUploadForm
            key={change.isSuccess ? change.submittedAt : 'new'}
            busy={change.isPending}
            onSave={save}
          />
          {change.isPending && (
            <Alert role="status">
              <AlertDescription>Menyimpan versi…</AlertDescription>
            </Alert>
          )}
          {change.isError && (
            <Alert variant="destructive">
              <AlertDescription>
                {change.error instanceof ApiError ? change.error.message : 'Versi gagal disimpan.'}
              </AlertDescription>
            </Alert>
          )}
          {change.isSuccess && (
            <Alert role="status">
              <AlertDescription>
                Versi {change.data.version} {change.data.locked_at ? 'dikunci.' : 'disimpan.'}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
      {selected && version.isPending && (
        <LoadingState label="Memuat isi set uji" rows={1} rowClassName="h-40 w-full" />
      )}
      {version.isError && (
        <ErrorStateCard title="Isi versi gagal dimuat." onRetry={() => void version.refetch()} />
      )}
      {version.data && (
        <TestsetVersionPanel
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
