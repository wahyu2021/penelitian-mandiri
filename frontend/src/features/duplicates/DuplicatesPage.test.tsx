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

it('menampilkan pasangan berdampingan dan menyimpan keputusan dengan CSRF untuk admin', async () => {
  let savedDecision: string | null = null
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    if (url === '/api/v1/session') return stubSession('admin')
    if (url.startsWith('/api/v1/research/duplicates/101/102') && options?.method === 'PUT') {
      expect(new Headers(options.headers).get('X-CSRF-Token')).toBe('csrf')
      const body = JSON.parse(String(options.body)) as { decision: 'duplikat'; notes: string }
      savedDecision = body.decision
      return Response.json({
        data: {
          archive_a_id: 101,
          archive_b_id: 102,
          decision: body.decision,
          notes: body.notes,
          reviewed_by: 'peneliti',
          reviewed_at: '2026-11-24T01:00:00Z',
        },
      })
    }
    if (url.startsWith('/api/v1/research/duplicates')) {
      return Response.json({
        data: {
          summary: {
            total_candidates: 1,
            unreviewed: savedDecision ? 0 : 1,
            duplikat: savedDecision === 'duplikat' ? 1 : 0,
            bukan_duplikat: 0,
            perlu_cek: 0,
          },
          items: [
            {
              archive_a_id: 101,
              archive_b_id: 102,
              reason: 'same_spm',
              similarity: 1.0,
              decision: savedDecision,
              notes: '',
              reviewed_by: savedDecision ? 'peneliti' : null,
              reviewed_at: savedDecision ? '2026-11-24T01:00:00Z' : null,
              history: [],
              archive_a: {
                id: 101,
                year: 2024,
                opd_name: 'Dinas PU',
                summary_raw: 'Ringkasan arsip A',
                spm_number: '001/UP',
                sp2d_number: null,
                document_date: '2024-05-01',
                amount_rp: 1500000,
                party_name: 'CV Maju',
                location: { block: 'A', rack: '1', row: '2', box: 'B3' },
              },
              archive_b: {
                id: 102,
                year: 2024,
                opd_name: 'Dinas PU',
                summary_raw: 'Ringkasan arsip B',
                spm_number: '001/UP',
                sp2d_number: null,
                document_date: '2024-05-02',
                amount_rp: 1500000,
                party_name: 'CV Maju',
                location: { block: 'A', rack: '1', row: '3', box: 'B4' },
              },
            },
          ],
          total: 1,
          page: 1,
          per_page: 20,
          pages: 1,
        },
      })
    }
    throw new Error(`Unexpected URL: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)

  window.history.replaceState(null, '', '/app/research/duplicates')
  const user = userEvent.setup()
  render(<App />)

  expect(await screen.findByText('Pasangan #101 & #102', {}, { timeout: 8000 })).toBeInTheDocument()
  expect(screen.getByText('Ringkasan arsip A')).toBeInTheDocument()
  expect(screen.getByText('Ringkasan arsip B')).toBeInTheDocument()
  expect(screen.getByText('Hanya peninjauan manual tanpa penghapusan otomatis')).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Duplikat' }))
  await user.type(
    screen.getByLabelText('Catatan penilai (opsional)'),
    'Terindikasi ganda saat impor',
  )
  await user.click(screen.getByRole('button', { name: 'Simpan keputusan' }))

  expect(
    await screen.findByText('Keputusan tersimpan tanpa mengubah arsip sumber.'),
  ).toBeInTheDocument()
})

it('menampilkan keadaan kosong dan menolak petugas 403', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url === '/api/v1/session') return stubSession('admin')
      if (url.startsWith('/api/v1/research/duplicates')) {
        return Response.json({
          data: {
            summary: {
              total_candidates: 0,
              unreviewed: 0,
              duplikat: 0,
              bukan_duplikat: 0,
              perlu_cek: 0,
            },
            items: [],
            total: 0,
            page: 1,
            per_page: 20,
            pages: 1,
          },
        })
      }
      throw new Error(`Unexpected URL: ${url}`)
    }),
  )

  window.history.replaceState(null, '', '/app/research/duplicates')
  const app = render(<App />)
  expect(
    await screen.findByText(
      'Tidak ada pasangan kandidat duplikat yang sesuai dengan filter saat ini.',
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
  window.history.replaceState(null, '', '/app/research/duplicates')
  render(<App />)
  expect(
    await screen.findByText('Tinjauan kandidat duplikat hanya tersedia untuk admin.'),
  ).toBeInTheDocument()
})
