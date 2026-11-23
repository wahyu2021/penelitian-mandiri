import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Menu, X } from 'lucide-react'
import { Outlet, useNavigate } from 'react-router'
import { AppBrand, AppSidebar } from '@/components/shared/AppSidebar'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
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
          <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" size="icon-lg" className="size-11" aria-label="Buka menu">
                <Menu aria-hidden="true" />
              </Button>
            </SheetTrigger>
            <SheetContent
              side="left"
              showCloseButton={false}
              aria-describedby={undefined}
              className="w-72 max-w-[calc(100%-2rem)] gap-0 border-sidebar-border bg-sidebar p-0 lg:hidden"
            >
              <SheetHeader className="flex-row items-center justify-between gap-3 border-b border-sidebar-border px-4 py-3">
                <SheetTitle className="text-sm font-semibold">
                  {research ? 'Menu penelitian' : 'Menu aplikasi'}
                </SheetTitle>
                <SheetClose asChild>
                  <Button
                    variant="ghost"
                    size="icon-lg"
                    className="size-11"
                    aria-label="Tutup menu"
                  >
                    <X aria-hidden="true" />
                  </Button>
                </SheetClose>
              </SheetHeader>
              <AppSidebar {...sidebarProps} onNavigate={() => setMenuOpen(false)} />
            </SheetContent>
          </Sheet>
        </header>

        <div className="w-full max-w-[1600px] px-4 sm:px-5 lg:px-6">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
