import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import App from '@/App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

function sessionResponse(role: 'admin' | 'petugas') {
  return Response.json({
    data: {
      authenticated: true,
      user: { id: role === 'admin' ? 1 : 2, username: role, role },
      csrf_token: 'csrf',
    },
  })
}

it('menampilkan ringkasan status nyata dan alur penelitian untuk admin', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url === '/api/v1/session') return sessionResponse('admin')
      if (url === '/api/v1/testsets') {
        return Response.json({
          data: [
            {
              version: 'v2',
              content_sha256: 'abc',
              locked_at: '2026-11-22T10:00:00Z',
              locked_by: 1,
              updated_at: '2026-11-22T10:00:00Z',
              n_queries: 112,
              n_tuning: 28,
              n_test: 84,
              n_base_queries: 56,
              n_tuning_base_queries: 14,
              n_test_base_queries: 42,
              sources: { sintetis: 80, arsiparis: 32 },
            },
          ],
        })
      }
      if (url === '/api/v1/research/agreement') {
        return Response.json({
          data: {
            generated_at: '2026-11-23T14:00:00Z',
            relevance: [],
            audit: {
              status: 'pending',
              dataset: null,
              reviewers: [],
              selected_raters: [],
              overall: null,
              fields: [],
              limitations: ['Belum ada data'],
            },
          },
        })
      }
      if (url === '/api/v1/spm-types') {
        return Response.json({
          data: [
            {
              code: 'UP',
              label: 'Uang Persediaan',
              confidence: 'terkonfirmasi',
              source_note: 'Dokumen resmi',
              confirmed_by: 'admin',
              confirmed_at: '2026-11-20T10:00:00Z',
              archive_count: 20,
            },
            {
              code: 'LS',
              label: 'Langsung',
              confidence: 'dugaan',
              source_note: null,
              confirmed_by: null,
              confirmed_at: null,
              archive_count: 50,
            },
          ],
        })
      }
      throw new Error(`Unexpected URL: ${url}`)
    }),
  )

  window.history.replaceState(null, '', '/app/research')
  render(<App />)

  expect(
    await screen.findByRole('heading', { name: 'Ringkasan alur penelitian' }),
  ).toBeInTheDocument()
  expect(await screen.findByText('1 versi')).toBeInTheDocument()
  expect(screen.getByText('1 terkunci siap untuk eksperimen')).toBeInTheDocument()
  expect(screen.getByText('2 kode')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Demo perbandingan 5 metode/i })).toHaveAttribute(
    'href',
    '/app/research/compare',
  )
})

it('hanya menampilkan tugas penilaian untuk petugas tanpa memanggil endpoint admin', async () => {
  const fetchSpy = vi.fn(async (url: string) => {
    if (url === '/api/v1/session') return sessionResponse('petugas')
    throw new Error(`Endpoint admin tidak boleh dipanggil: ${url}`)
  })
  vi.stubGlobal('fetch', fetchSpy)

  window.history.replaceState(null, '', '/app/research')
  render(<App />)

  expect(
    await screen.findByRole('heading', { name: 'Tugas penilaian peneliti/petugas' }),
  ).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Buka penilaian/i })).toHaveAttribute(
    'href',
    '/app/research/relevance',
  )
  expect(screen.getByRole('link', { name: /Buka audit/i })).toHaveAttribute(
    'href',
    '/app/research/extraction-audit',
  )
  expect(fetchSpy.mock.calls.every(([url]) => url === '/api/v1/session')).toBe(true)
})
