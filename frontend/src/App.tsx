import { Navigate, Route, Routes, useLocation } from 'react-router'
import { AppProviders } from '@/app/providers'
import { AppShell } from '@/components/shared/AppShell'
import { ProtectedRoute, RootRedirect } from '@/features/auth/AuthRoutes'
import { LoginPage } from '@/features/auth/LoginPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { ArchiveDetailPage } from '@/features/archives/ArchiveDetailPage'
import { ComparePage } from '@/features/compare/ComparePage'
import { ImportPage } from '@/features/imports/ImportPage'
import { UsersPage } from '@/features/admin/UsersPage'
import { ExtractionAuditPage } from '@/features/audit/ExtractionAuditPage'
import { SpmTypesPage } from '@/features/audit/SpmTypesPage'
import { TestsetsPage } from '@/features/testsets/TestsetsPage'
import { RelevancePage } from '@/features/relevance/RelevancePage'
import { RelevanceAdminPage } from '@/features/relevance/RelevanceAdminPage'
import { AgreementPage } from '@/features/agreement/AgreementPage'
import { ResearchOverviewPage } from '@/features/research/ResearchOverviewPage'
import { SearchPage } from '@/features/search/SearchPage'
import { StatusPage } from '@/features/status/StatusPage'
import { NotFoundPage } from '@/features/status/NotFoundPage'

function ResearchRedirect({ to }: { to: string }) {
  const { search } = useLocation()
  return <Navigate to={{ pathname: to, search }} replace />
}

export default function App() {
  return (
    <AppProviders>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/app/research" element={<AppShell research />}>
            <Route index element={<ResearchOverviewPage />} />
            <Route path="compare" element={<ComparePage />} />
            <Route path="extraction-audit" element={<ExtractionAuditPage />} />
            <Route path="spm-types" element={<SpmTypesPage />} />
            <Route path="testsets" element={<TestsetsPage />} />
            <Route path="relevance" element={<RelevancePage />} />
            <Route path="relevance-admin" element={<RelevanceAdminPage />} />
            <Route path="agreement" element={<AgreementPage />} />
          </Route>
          <Route path="/app" element={<AppShell />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="archives/:id" element={<ArchiveDetailPage />} />
            <Route path="compare" element={<ResearchRedirect to="/app/research/compare" />} />
            <Route path="imports" element={<ImportPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route
              path="extraction-audit"
              element={<ResearchRedirect to="/app/research/extraction-audit" />}
            />
            <Route path="spm-types" element={<ResearchRedirect to="/app/research/spm-types" />} />
            <Route path="testsets" element={<ResearchRedirect to="/app/research/testsets" />} />
            <Route path="relevance" element={<ResearchRedirect to="/app/research/relevance" />} />
            <Route
              path="relevance-admin"
              element={<ResearchRedirect to="/app/research/relevance-admin" />}
            />
            <Route path="status" element={<StatusPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppProviders>
  )
}
