import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import App from '@/App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

function stubAdminSession() {
  return Response.json({
    data: {
      authenticated: true,
      user: { id: 1, username: 'peneliti', role: 'admin' },
      csrf_token: 'csrf',
    },
  })
}

it('penilai eksternal dapat menilai relevansi lewat /f/rv_ tanpa login dan menyerahkan final', async () => {
  let decision: 0 | 1 | null = null
  let notes = ''
  let revision = 0
  let submittedAt: string | null = null

  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    if (
      url === '/api/v1/public/tasks/rv_tok1/relevance' ||
      url.startsWith('/api/v1/public/tasks/rv_tok1/relevance?')
    ) {
      return Response.json({
        data: {
          link: {
            label: 'Penilai 2 (arsiparis) · uji-v2',
            target_username: 'arsiparis',
            target_version: 'uji-v2',
            target_slot: 2,
            lock_single_device: true,
            submitted_at: submittedAt,
          },
          review: {
            index: 0,
            total: 1,
            rated: decision === null ? 0 : 1,
            submitted_at: submittedAt,
            item: {
              id: 42,
              base_query_text: 'Pembayaran listrik kantor',
              query_type: 'topik',
              summary_raw: 'SPM pembayaran tagihan listrik bulan Januari.',
              is_relevant: decision,
              ragu: false,
              notes,
              revision,
            },
          },
        },
      })
    }
    if (url === '/api/v1/public/tasks/rv_tok1/relevance/42' && options?.method === 'PUT') {
      const body = JSON.parse(String(options.body)) as {
        is_relevant: 0 | 1 | null
        ragu: boolean
        notes: string
        revision: number
      }
      decision = body.is_relevant
      notes = body.notes
      revision += 1
      return Response.json({ data: { revision, rated: 1, total: 1 } })
    }
    if (url === '/api/v1/public/tasks/rv_tok1/relevance/submit' && options?.method === 'POST') {
      submittedAt = '2026-11-24T05:00:00Z'
      return Response.json({ data: { submitted_at: submittedAt } })
    }
    throw new Error(`Unexpected URL: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)

  window.history.replaceState(null, '', '/f/rv_tok1')
  const user = userEvent.setup()
  render(<App />)

  expect(
    await screen.findByText('SPM pembayaran tagihan listrik bulan Januari.', {}, { timeout: 8000 }),
  ).toBeInTheDocument()
  expect(screen.getByText('Terkunci pada perangkat ini')).toBeInTheDocument()
  expect(screen.queryByRole('navigation', { name: 'Navigasi utama' })).not.toBeInTheDocument()
  expect(document.body.textContent).not.toContain('noise_type')

  await user.click(screen.getByRole('radio', { name: 'Relevan' }))
  await user.click(screen.getByRole('button', { name: 'Simpan jawaban' }))
  expect(await screen.findByText('1 dari 1 pasangan dinilai')).toBeInTheDocument()

  await user.click(
    screen.getByRole('checkbox', {
      name: /Saya sudah memeriksa jawaban/i,
    }),
  )
  await user.click(screen.getByRole('button', { name: 'Serahkan jawaban' }))
  expect(await screen.findByText('Penilaian relevansi telah diserahkan')).toBeInTheDocument()
}, 10000)

it('penilai eksternal dapat mengisi audit ekstraksi lewat /f/au_ tanpa login dan menyerahkan final', async () => {
  let spmVerdict: 'benar' | 'salah' | 'terlewat' | 'tidak_ada_di_teks' | null = null
  let submittedAt: string | null = null

  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    if (url === '/api/v1/public/tasks/au_tok1/audit?index=0') {
      const done = spmVerdict !== null
      return Response.json({
        data: {
          link: {
            label: 'Audit ekstraksi · petugas',
            target_username: 'petugas',
            target_version: null,
            target_slot: null,
            lock_single_device: true,
            submitted_at: submittedAt,
          },
          audit: {
            fingerprint: 'fp-1',
            extractor_version: 'v1.0.0',
            source_filename: 'sample.csv',
            index: 0,
            total_samples: 1,
            completed_samples: done ? 1 : 0,
            completed_cells: done ? 5 : 4,
            total_cells: 5,
            final: done,
            sample: {
              sample_id: 1,
              archive_id: 101,
              archive_status: 'Aktif',
              summary_raw: 'SPM 123/LS untuk CV Uji',
              extracted_spm: '123/LS',
              extracted_sp2d: '',
              extracted_date: '2020-01-01',
              extracted_amount: '5000',
              extracted_party: 'CV Uji',
            },
            judgments: {
              spm: { verdict: spmVerdict, note: '' },
              sp2d: { verdict: 'tidak_ada_di_teks', note: '' },
              date: { verdict: 'benar', note: '' },
              amount: { verdict: 'benar', note: '' },
              party: { verdict: 'benar', note: '' },
            },
            results: Object.fromEntries(
              ['spm', 'sp2d', 'date', 'amount', 'party'].map((f) => [
                f,
                {
                  rated: done || f !== 'spm' ? 1 : 0,
                  total: 1,
                  status: 'sementara',
                  metrics: null,
                },
              ]),
            ),
          },
        },
      })
    }
    if (
      url === '/api/v1/public/tasks/au_tok1/audit/101/fields/spm' &&
      options?.method === 'PATCH'
    ) {
      spmVerdict = 'benar'
      return Response.json({ data: { saved: true } })
    }
    if (url === '/api/v1/public/tasks/au_tok1/audit/submit' && options?.method === 'POST') {
      submittedAt = '2026-11-24T05:10:00Z'
      return Response.json({ data: { submitted_at: submittedAt } })
    }
    throw new Error(`Unexpected URL: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)

  window.history.replaceState(null, '', '/f/au_tok1')
  const user = userEvent.setup()
  render(<App />)

  expect(
    await screen.findByText('SPM 123/LS untuk CV Uji', {}, { timeout: 8000 }),
  ).toBeInTheDocument()
  expect(screen.queryByRole('navigation', { name: 'Navigasi utama' })).not.toBeInTheDocument()

  await user.click(screen.getByRole('combobox', { name: 'Penilaian Nomor SPM' }))
  await user.click(await screen.findByRole('option', { name: 'Benar' }))
  await user.click(screen.getByRole('button', { name: 'Simpan Nomor SPM' }))

  const confirmCheckbox = await screen.findByRole('checkbox', {
    name: /Saya sudah memeriksa seluruh sampel/i,
  })
  await user.click(confirmCheckbox)
  await user.click(screen.getByRole('button', { name: 'Serahkan audit final' }))

  expect(await screen.findByText('Audit ekstraksi telah diserahkan')).toBeInTheDocument()
}, 10000)

it('menampilkan penolakan perangkat lain (403) pada tautan penilaian publik', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      Response.json(
        { error: { code: 'forbidden', message: 'Tautan sudah diklaim perangkat lain.' } },
        { status: 403 },
      ),
    ),
  )

  window.history.replaceState(null, '', '/f/rv_terkunci')
  render(<App />)

  expect(
    await screen.findByText('Tautan sudah diklaim perangkat lain.', {}, { timeout: 4000 }),
  ).toBeInTheDocument()
})

it('admin dapat membuat, mereset, dan mencabut tautan tugas dari halaman kelola penilaian', async () => {
  let links: Array<Record<string, unknown>> = []

  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    if (url === '/api/v1/session') return stubAdminSession()
    if (url === '/api/v1/relevance-admin') {
      return Response.json({
        data: {
          available_versions: [],
          accounts: [
            { id: 1, username: 'peneliti', role: 'admin' },
            { id: 2, username: 'arsiparis', role: 'petugas' },
          ],
          reviews: [
            {
              version: 'uji-v2',
              sample_rows: 3,
              reviewers: [
                {
                  slot: 1,
                  user_id: 1,
                  username: 'peneliti',
                  submitted_at: '2026-11-24T00:00:00Z',
                  total: 2,
                  rated: 2,
                },
                {
                  slot: 2,
                  user_id: 2,
                  username: 'arsiparis',
                  submitted_at: null,
                  total: 2,
                  rated: 0,
                },
              ],
            },
          ],
        },
      })
    }
    if (url.startsWith('/api/v1/research/task-links?')) {
      return Response.json({ data: links })
    }
    if (url === '/api/v1/research/task-links' && options?.method === 'POST') {
      links = [
        {
          id: 9,
          task_kind: 'relevance',
          token_preview: 'rv_abc...xyz',
          target_user_id: 2,
          target_username: 'arsiparis',
          target_version: 'uji-v2',
          target_slot: 2,
          label: 'Penilai 2 (arsiparis) · uji-v2',
          lock_single_device: true,
          status: 'claimed',
          claimed_at: '2026-11-24T01:00:00Z',
          submitted_at: null,
          revoked_at: null,
          created_at: '2026-11-24T01:00:00Z',
        },
      ]
      return Response.json(
        {
          data: {
            ...links[0],
            token: 'rv_token_baru_1234',
            public_path: '/f/rv_token_baru_1234',
          },
        },
        { status: 201 },
      )
    }
    if (url === '/api/v1/research/task-links/9/reset-device' && options?.method === 'POST') {
      links = [{ ...links[0], status: 'unopened', claimed_at: null }]
      return Response.json({ data: { id: 9, reset: true } })
    }
    if (url === '/api/v1/research/task-links/9/revoke' && options?.method === 'POST') {
      links = [{ ...links[0], status: 'revoked', revoked_at: '2026-11-24T02:00:00Z' }]
      return Response.json({ data: { id: 9, revoked_at: '2026-11-24T02:00:00Z' } })
    }
    throw new Error(`Unexpected URL: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)

  window.history.replaceState(null, '', '/app/research/relevance-admin')
  const user = userEvent.setup()
  render(<App />)

  const createBtn = await screen.findByRole(
    'button',
    { name: 'Buat tautan 1-perangkat' },
    { timeout: 8000 },
  )
  await user.click(createBtn)

  expect(await screen.findByDisplayValue(/\/f\/rv_token_baru_1234$/)).toBeInTheDocument()
  await user.click(await screen.findByRole('button', { name: 'Reset perangkat' }))
  expect(await screen.findByText('Belum dibuka')).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Cabut' }))
  expect(await screen.findByText('Dicabut')).toBeInTheDocument()
}, 10000)
