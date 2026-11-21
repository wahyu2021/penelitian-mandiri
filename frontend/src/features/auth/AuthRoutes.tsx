import { Navigate, Outlet } from 'react-router'
import { useSession } from '@/features/auth/useSession'

export function RootRedirect() {
  const session = useSession()
  if (session.isPending) return <LoadingSession />
  if (session.isError) return <SessionError retry={() => void session.refetch()} />
  return <Navigate to={session.data.authenticated ? '/app' : '/login'} replace />
}

export function ProtectedRoute() {
  const session = useSession()
  if (session.isPending) return <LoadingSession />
  if (session.isError) return <SessionError retry={() => void session.refetch()} />
  if (!session.data.authenticated) return <Navigate to="/login" replace />
  return <Outlet />
}

function LoadingSession() {
  return (
    <main className="grid min-h-svh place-items-center px-4" role="status">
      Memuat sesi…
    </main>
  )
}

function SessionError({ retry }: { retry: () => void }) {
  return (
    <main className="grid min-h-svh place-items-center px-4">
      <div role="alert" className="text-center">
        <p>Sesi belum dapat diperiksa.</p>
        <button type="button" className="mt-3 underline" onClick={retry}>
          Coba lagi
        </button>
      </div>
    </main>
  )
}
