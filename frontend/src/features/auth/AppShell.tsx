import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Menu, X } from 'lucide-react'
import { Dialog } from 'radix-ui'
import { Outlet, useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { AppBrand, AppSidebar } from '@/features/auth/AppSidebar'
import { sessionKey, useSession } from '@/features/auth/useSession'
import { ApiError, logout } from '@/lib/api/session'

export function AppShell({ research = false }: { research?: boolean }) {
  const { data } = useSession()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const desktop = window.matchMedia?.('(min-width: 64rem)')
    const closeOnDesktop = (event: MediaQueryListEvent) => {
      if (event.matches) setMenuOpen(false)
    }
    desktop?.addEventListener('change', closeOnDesktop)
    return () => desktop?.removeEventListener('change', closeOnDesktop)
  }, [])

  const endSession = () => {
    queryClient.removeQueries({ queryKey: sessionKey })
    navigate('/login', { replace: true })
  }
  const mutation = useMutation({
    mutationFn: () => logout(data!.csrf_token),
    onSuccess: endSession,
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) endSession()
    },
  })
  const sidebarProps = {
    user: data?.user ?? null,
    research,
    onLogout: () => mutation.mutate(),
    loggingOut: mutation.isPending,
    logoutFailed: mutation.isError,
  }

  return (
    <div className="min-h-svh bg-stone-50 lg:grid lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-dvh flex-col self-start border-r border-sidebar-border bg-sidebar lg:flex">
        <div className="border-b border-sidebar-border px-4 py-5">
          <AppBrand research={research} />
        </div>
        <AppSidebar {...sidebarProps} />
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-border bg-card px-4 py-3 sm:px-6 lg:hidden">
          <AppBrand research={research} />
          <Dialog.Root open={menuOpen} onOpenChange={setMenuOpen}>
            <Dialog.Trigger asChild>
              <Button variant="outline" size="icon-lg" className="size-11" aria-label="Buka menu">
                <Menu aria-hidden="true" />
              </Button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="fixed inset-0 z-40 bg-foreground/35 lg:hidden" />
              <Dialog.Content
                aria-describedby={undefined}
                className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[calc(100%-2rem)] flex-col border-r border-sidebar-border bg-sidebar shadow-xl lg:hidden"
              >
                <div className="flex items-center justify-between gap-3 border-b border-sidebar-border px-4 py-3">
                  <Dialog.Title className="text-sm font-semibold">
                    {research ? 'Menu penelitian' : 'Menu aplikasi'}
                  </Dialog.Title>
                  <Dialog.Close asChild>
                    <Button
                      variant="ghost"
                      size="icon-lg"
                      className="size-11"
                      aria-label="Tutup menu"
                    >
                      <X aria-hidden="true" />
                    </Button>
                  </Dialog.Close>
                </div>
                <AppSidebar {...sidebarProps} onNavigate={() => setMenuOpen(false)} />
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </header>

        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
