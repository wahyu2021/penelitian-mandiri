import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '@/App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

function json(data: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => data }
}

const methods = [
  {
    name: 'like',
    label: 'LIKE (pembanding)',
    items: [{ id: 10, summary_raw: 'Jembatan kota', score: 1 }],
  },
  {
    name: 'levenshtein',
    label: 'Levenshtein',
    items: [{ id: 11, summary_raw: 'Jembatan <script>alert(1)</script>', score: 0.72 }],
  },
  { name: 'jaro_winkler', label: 'Jaro-Winkler', items: [] },
  { name: 'token_set', label: 'Token Set', items: [] },
  { name: 'ngram', label: 'N-gram Dice', items: [] },
]

function result(url: string, rows = methods) {
  const params = new URL(url, 'http://localhost').searchParams
  return json({
    data: {
      query: params.get('q') ?? '',
      limit: Number(params.get('limit') ?? 10),
      filters: {
        opd_id: params.has('opd_id') ? Number(params.get('opd_id')) : null,
        year: params.has('year') ? Number(params.get('year')) : null,
        status: params.has('status') ? Number(params.get('status')) : null,
      },
      methods: rows,
      score_note: 'Skor antarmetode tidak selalu sebanding.',
    },
  })
}

function renderCompare(
  options: {
    role?: 'admin' | 'petugas'
    path?: string
    compare?: (url: string) => Promise<ReturnType<typeof json>>
  } = {},
) {
  const role = options.role ?? 'admin'
  window.history.replaceState(null, '', options.path ?? '/app/compare')
  const fetchMock = vi.fn().mockImplementation((url: string) => {
    if (url === '/api/v1/session')
      return Promise.resolve(
        json({
          data: {
            authenticated: true,
            user: { id: 1, username: role, role },
            csrf_token: 'secret-test-token',
          },
        }),
      )
    if (url === '/api/v1/search/filters')
      return Promise.resolve(
        json({
          data: {
            opds: [{ id: 1, name: 'Dinas PU' }],
            default_method: 'like',
            methods: [],
          },
        }),
      )
    if (url.startsWith('/api/v1/search/compare?'))
      return options.compare?.(url) ?? Promise.resolve(result(url))
    throw new Error(`Permintaan tidak terduga: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return { view: render(<App />), fetchMock }
}

describe('perbandingan metode React', () => {
  it('admin mengirim kueri dan filter tanpa token sesi di URL', async () => {
    const user = userEvent.setup()
    const { fetchMock } = renderCompare()
    expect(
      await screen.findByText('Masukkan kata kunci untuk membandingkan metode.'),
    ).toBeInTheDocument()
    await user.type(screen.getByLabelText('Kata kunci'), 'jembatan')
    await user.click(screen.getByRole('combobox', { name: 'OPD' }))
    await user.click(await screen.findByRole('option', { name: 'Dinas PU' }))
    await user.type(screen.getByLabelText('Tahun'), '2020')
    await user.click(screen.getByRole('combobox', { name: 'Status' }))
    await user.click(await screen.findByRole('option', { name: 'Aktif' }))
    await user.click(screen.getByRole('combobox', { name: 'Hasil per metode' }))
    await user.click(await screen.findByRole('option', { name: '5' }))
    await user.click(screen.getByRole('button', { name: 'Bandingkan' }))
    expect(await screen.findByRole('heading', { name: 'Hasil per metode' })).toBeInTheDocument()
    expect(Object.fromEntries(new URLSearchParams(window.location.search))).toEqual({
      q: 'jembatan',
      opd_id: '1',
      year: '2020',
      status: '1',
      limit: '5',
    })
    expect(window.location.href).not.toContain('secret-test-token')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/search/compare?q=jembatan&opd_id=1&year=2020&status=1&limit=5',
      expect.objectContaining({ cache: 'no-store' }),
    )
  })

  it('mempertahankan urutan metode dan hasil API, serta merender teks mentah dengan aman', async () => {
    const { view } = renderCompare({ path: '/app/compare?q=jembatan' })
    expect(
      await screen.findByText('Skor antarmetode tidak selalu sebanding.', { exact: false }),
    ).toBeInTheDocument()
    expect(
      screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent),
    ).toEqual(['LIKE (pembanding)', 'Levenshtein', 'Jaro-Winkler', 'Token Set', 'N-gram Dice'])
    expect(screen.getByText('0.720')).toBeInTheDocument()
    expect(screen.getByText('Cocok')).toBeInTheDocument()
    expect(view.container.querySelector('script')).toBeNull()
    expect(view.container.textContent).toContain('<script>alert(1)</script>')
  })

  it('menampilkan semua metode saat hasil kosong dan dapat dibersihkan', async () => {
    const user = userEvent.setup()
    renderCompare({
      path: '/app/compare?q=tidak-ada',
      compare: (url) =>
        Promise.resolve(
          result(
            url,
            methods.map((method) => ({ ...method, items: [] })),
          ),
        ),
    })
    expect(
      (await screen.findAllByText('Tidak ada arsip yang cocok untuk metode ini.')).length,
    ).toBe(5)
    await user.click(screen.getByRole('button', { name: 'Bersihkan' }))
    expect(
      await screen.findByText('Masukkan kata kunci untuk membandingkan metode.'),
    ).toBeInTheDocument()
    expect(window.location.search).toBe('')
  })

  it('menangani loading, galat, dan coba lagi', async () => {
    const user = userEvent.setup()
    let rejectFirst: (error: Error) => void = () => {}
    let calls = 0
    renderCompare({
      path: '/app/compare?q=jembatan',
      compare: (url) => {
        calls += 1
        if (calls === 1)
          return new Promise((_resolve, reject) => {
            rejectFirst = reject
          })
        return Promise.resolve(result(url))
      },
    })
    expect(await screen.findByRole('status', { name: 'Membandingkan metode' })).toBeInTheDocument()
    rejectFirst(new Error('offline'))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Perbandingan belum dapat ditampilkan.',
    )
    await user.click(screen.getByRole('button', { name: 'Coba lagi' }))
    expect(await screen.findByRole('heading', { name: 'Hasil per metode' })).toBeInTheDocument()
  })

  it('petugas tidak melihat menu dan mendapat 403 pada alamat langsung tanpa memanggil API perbandingan', async () => {
    const { fetchMock } = renderCompare({ role: 'petugas', path: '/app/compare?q=jembatan' })
    expect(await screen.findByRole('heading', { name: '403 · Akses ditolak' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Perbandingan' })).not.toBeInTheDocument()
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).startsWith('/api/v1/search/compare')),
    ).toBe(false)
  })

  it('menampilkan penolakan 403 dari server untuk admin', async () => {
    renderCompare({
      path: '/app/compare?q=jembatan',
      compare: () => Promise.resolve(json({ error: { message: 'Akses ditolak.' } }, 403)),
    })
    expect(
      await screen.findByText('403 · Akses perbandingan ditolak oleh server.'),
    ).toBeInTheDocument()
  })
})
