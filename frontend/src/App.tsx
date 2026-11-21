import { Route, Routes } from 'react-router'
import { AppProviders } from '@/app/providers'
import { StatusPage } from '@/features/status/StatusPage'
import { NotFoundPage } from '@/features/status/NotFoundPage'

export default function App() {
  return (
    <AppProviders>
      <Routes>
        <Route path="/" element={<StatusPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppProviders>
  )
}
