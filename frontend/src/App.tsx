import { Navigate, Route, Routes } from 'react-router'
import { AppProviders } from '@/app/providers'
import { AppShell } from '@/features/auth/AppShell'
import { ProtectedRoute, RootRedirect } from '@/features/auth/AuthRoutes'
import { LoginPage } from '@/features/auth/LoginPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { ArchiveDetailPage } from '@/features/archives/ArchiveDetailPage'
import { ComparePage } from '@/features/compare/ComparePage'
import { SearchPage } from '@/features/search/SearchPage'
import { StatusPage } from '@/features/status/StatusPage'
import { NotFoundPage } from '@/features/status/NotFoundPage'

export default function App() {
  return (
    <AppProviders>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/app" element={<AppShell />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="archives/:id" element={<ArchiveDetailPage />} />
            <Route path="compare" element={<ComparePage />} />
            <Route path="status" element={<StatusPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppProviders>
  )
}
