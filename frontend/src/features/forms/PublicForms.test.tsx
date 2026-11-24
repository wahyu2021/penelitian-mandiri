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

it('responden dapat mengisi formulir publik tanpa login dan melihat konfirmasi selesai', async () => {
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    if (url === '/api/v1/public/forms/tok-p01') {
      return Response.json({
        data: {
          already_submitted: false,
          submitted_at: null,
          participant_code: 'P01',
          participant_role: 'petugas',
          lock_single_device: true,
          form: {
            id: 7,
            title: 'Survei Lapangan',
            description: 'Mohon isi penilaian singkat.',
            form_kind: 'custom',
            questions: [
              { id: 'nilai', type: 'scale', label: 'Kemudahan pencarian', required: true },
              { id: 'catatan', type: 'textarea', label: 'Saran', required: false },
            ],
          },
        },
      })
    }
    if (url === '/api/v1/public/forms/tok-p01/submit' && options?.method === 'POST') {
      const parsed = JSON.parse(String(options.body)) as { answers: Record<string, unknown> }
      expect(parsed.answers.nilai).toBe(5)
      return Response.json(
        {
          data: {
            submitted: true,
            submitted_at: '2026-11-24T04:00:00Z',
            participant_code: 'P01',
            sus_score: null,
          },
        },
        { status: 201 },
      )
    }
    throw new Error(`Unexpected URL: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)

  window.history.replaceState(null, '', '/f/tok-p01')
  const user = userEvent.setup()
  render(<App />)

  expect(
    await screen.findByRole('heading', { name: 'Survei Lapangan' }, { timeout: 8000 }),
  ).toBeInTheDocument()
  expect(screen.getByText('Terkunci pada perangkat ini')).toBeInTheDocument()
  expect(screen.queryByRole('navigation', { name: 'Navigasi utama' })).not.toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: '5' }))
  await user.type(screen.getByPlaceholderText('Tulis catatan bila ada…'), 'Sudah cepat')
  await user.click(screen.getByRole('button', { name: 'Kirim jawaban' }))

  expect(await screen.findByText('Terima kasih, jawaban Anda sudah tercatat')).toBeInTheDocument()
}, 10000)

it('menampilkan pesan error saat tautan diklaim perangkat lain (403)', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      Response.json(
        {
          error: {
            code: 'forbidden',
            message: 'Tautan ini sudah dikunci pada perangkat pertama.',
          },
        },
        { status: 403 },
      ),
    ),
  )

  window.history.replaceState(null, '', '/f/tok-terkunci')
  render(<App />)

  expect(
    await screen.findByText(
      'Tautan ini sudah dikunci pada perangkat pertama.',
      {},
      { timeout: 4000 },
    ),
  ).toBeInTheDocument()
})

it('admin dapat membuat template SUS dan generate tautan di /app/research/forms, petugas ditolak 403', async () => {
  let forms: Array<Record<string, unknown>> = []
  let links: Array<Record<string, unknown>> = []

  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    if (url === '/api/v1/session') return stubSession('admin')
    if (url === '/api/v1/research/forms' && (!options?.method || options.method === 'GET')) {
      return Response.json({ data: forms })
    }
    if (url === '/api/v1/research/forms' && options?.method === 'POST') {
      expect(new Headers(options.headers).get('X-CSRF-Token')).toBe('csrf')
      forms = [
        {
          id: 1,
          slug: 'sus-abcd',
          title: 'Kuesioner SUS & Umpan Balik Petugas',
          description: 'Uji',
          form_kind: 'sus',
          created_at: '2026-11-24T04:00:00Z',
          total_links: 0,
          total_responses: 0,
        },
      ]
      return Response.json(
        {
          data: {
            id: 1,
            slug: 'sus-abcd',
            title: 'Kuesioner SUS & Umpan Balik Petugas',
            description: 'Uji',
            form_kind: 'sus',
            questions: [],
            created_at: '2026-11-24T04:00:00Z',
          },
        },
        { status: 201 },
      )
    }
    if (url === '/api/v1/research/forms/1') {
      return Response.json({
        data: {
          form: {
            id: 1,
            slug: 'sus-abcd',
            title: 'Kuesioner SUS & Umpan Balik Petugas',
            description: 'Uji',
            form_kind: 'sus',
            questions: [],
            created_at: '2026-11-24T04:00:00Z',
          },
          links,
          responses: [],
          sus_summary: {
            status: 'pending',
            n_respondents: 0,
            mean_sus: null,
            median_sus: null,
            min_sus: null,
            max_sus: null,
            std_sus: null,
            limitations: [],
          },
        },
      })
    }
    if (url === '/api/v1/research/forms/1/links' && options?.method === 'POST') {
      expect(new Headers(options.headers).get('X-CSRF-Token')).toBe('csrf')
      links = [
        {
          id: 10,
          token_preview: 'tok123...abcd',
          participant_code: 'P01',
          participant_role: 'petugas',
          lock_single_device: true,
          status: 'unopened',
          claimed_at: null,
          submitted_at: null,
          revoked_at: null,
          created_at: '2026-11-24T04:01:00Z',
        },
      ]
      return Response.json(
        {
          data: {
            id: 10,
            form_id: 1,
            token: 'tok123456abcd',
            token_preview: 'tok123...abcd',
            public_path: '/f/tok123456abcd',
            participant_code: 'P01',
            participant_role: 'petugas',
            lock_single_device: true,
            status: 'unopened',
            created_at: '2026-11-24T04:01:00Z',
          },
        },
        { status: 201 },
      )
    }
    throw new Error(`Unexpected URL: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)

  window.history.replaceState(null, '', '/app/research/forms')
  const user = userEvent.setup()
  const app = render(<App />)

  await user.click(
    await screen.findByRole('button', { name: /Buat template SUS 10 butir/i }, { timeout: 4000 }),
  )
  await user.click(await screen.findByRole('button', { name: /Generate tautan/i }))

  expect(await screen.findByDisplayValue(/\/f\/tok123456abcd/)).toBeInTheDocument()
  app.unmount()

  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url === '/api/v1/session') return stubSession('petugas')
      throw new Error(`Unexpected URL: ${url}`)
    }),
  )
  window.history.replaceState(null, '', '/app/research/forms')
  render(<App />)
  expect(
    await screen.findByText('Pengelolaan formulir publik hanya tersedia untuk admin.'),
  ).toBeInTheDocument()
})
