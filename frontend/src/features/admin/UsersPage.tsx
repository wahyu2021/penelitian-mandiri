import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { ForbiddenCard } from '@/components/shared/ForbiddenCard'
import { PageHeader } from '@/components/shared/PageHeader'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ActivityLogCard, type ActivityFilters } from '@/features/admin/ActivityLogCard'
import { CreateUserCard } from '@/features/admin/CreateUserCard'
import { UsersTableCard } from '@/features/admin/UsersTableCard'
import { useSession } from '@/features/auth/useSession'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { listActivityLogs, listAdminUsers } from '@/lib/api/adminUsers'

export function UsersPage() {
  const session = useSession()
  const currentUser = session.data?.user ?? null
  const isAdmin = currentUser?.role === 'admin'
  const csrfToken = session.data?.csrf_token ?? ''

  const [feedback, setFeedback] = useState('')
  const [actionError, setActionError] = useState('')
  const [appliedFilters, setAppliedFilters] = useState<ActivityFilters>({})

  const usersQuery = useQuery({
    queryKey: ['admin-users'],
    queryFn: listAdminUsers,
    enabled: isAdmin,
  })

  const activityQuery = useQuery({
    queryKey: ['admin-activity', appliedFilters],
    queryFn: () => listActivityLogs({ ...appliedFilters, limit: 50 }),
    enabled: isAdmin,
  })

  useUnauthorizedRedirect([usersQuery.error, activityQuery.error])

  if (!isAdmin) {
    return (
      <ForbiddenCard message="Administrasi akun dan log aktivitas hanya tersedia untuk admin." />
    )
  }

  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Administrasi sistem"
        title="Akun & log aktivitas"
        description="Kelola akun lokal petugas dan admin serta pantau riwayat tindakan penting."
        actions={
          <Button
            variant="outline"
            onClick={() => {
              void usersQuery.refetch()
              void activityQuery.refetch()
            }}
            disabled={usersQuery.isFetching || activityQuery.isFetching}
          >
            <RefreshCw aria-hidden="true" /> Muat ulang
          </Button>
        }
      />

      {feedback && (
        <Alert role="status" className="border-emerald-200 bg-emerald-50 text-emerald-950">
          <AlertDescription className="text-emerald-950">{feedback}</AlertDescription>
        </Alert>
      )}
      {actionError && (
        <Alert variant="destructive">
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      )}

      <CreateUserCard
        csrfToken={csrfToken}
        onSuccessFeedback={setFeedback}
        onClearExternalError={() => setActionError('')}
      />

      <UsersTableCard
        users={usersQuery.data}
        isPending={usersQuery.isPending}
        isError={usersQuery.isError}
        onRetry={() => void usersQuery.refetch()}
        currentUserId={currentUser?.id}
        csrfToken={csrfToken}
        onSuccessFeedback={setFeedback}
        onActionError={setActionError}
      />

      <ActivityLogCard
        items={activityQuery.data}
        isPending={activityQuery.isPending}
        isError={activityQuery.isError}
        onRetry={() => void activityQuery.refetch()}
        appliedFilters={appliedFilters}
        onApplyFilters={setAppliedFilters}
      />
    </main>
  )
}
