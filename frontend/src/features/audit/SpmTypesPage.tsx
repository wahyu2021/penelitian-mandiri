import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { SpmTypeCard } from '@/features/audit/SpmTypeCard'
import { useSession } from '@/features/auth/useSession'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { getSpmTypes } from '@/lib/api/extractionAudit'

export function SpmTypesPage() {
  const session = useSession()
  const admin = session.data?.user?.role === 'admin'
  const queryClient = useQueryClient()
  const types = useQuery({ queryKey: ['spm-types'], queryFn: getSpmTypes, enabled: admin })

  useUnauthorizedRedirect([types.error])

  if (!admin) {
    return <ForbiddenCard message="Kamus SPM hanya tersedia untuk admin." />
  }

  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Validasi metadata"
        title="Kamus jenis SPM"
        description="Kode berstatus dugaan hanya boleh dikonfirmasi setelah label dan sumbernya diperiksa. Konfirmasi tercatat atas nama admin."
      />
      {types.isPending && (
        <LoadingState label="Memuat kamus SPM" rows={2} rowClassName="h-40 w-full" />
      )}
      {types.isError && (
        <ErrorStateCard
          title="Daftar kode SPM belum dapat dimuat."
          onRetry={() => void types.refetch()}
        />
      )}
      {types.data && (
        <>
          <p className="text-sm text-muted-foreground">
            {types.data.filter((item) => item.confidence === 'dugaan').length} dugaan ·{' '}
            {types.data.filter((item) => item.confidence === 'terkonfirmasi').length} terkonfirmasi
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            {types.data.map((entry) => (
              <SpmTypeCard
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
