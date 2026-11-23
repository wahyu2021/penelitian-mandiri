import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import App from '@/App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

function stubSession(role: 'admin' | 'petugas') {
  return Response.json({
    data: {
      authenticated: true,
      user: {
        id: role === 'admin' ? 1 : 2,
        username: role === 'admin' ? 'peneliti' : 'arsiparis',
        role,
      },
      csrf_token: 'csrf',
    },
  })
}

it('menampilkan cakupan metadata, status dugaan SPM, filter, dan paginasi untuk admin', async () => {
  const fetchMock = vi.fn(async (url: string) => {
    if (url === '/api/v1/session') return stubSession('admin')
    if (url.startsWith('/api/v1/research/quality')) {
      return Response.json({
        data: {
          total_archives: 100,
          total_issues: 2,
          spm_confidence_summary: { dugaan: 60, terkonfirmasi: 30, tanpa_kode: 10 },
          metadata_coverage: [
            { field: 'spm_number', label: 'Nomor SPM', filled: 90, missing: 10, fill_rate: 0.9 },
            { field: 'sp2d_number', label: 'Nomor SP2D', filled: 40, missing: 60, fill_rate: 0.4 },
          ],
          issue_categories: [{ issue_type: 'orphan_opd', field_name: 'opd_id', count: 2 }],
          filters: {
            issue_types: ['orphan_opd'],
            field_names: ['opd_id'],
          },
          issues: {
            items: [
              {
                id: 11,
                archive_id: 204,
                issue_type: 'orphan_opd',
                field_name: 'opd_id',
                raw_value: '99',
                detail: 'OPD tidak ditemukan pada tabel referensi.',
                year: 2024,
                opd_name: '',
                spm_type_code: 'LS',
                spm_confidence: 'dugaan',
                summary_preview: 'Pembayaran belanja modal',
              },
            ],
            total: 1,
            page: 1,
            per_page: 25,
            pages: 1,
          },
        },
      })
    }
    throw new Error(`Unexpected URL: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)

  window.history.replaceState(null, '', '/app/research/quality')
  const user = userEvent.setup()
  render(<App />)

  expect(
    await screen.findByText('Cakupan ekstraksi metadata (5 field)', {}, { timeout: 8000 }),
  ).toBeInTheDocument()
  expect(screen.getByText('Tabel cakupan metadata per field')).toBeInTheDocument()
  expect(screen.getByText('90,0%')).toBeInTheDocument()
  expect(screen.getByText('Status kode SPM dugaan tetap dipisahkan')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Arsip #204' })).toHaveAttribute(
    'href',
    '/app/archives/204',
  )
  expect(screen.getByText('LS · dugaan')).toBeInTheDocument()

  await user.click(screen.getByRole('combobox', { name: 'Filter status kode SPM' }))
  await user.click(await screen.findByRole('option', { name: 'Dugaan' }))
  expect(fetchMock.mock.calls.some(([url]) => String(url).includes('spm_confidence=dugaan'))).toBe(
    true,
  )
}, 10000)

it('menampilkan keadaan kosong tanpa isu dan menolak petugas 403', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url === '/api/v1/session') return stubSession('admin')
      if (url.startsWith('/api/v1/research/quality')) {
        return Response.json({
          data: {
            total_archives: 0,
            total_issues: 0,
            spm_confidence_summary: { dugaan: 0, terkonfirmasi: 0, tanpa_kode: 0 },
            metadata_coverage: [
              { field: 'spm_number', label: 'Nomor SPM', filled: 0, missing: 0, fill_rate: 0 },
            ],
            issue_categories: [],
            filters: { issue_types: [], field_names: [] },
            issues: { items: [], total: 0, page: 1, per_page: 25, pages: 1 },
          },
        })
      }
      throw new Error(`Unexpected URL: ${url}`)
    }),
  )

  window.history.replaceState(null, '', '/app/research/quality')
  const app = render(<App />)
  expect(
    await screen.findByText(
      'Tidak ada masalah kualitas yang tercatat untuk filter ini.',
      {},
      { timeout: 4000 },
    ),
  ).toBeInTheDocument()
  app.unmount()

  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url === '/api/v1/session') return stubSession('petugas')
      throw new Error(`Unexpected URL: ${url}`)
    }),
  )
  window.history.replaceState(null, '', '/app/research/quality')
  render(<App />)
  expect(
    await screen.findByText('Tinjauan kualitas metadata hanya tersedia untuk admin.'),
  ).toBeInTheDocument()
})
