import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, RefreshCw, ShieldCheck, UserPlus, Users } from 'lucide-react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Skeleton } from '@/components/ui/skeleton'
import { sessionKey, useSession } from '@/features/auth/useSession'
import {
  createAdminUser,
  listActivityLogs,
  listAdminUsers,
  resetAdminUserPassword,
  updateAdminUserStatus,
  type AdminUser,
} from '@/lib/api/adminUsers'
import { ApiError } from '@/lib/api/session'

const dateFormat = new Intl.DateTimeFormat('id-ID', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function formatDate(value: string) {
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : dateFormat.format(parsed)
}

export function UsersPage() {
  const session = useSession()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const currentUser = session.data?.user ?? null
  const isAdmin = currentUser?.role === 'admin'
  const csrfToken = session.data?.csrf_token ?? ''

  const [username, setUsername] = useState('')
  const [role, setRole] = useState<'petugas' | 'admin'>('petugas')
  const [password, setPassword] = useState('')
  const [formError, setFormError] = useState('')
  const [feedback, setFeedback] = useState('')

  const [resetUserId, setResetUserId] = useState<number | null>(null)
  const [resetPassword, setResetPassword] = useState('')
  const [actionError, setActionError] = useState('')

  const [draftAction, setDraftAction] = useState('')
  const [draftUsername, setDraftUsername] = useState('')
  const [appliedFilters, setAppliedFilters] = useState<{ action?: string; username?: string }>({})

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

  useEffect(() => {
    const errors = [usersQuery.error, activityQuery.error]
    if (errors.some((error) => error instanceof ApiError && error.status === 401)) {
      queryClient.removeQueries({ queryKey: sessionKey })
      navigate('/login', { replace: true })
    }
  }, [usersQuery.error, activityQuery.error, queryClient, navigate])

  const createMutation = useMutation({
    mutationFn: () => createAdminUser({ username: username.trim(), role, password }, csrfToken),
    onSuccess: (created) => {
      setUsername('')
      setRole('petugas')
      setPassword('')
      setFormError('')
      setActionError('')
      setFeedback(`Akun ${created.username} (${created.role}) berhasil dibuat.`)
      void queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      void queryClient.invalidateQueries({ queryKey: ['admin-activity'] })
    },
    onError: (error) => {
      setFeedback('')
      setFormError(
        error instanceof ApiError ? error.message : 'Akun baru belum dapat dibuat saat ini.',
      )
    },
  })

  const statusMutation = useMutation({
    mutationFn: ({ userId, isActive }: { userId: number; isActive: boolean }) =>
      updateAdminUserStatus(userId, isActive, csrfToken),
    onSuccess: (updated) => {
      setActionError('')
      setFeedback(
        `Akun ${updated.username} kini berstatus ${updated.is_active ? 'Aktif' : 'Nonaktif'}.`,
      )
      void queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      void queryClient.invalidateQueries({ queryKey: ['admin-activity'] })
    },
    onError: (error) => {
      setFeedback('')
      setActionError(error instanceof ApiError ? error.message : 'Status akun belum dapat diubah.')
    },
  })

  const resetMutation = useMutation({
    mutationFn: ({ userId, newPassword }: { userId: number; newPassword: string }) =>
      resetAdminUserPassword(userId, newPassword, csrfToken),
    onSuccess: (updated) => {
      setResetUserId(null)
      setResetPassword('')
      setActionError('')
      setFeedback(`Kata sandi untuk ${updated.username} telah diperbarui.`)
      void queryClient.invalidateQueries({ queryKey: ['admin-activity'] })
    },
    onError: (error) => {
      setFeedback('')
      setActionError(
        error instanceof ApiError ? error.message : 'Kata sandi belum dapat diatur ulang.',
      )
    },
  })

  if (!isAdmin) {
    return (
      <main className="py-8 sm:py-10">
        <Card role="alert">
          <CardContent>
            <h1 className="text-xl font-semibold">403 · Akses ditolak</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Administrasi akun dan log aktivitas hanya tersedia untuk admin.
            </p>
          </CardContent>
        </Card>
      </main>
    )
  }

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError('')
    setFeedback('')
    const trimmed = username.trim()
    if (!trimmed || /\s/.test(trimmed)) {
      setFormError('Nama pengguna wajib diisi tanpa spasi.')
      return
    }
    if (password.length < 10) {
      setFormError('Kata sandi minimal 10 karakter.')
      return
    }
    createMutation.mutate()
  }

  function handleResetSubmit(event: FormEvent<HTMLFormElement>, user: AdminUser) {
    event.preventDefault()
    setActionError('')
    setFeedback('')
    if (resetPassword.length < 10) {
      setActionError('Kata sandi baru minimal 10 karakter.')
      return
    }
    resetMutation.mutate({ userId: user.id, newPassword: resetPassword })
  }

  function applyActivityFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAppliedFilters({
      action: draftAction.trim() || undefined,
      username: draftUsername.trim() || undefined,
    })
  }

  return (
    <main className="space-y-6 py-8 sm:py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Administrasi sistem</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
            Akun &amp; log aktivitas
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Kelola akun lokal petugas dan admin serta pantau riwayat tindakan penting.
          </p>
        </div>
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
      </header>

      {feedback && (
        <p
          role="status"
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950"
        >
          {feedback}
        </p>
      )}
      {actionError && (
        <p
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          {actionError}
        </p>
      )}

      <Card>
        <CardHeader className="border-b border-border">
          <CardTitle>
            <h2 className="flex items-center gap-2">
              <UserPlus aria-hidden="true" className="size-4" /> Tambah akun baru
            </h2>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-3 sm:items-end">
            <div className="space-y-2">
              <label htmlFor="new-username" className="text-sm font-medium">
                Nama pengguna
              </label>
              <Input
                id="new-username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                maxLength={80}
                placeholder="mis. petugas_budi"
                className="h-10"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="new-role" className="text-sm font-medium">
                Peran
              </label>
              <NativeSelect
                id="new-role"
                value={role}
                onChange={(event) => setRole(event.target.value as 'admin' | 'petugas')}
                className="w-full"
              >
                <NativeSelectOption value="petugas">Petugas</NativeSelectOption>
                <NativeSelectOption value="admin">Admin</NativeSelectOption>
              </NativeSelect>
            </div>
            <div className="space-y-2">
              <label htmlFor="new-password" className="text-sm font-medium">
                Kata sandi (min. 10 karakter)
              </label>
              <Input
                id="new-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Minimal 10 karakter"
                className="h-10"
              />
            </div>
            <div className="sm:col-span-3 flex flex-wrap items-center justify-between gap-3">
              {formError ? (
                <p role="alert" className="text-sm text-destructive">
                  {formError}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Kata sandi disimpan sebagai hash aman dan tidak pernah dicatat di log.
                </p>
              )}
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Menyimpan…' : 'Buat akun'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-border">
          <CardTitle>
            <h2 className="flex items-center gap-2">
              <Users aria-hidden="true" className="size-4" /> Daftar akun lokal
            </h2>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {usersQuery.isPending ? (
            <div role="status" aria-label="Memuat daftar akun" className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : usersQuery.isError ? (
            <div role="alert" className="space-y-2 text-sm">
              <p className="font-medium">Daftar akun belum dapat dimuat.</p>
              <Button variant="outline" size="sm" onClick={() => void usersQuery.refetch()}>
                Coba lagi
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[38rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs text-muted-foreground">
                    <th className="py-2.5 pr-4 font-medium">Nama pengguna</th>
                    <th className="py-2.5 pr-4 font-medium">Peran</th>
                    <th className="py-2.5 pr-4 font-medium">Status</th>
                    <th className="py-2.5 pr-4 font-medium">Dibuat</th>
                    <th className="py-2.5 font-medium">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {usersQuery.data.map((user) => {
                    const isSelf = user.id === currentUser?.id
                    const isResetting = resetUserId === user.id
                    return (
                      <tr key={user.id} className="align-top">
                        <td className="py-3 pr-4 font-medium">
                          {user.username}{' '}
                          {isSelf && (
                            <span className="ml-1 rounded bg-muted px-1.5 py-0.5 text-xs font-normal text-muted-foreground">
                              Akun Anda
                            </span>
                          )}
                        </td>
                        <td className="py-3 pr-4">{user.role === 'admin' ? 'Admin' : 'Petugas'}</td>
                        <td className="py-3 pr-4">
                          <span
                            className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${
                              user.is_active
                                ? 'bg-emerald-50 text-emerald-900'
                                : 'bg-stone-200 text-stone-800'
                            }`}
                          >
                            {user.is_active ? 'Aktif' : 'Nonaktif'}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-xs text-muted-foreground">
                          {formatDate(user.created_at)}
                        </td>
                        <td className="py-3 space-y-2">
                          <div className="flex flex-wrap gap-2">
                            {isSelf ? (
                              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                                <ShieldCheck aria-hidden="true" className="size-3.5" /> Akun aktif
                                Anda
                              </span>
                            ) : (
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                disabled={statusMutation.isPending}
                                onClick={() =>
                                  statusMutation.mutate({
                                    userId: user.id,
                                    isActive: !user.is_active,
                                  })
                                }
                              >
                                {user.is_active ? 'Nonaktifkan' : 'Aktifkan'}
                              </Button>
                            )}
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setActionError('')
                                setResetPassword('')
                                setResetUserId(isResetting ? null : user.id)
                              }}
                            >
                              <KeyRound aria-hidden="true" className="size-3.5" /> Reset sandi
                            </Button>
                          </div>
                          {isResetting && (
                            <form
                              onSubmit={(event) => handleResetSubmit(event, user)}
                              className="flex flex-wrap items-center gap-2 pt-1"
                            >
                              <label htmlFor={`reset-pw-${user.id}`} className="sr-only">
                                Kata sandi baru untuk {user.username}
                              </label>
                              <Input
                                id={`reset-pw-${user.id}`}
                                type="password"
                                value={resetPassword}
                                onChange={(event) => setResetPassword(event.target.value)}
                                placeholder="Sandi baru (min. 10)"
                                className="h-9 w-48"
                              />
                              <Button type="submit" size="sm" disabled={resetMutation.isPending}>
                                Simpan sandi
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setResetUserId(null)
                                  setResetPassword('')
                                }}
                              >
                                Batal
                              </Button>
                            </form>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-border">
          <CardTitle>
            <h2>Log aktivitas</h2>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={applyActivityFilters} className="flex flex-wrap items-end gap-3">
            <div className="space-y-1.5">
              <label htmlFor="filter-action" className="text-xs font-medium">
                Filter aksi
              </label>
              <Input
                id="filter-action"
                value={draftAction}
                onChange={(event) => setDraftAction(event.target.value)}
                placeholder="mis. login, user_create"
                className="h-9 w-48"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="filter-username" className="text-xs font-medium">
                Filter pengguna
              </label>
              <Input
                id="filter-username"
                value={draftUsername}
                onChange={(event) => setDraftUsername(event.target.value)}
                placeholder="Nama pengguna"
                className="h-9 w-44"
              />
            </div>
            <Button type="submit" variant="outline" size="sm">
              Terapkan
            </Button>
            {(appliedFilters.action || appliedFilters.username) && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setDraftAction('')
                  setDraftUsername('')
                  setAppliedFilters({})
                }}
              >
                Bersihkan
              </Button>
            )}
          </form>

          {activityQuery.isPending ? (
            <div role="status" aria-label="Memuat log aktivitas" className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : activityQuery.isError ? (
            <div role="alert" className="space-y-2 text-sm">
              <p className="font-medium">Log aktivitas belum dapat dimuat.</p>
              <Button variant="outline" size="sm" onClick={() => void activityQuery.refetch()}>
                Coba lagi
              </Button>
            </div>
          ) : activityQuery.data.length === 0 ? (
            <p className="text-sm text-muted-foreground">Belum ada catatan aktivitas yang cocok.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[36rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">Waktu</th>
                    <th className="py-2 pr-4 font-medium">Pengguna</th>
                    <th className="py-2 pr-4 font-medium">Aksi</th>
                    <th className="py-2 font-medium">Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {activityQuery.data.map((entry) => (
                    <tr key={entry.id}>
                      <td className="py-2.5 pr-4 text-xs text-muted-foreground">
                        {formatDate(entry.created_at)}
                      </td>
                      <td className="py-2.5 pr-4">{entry.username ?? 'Sistem'}</td>
                      <td className="py-2.5 pr-4 font-mono text-xs">{entry.action}</td>
                      <td className="py-2.5 break-all text-xs text-muted-foreground">
                        {entry.detail || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  )
}
