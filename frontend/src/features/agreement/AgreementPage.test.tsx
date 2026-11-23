import { cleanup, render, screen } from '@testing-library/react'
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

it('menampilkan status tertunda dan final serta tautan ekspor untuk admin', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url === '/api/v1/session') return stubSession('admin')
      if (url === '/api/v1/research/agreement') {
        return Response.json({
          data: {
            generated_at: '2026-11-23T14:00:00Z',
            relevance: [
              {
                version: 'v2-lengkap',
                created_at: '2026-11-20T10:00:00Z',
                n_sample_rows: 120,
                reviewers: [
                  {
                    slot: 1,
                    user_id: 1,
                    username: 'peneliti',
                    submitted_at: '2026-11-22T10:00:00Z',
                    rated: 5,
                    total: 5,
                  },
                  {
                    slot: 2,
                    user_id: 2,
                    username: 'arsiparis',
                    submitted_at: '2026-11-22T11:00:00Z',
                    rated: 5,
                    total: 5,
                  },
                ],
                status: 'complete',
                n_total: 5,
                n_paired: 5,
                n_agreed: 4,
                percentage_agreement: 0.8,
                relevant_class_agreement: 0.8,
                cohen_kappa: 0.615,
                confusion_matrix: {
                  both_relevant: 2,
                  rater1_only_relevant: 1,
                  rater2_only_relevant: 0,
                  both_irrelevant: 2,
                },
                agreement_by_query_type: {
                  topik: { n_samples: 5, n_agreed: 4, agreement: 0.8 },
                },
                limitations: [
                  'Dihitung dari penilaian biner 0/1 pada pasangan yang dinilai kedua pihak.',
                ],
              },
              {
                version: 'v3-tertunda',
                created_at: '2026-11-23T10:00:00Z',
                n_sample_rows: 10,
                reviewers: [
                  {
                    slot: 1,
                    user_id: 1,
                    username: 'peneliti',
                    submitted_at: null,
                    rated: 3,
                    total: 10,
                  },
                  {
                    slot: 2,
                    user_id: 2,
                    username: 'arsiparis',
                    submitted_at: null,
                    rated: 0,
                    total: 10,
                  },
                ],
                status: 'pending',
                n_total: 10,
                n_paired: 0,
                n_agreed: null,
                percentage_agreement: null,
                relevant_class_agreement: null,
                cohen_kappa: null,
                confusion_matrix: null,
                agreement_by_query_type: {},
                limitations: ['Belum ada pasangan yang dinilai kedua pihak (0 dari 10 sampel).'],
              },
            ],
            audit: {
              status: 'pending',
              dataset: null,
              reviewers: [],
              selected_raters: [],
              overall: null,
              fields: [],
              limitations: [
                'Sampel audit ekstraksi belum dimuat atau belum ada penilaian tersimpan.',
              ],
            },
          },
        })
      }
      throw new Error(`Unexpected URL: ${url}`)
    }),
  )

  window.history.replaceState(null, '', '/app/research/agreement')
  render(<App />)

  expect(await screen.findByText('Relevansi · v2-lengkap')).toBeInTheDocument()
  expect(screen.getByText('Lengkap & final')).toBeInTheDocument()
  expect(screen.getAllByText('Tertunda (belum lengkap)').length).toBeGreaterThanOrEqual(2)
  expect(screen.getByText('80,0% (4/5)')).toBeInTheDocument()
  expect(screen.getByText('0,615')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Unduh laporan JSON/i })).toHaveAttribute(
    'href',
    '/api/v1/research/agreement/export',
  )
})

it('menolak akses petugas pada halaman kesepakatan', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url === '/api/v1/session') return stubSession('petugas')
      throw new Error(`Unexpected URL: ${url}`)
    }),
  )

  window.history.replaceState(null, '', '/app/research/agreement')
  render(<App />)

  expect(
    await screen.findByText('Ringkasan kesepakatan penilai hanya tersedia untuk admin.'),
  ).toBeInTheDocument()
})
