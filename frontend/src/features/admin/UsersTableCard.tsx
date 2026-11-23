import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { KeyRound, ShieldCheck, Users } from 'lucide-react'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { resetAdminUserPassword, updateAdminUserStatus, type AdminUser } from '@/lib/api/adminUsers'
import { ApiError } from '@/lib/api/session'
import { formatDateTimeId } from '@/lib/format'

export function UsersTableCard({
  users,
  isPending,
  isError,
  onRetry,
  currentUserId,
  csrfToken,
  onSuccessFeedback,
  onActionError,
}: {
  users?: AdminUser[]
  isPending: boolean
  isError: boolean
  onRetry: () => void
  currentUserId?: number
  csrfToken: string
  onSuccessFeedback: (message: string) => void
  onActionError: (message: string) => void
}) {
  const queryClient = useQueryClient()
  const [resetUserId, setResetUserId] = useState<number | null>(null)
  const [resetPassword, setResetPassword] = useState('')

  const statusMutation = useMutation({
    mutationFn: ({ userId, isActive }: { userId: number; isActive: boolean }) =>
      updateAdminUserStatus(userId, isActive, csrfToken),
    onSuccess: (updated) => {
      onActionError('')
      onSuccessFeedback(
        `Akun ${updated.username} kini berstatus ${updated.is_active ? 'Aktif' : 'Nonaktif'}.`,
      )
      void queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      void queryClient.invalidateQueries({ queryKey: ['admin-activity'] })
    },
    onError: (error) => {
      onSuccessFeedback('')
      onActionError(error instanceof ApiError ? error.message : 'Status akun belum dapat diubah.')
    },
  })

  const resetMutation = useMutation({
    mutationFn: ({ userId, newPassword }: { userId: number; newPassword: string }) =>
      resetAdminUserPassword(userId, newPassword, csrfToken),
    onSuccess: (updated) => {
      setResetUserId(null)
      setResetPassword('')
      onActionError('')
      onSuccessFeedback(`Kata sandi untuk ${updated.username} telah diperbarui.`)
      void queryClient.invalidateQueries({ queryKey: ['admin-activity'] })
    },
    onError: (error) => {
      onSuccessFeedback('')
      onActionError(
        error instanceof ApiError ? error.message : 'Kata sandi belum dapat diatur ulang.',
      )
    },
  })

  function handleResetSubmit(event: FormEvent<HTMLFormElement>, user: AdminUser) {
    event.preventDefault()
    onActionError('')
    onSuccessFeedback('')
    if (resetPassword.length < 10) {
      onActionError('Kata sandi baru minimal 10 karakter.')
      return
    }
    resetMutation.mutate({ userId: user.id, newPassword: resetPassword })
  }

  return (
    <Card>
      <CardHeader className="border-b border-border">
        <CardTitle>
          <h2 className="flex items-center gap-2">
            <Users aria-hidden="true" className="size-4" /> Daftar akun lokal
          </h2>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isPending ? (
          <LoadingState label="Memuat daftar akun" rows={2} rowClassName="h-10 w-full" />
        ) : isError ? (
          <ErrorStateCard title="Daftar akun belum dapat dimuat." onRetry={onRetry} />
        ) : (
          <Table className="min-w-[38rem]">
            <TableHeader>
              <TableRow>
                <TableHead>Nama pengguna</TableHead>
                <TableHead>Peran</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Dibuat</TableHead>
                <TableHead>Aksi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users?.map((user) => {
                const isSelf = user.id === currentUserId
                const isResetting = resetUserId === user.id
                return (
                  <TableRow key={user.id} className="align-top">
                    <TableCell className="font-medium">
                      <span className="inline-flex items-center gap-2">
                        {user.username}
                        {isSelf && <Badge variant="secondary">Akun Anda</Badge>}
                      </span>
                    </TableCell>
                    <TableCell>{user.role === 'admin' ? 'Admin' : 'Petugas'}</TableCell>
                    <TableCell>
                      <Badge
                        variant={user.is_active ? 'outline' : 'secondary'}
                        className={
                          user.is_active
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                            : undefined
                        }
                      >
                        {user.is_active ? 'Aktif' : 'Nonaktif'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDateTimeId(user.created_at)}
                    </TableCell>
                    <TableCell className="space-y-2 whitespace-normal">
                      <div className="flex flex-wrap gap-2">
                        {isSelf ? (
                          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                            <ShieldCheck aria-hidden="true" className="size-3.5" /> Akun aktif Anda
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
                            onActionError('')
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
                          <Label htmlFor={`reset-pw-${user.id}`} className="sr-only">
                            Kata sandi baru untuk {user.username}
                          </Label>
                          <Input
                            id={`reset-pw-${user.id}`}
                            type="password"
                            value={resetPassword}
                            onChange={(event) => setResetPassword(event.target.value)}
                            placeholder="Sandi baru (min. 10)"
                            className="w-48"
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
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
