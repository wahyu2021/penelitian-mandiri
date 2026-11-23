import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Archive, ArrowRight } from 'lucide-react'
import { Navigate, useNavigate } from 'react-router'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { sessionKey, useSession } from '@/features/auth/useSession'
import { ApiError, login } from '@/lib/api/session'

export function LoginPage() {
  const session = useSession()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const mutation = useMutation({
    mutationFn: () => login(username, password, session.data!.csrf_token),
    onSuccess: (data) => {
      queryClient.setQueryData(sessionKey, data)
      navigate('/app', { replace: true })
    },
  })

  if (session.isPending)
    return (
      <main role="status" className="grid min-h-svh place-items-center">
        Memuat sesi…
      </main>
    )
  if (session.isError)
    return (
      <main className="grid min-h-svh place-items-center px-4">
        <div role="alert" className="text-center">
          <p>Sesi belum dapat diperiksa.</p>
          <Button variant="outline" className="mt-4" onClick={() => void session.refetch()}>
            Coba lagi
          </Button>
        </div>
      </main>
    )
  if (session.data.authenticated) return <Navigate to="/app" replace />

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate()
  }

  const error =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.isError
        ? 'Gagal menghubungi layanan. Coba lagi.'
        : null

  return (
    <main className="flex min-h-svh items-center justify-center bg-stone-50 px-4 py-8 sm:px-6">
      <Card className="w-full max-w-md rounded-2xl shadow-xs" aria-labelledby="login-title">
        <CardContent className="p-6 sm:p-9">
          <div className="mb-8 flex size-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Archive aria-hidden="true" className="size-6" />
          </div>
          <p className="text-xs font-semibold tracking-widest text-muted-foreground">
            PENELITIAN MANDIRI
          </p>
          <h1 id="login-title" className="mt-2 text-2xl font-semibold tracking-tight">
            Masuk ke aplikasi arsip
          </h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Gunakan akun yang dibuat untuk salinan data penelitian.
          </p>
          <form onSubmit={submit} className="mt-8 space-y-5">
            <div className="space-y-2">
              <Label htmlFor="username">Nama pengguna</Label>
              <Input
                id="username"
                name="username"
                autoComplete="username"
                required
                maxLength={100}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="h-11"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Kata sandi</Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="h-11"
              />
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" className="h-11 w-full" disabled={mutation.isPending}>
              {mutation.isPending ? 'Memeriksa akun…' : 'Masuk'}
              {!mutation.isPending && <ArrowRight aria-hidden="true" />}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  )
}
