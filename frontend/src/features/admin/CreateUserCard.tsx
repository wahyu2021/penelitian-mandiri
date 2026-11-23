import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { UserPlus } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { createAdminUser } from '@/lib/api/adminUsers'
import { ApiError } from '@/lib/api/session'

export function CreateUserCard({
  csrfToken,
  onSuccessFeedback,
  onClearExternalError,
}: {
  csrfToken: string
  onSuccessFeedback: (message: string) => void
  onClearExternalError: () => void
}) {
  const queryClient = useQueryClient()
  const [username, setUsername] = useState('')
  const [role, setRole] = useState<'petugas' | 'admin'>('petugas')
  const [password, setPassword] = useState('')
  const [formError, setFormError] = useState('')

  const mutation = useMutation({
    mutationFn: () => createAdminUser({ username: username.trim(), role, password }, csrfToken),
    onSuccess: (created) => {
      setUsername('')
      setRole('petugas')
      setPassword('')
      setFormError('')
      onClearExternalError()
      onSuccessFeedback(`Akun ${created.username} (${created.role}) berhasil dibuat.`)
      void queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      void queryClient.invalidateQueries({ queryKey: ['admin-activity'] })
    },
    onError: (error) => {
      onSuccessFeedback('')
      setFormError(
        error instanceof ApiError ? error.message : 'Akun baru belum dapat dibuat saat ini.',
      )
    },
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError('')
    onSuccessFeedback('')
    const trimmed = username.trim()
    if (!trimmed || /\s/.test(trimmed)) {
      setFormError('Nama pengguna wajib diisi tanpa spasi.')
      return
    }
    if (password.length < 10) {
      setFormError('Kata sandi minimal 10 karakter.')
      return
    }
    mutation.mutate()
  }

  return (
    <Card>
      <CardHeader className="border-b border-border">
        <CardTitle>
          <h2 className="flex items-center gap-2">
            <UserPlus aria-hidden="true" className="size-4" /> Tambah akun baru
          </h2>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-3 sm:items-end">
          <div className="space-y-2">
            <Label htmlFor="new-username">Nama pengguna</Label>
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
            <Label htmlFor="new-role">Peran</Label>
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
            <Label htmlFor="new-password">Kata sandi (min. 10 karakter)</Label>
            <Input
              id="new-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimal 10 karakter"
              className="h-10"
            />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 sm:col-span-3">
            {formError ? (
              <Alert variant="destructive" className="w-auto border-0 bg-transparent p-0">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            ) : (
              <p className="text-xs text-muted-foreground">
                Kata sandi disimpan sebagai hash aman dan tidak pernah dicatat di log.
              </p>
            )}
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Menyimpan…' : 'Buat akun'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
