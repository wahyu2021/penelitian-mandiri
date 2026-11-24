import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router'
import { AppProviders } from '@/app/providers'
import { AppShell } from '@/components/shared/AppShell'
import { LoadingState } from '@/components/shared/LoadingState'
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

const EvaluationPage = lazy(() =>
  import('@/features/evaluation/EvaluationPage').then((module) => ({
    default: module.EvaluationPage,
  })),
)
const QualityPage = lazy(() =>
  import('@/features/quality/QualityPage').then((module) => ({
    default: module.QualityPage,
  })),
)
const DuplicatesPage = lazy(() =>
  import('@/features/duplicates/DuplicatesPage').then((module) => ({
    default: module.DuplicatesPage,
  })),
)
const FormsAdminPage = lazy(() =>
  import('@/features/forms/FormsAdminPage').then((module) => ({
    default: module.FormsAdminPage,
  })),
)
const PublicFormPage = lazy(() =>
  import('@/features/forms/PublicFormPage').then((module) => ({
    default: module.PublicFormPage,
  })),
)

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
        <Route
          path="/f/:token"
          element={
            <Suspense
              fallback={
                <LoadingState label="Membuka formulir" rows={2} rowClassName="h-32 w-full" />
              }
            >
              <PublicFormPage />
            </Suspense>
          }
        />
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
            <Route
              path="evaluation"
              element={
                <Suspense
                  fallback={
                    <LoadingState
                      label="Memuat halaman evaluasi"
                      rows={2}
                      rowClassName="h-44 w-full"
                    />
                  }
                >
                  <EvaluationPage />
                </Suspense>
              }
            />
            <Route
              path="quality"
              element={
                <Suspense
                  fallback={
                    <LoadingState
                      label="Memuat kualitas metadata"
                      rows={2}
                      rowClassName="h-44 w-full"
                    />
                  }
                >
                  <QualityPage />
                </Suspense>
              }
            />
            <Route
              path="duplicates"
              element={
                <Suspense
                  fallback={
                    <LoadingState
                      label="Memuat kandidat duplikat"
                      rows={2}
                      rowClassName="h-44 w-full"
                    />
                  }
                >
                  <DuplicatesPage />
                </Suspense>
              }
            />
            <Route
              path="forms"
              element={
                <Suspense
                  fallback={
                    <LoadingState
                      label="Memuat formulir publik"
                      rows={2}
                      rowClassName="h-44 w-full"
                    />
                  }
                >
                  <FormsAdminPage />
                </Suspense>
              }
            />
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
