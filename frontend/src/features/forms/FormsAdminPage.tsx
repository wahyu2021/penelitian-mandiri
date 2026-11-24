import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useSession } from '@/features/auth/useSession'
import { CreateFormCard } from '@/features/forms/CreateFormCard'
import { FormLinksCard } from '@/features/forms/FormLinksCard'
import { FormResponsesCard } from '@/features/forms/FormResponsesCard'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { fetchFormDetail, fetchForms } from '@/lib/api/publicForms'
import { ApiError } from '@/lib/api/session'

export function FormsAdminPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === 'admin'
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const listQuery = useQuery({
    queryKey: ['research-forms'],
    queryFn: fetchForms,
    enabled: isAdmin,
  })

  const activeFormId = selectedId ?? listQuery.data?.[0]?.id ?? null

  const detailQuery = useQuery({
    queryKey: ['research-form-detail', activeFormId],
    queryFn: () => fetchFormDetail(activeFormId!),
    enabled: isAdmin && activeFormId !== null,
  })

  useUnauthorizedRedirect([listQuery.error, detailQuery.error])

  if (!isAdmin || !session) {
    return <ForbiddenCard message="Pengelolaan formulir publik hanya tersedia untuk admin." />
  }

  const refreshAll = () => {
    void queryClient.invalidateQueries({ queryKey: ['research-forms'] })
    void queryClient.invalidateQueries({ queryKey: ['research-form-detail'] })
  }

  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Pengumpulan data"
        title="Formulir publik & kuesioner SUS"
        description="Buat template SUS atau kuesioner kustom, terbitkan tautan 1-perangkat per peserta tanpa login, dan pantau rekapnya."
      />

      <CreateFormCard
        csrfToken={session.csrf_token}
        onCreated={(newId) => {
          setSelectedId(newId)
          refreshAll()
        }}
      />

      {listQuery.isPending && (
        <LoadingState label="Memuat daftar formulir" rows={1} rowClassName="h-28 w-full" />
      )}

      {listQuery.isError && (
        <ErrorStateCard
          title={
            listQuery.error instanceof ApiError
              ? listQuery.error.message
              : 'Daftar formulir belum dapat dimuat.'
          }
          onRetry={() => void listQuery.refetch()}
        />
      )}

      {listQuery.data && listQuery.data.length === 0 && (
        <EmptyState
          asCard
          message="Belum ada formulir publik. Klik 'Buat template SUS 10 butir' di atas untuk memulai."
        />
      )}

      {listQuery.data && listQuery.data.length > 0 && activeFormId !== null && (
        <div className="space-y-6">
          <div className="max-w-md space-y-1.5">
            <Label htmlFor="active-form-select">Pilih formulir aktif</Label>
            <Select
              value={String(activeFormId)}
              onValueChange={(value) => setSelectedId(Number(value))}
            >
              <SelectTrigger id="active-form-select" aria-label="Pilih formulir aktif">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {listQuery.data.map((f) => (
                  <SelectItem key={f.id} value={String(f.id)}>
                    {f.title} ({f.total_responses}/{f.total_links} terisi)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {detailQuery.isPending && (
            <LoadingState label="Memuat detail formulir" rows={2} rowClassName="h-36 w-full" />
          )}

          {detailQuery.data && (
            <>
              <FormLinksCard
                detail={detailQuery.data}
                csrfToken={session.csrf_token}
                onChanged={refreshAll}
              />
              <FormResponsesCard detail={detailQuery.data} />
            </>
          )}
        </div>
      )}
    </main>
  )
}
