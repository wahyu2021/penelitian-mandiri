import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Archive, LogOut } from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { sessionKey, useSession } from '@/features/auth/useSession'
import { ApiError, logout } from '@/lib/api/session'

export function AppShell() {
  const { data } = useSession()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const mutation = useMutation({
    mutationFn: () => logout(data!.csrf_token),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: sessionKey })
      navigate('/login', { replace: true })
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) {
        queryClient.removeQueries({ queryKey: sessionKey })
        navigate('/login', { replace: true })
      }
    },
  })
  const user = data?.user

  return (
    <div className="min-h-svh bg-stone-50">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Archive aria-hidden="true" className="size-5" />
            </span>
            <div>
              <p className="text-sm font-semibold">Sistem Pencarian Arsip</p>
              <p className="text-xs text-muted-foreground">Salinan data penelitian</p>
            </div>
          </div>
          <div className="flex w-full items-center justify-between gap-3 sm:w-auto">
            <span className="text-sm text-muted-foreground">
              {user?.username} · {user?.role === 'admin' ? 'Admin' : 'Petugas'}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              <LogOut aria-hidden="true" /> Keluar
            </Button>
          </div>
        </div>
      </header>
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <nav aria-label="Navigasi utama" className="flex gap-6 border-b border-border py-3 text-sm">
          <NavLink
            to="/app/dashboard"
            className={({ isActive }) =>
              isActive
                ? 'font-semibold text-primary underline underline-offset-8'
                : 'text-muted-foreground hover:text-foreground'
            }
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/app/status"
            className={({ isActive }) =>
              isActive
                ? 'font-semibold text-primary underline underline-offset-8'
                : 'text-muted-foreground hover:text-foreground'
            }
          >
            Status
          </NavLink>
          <NavLink
            to="/app/search"
            className={({ isActive }) =>
              isActive
                ? 'font-semibold text-primary underline underline-offset-8'
                : 'text-muted-foreground hover:text-foreground'
            }
          >
            Pencarian
          </NavLink>
          {user?.role === 'admin' && (
            <span className="text-muted-foreground" title="Tersedia setelah modul analisis dibuat">
              Analisis · segera hadir
            </span>
          )}
        </nav>
        {mutation.isError && (
          <p role="alert" className="mt-4 text-sm text-destructive">
            Gagal keluar. Coba lagi.
          </p>
        )}
        <Outlet />
      </div>
    </div>
  )
}
