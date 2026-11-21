import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
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

function item(id: number, summary_raw = 'Jembatan kota') {
  return {
    id,
    summary_raw,
    opd_name: 'Dinas PU',
    year: 2020,
    spm_number: null,
    file_number: 'B-1',
    has_document: true,
    score: 0.73,
  }
}

function searchResult(url: string, items = [item(1)], total = items.length) {
  const params = new URL(url, 'http://localhost').searchParams
  return json({
    data: {
      query: params.get('q') ?? '',
      method: params.get('method') ?? 'like',
      items,
      pagination: {
        limit: Number(params.get('limit') ?? 20),
        offset: Number(params.get('offset') ?? 0),
        total,
      },
    },
  })
}

function renderSearch(
  options: {
    role?: 'admin' | 'petugas'
    path?: string
    search?: (url: string) => Promise<unknown>
    filters?: () => Promise<unknown>
  } = {},
) {
  const role = options.role ?? 'admin'
  window.history.replaceState(null, '', options.path ?? '/app/search')
  const fetchMock = vi.fn().mockImplementation((url: string) => {
    if (url === '/api/v1/session')
      return Promise.resolve(
        json({
          data: {
            authenticated: true,
            user: { id: 1, username: role, role },
            csrf_token: 'test-token',
          },
        }),
      )
    if (url === '/api/v1/search/filters')
      return (
        options.filters?.() ??
        Promise.resolve(
          json({
            data: {
              opds: [{ id: 1, name: 'Dinas PU' }],
              default_method: 'like',
              methods:
                role === 'admin'
                  ? [
                      { name: 'like', label: 'LIKE (pembanding)' },
                      { name: 'levenshtein', label: 'Levenshtein' },
                    ]
                  : [],
            },
          }),
        )
      )
    if (url.startsWith('/api/v1/search?'))
      return options.search?.(url) ?? Promise.resolve(searchResult(url))
    throw new Error(`Permintaan tidak terduga: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return render(<App />)
}

describe('pencarian arsip React', () => {
  it('petugas mencari dengan filter tanpa pemilih metode dan URL tanpa sesi', async () => {
    const user = userEvent.setup()
    const view = renderSearch({ role: 'petugas' })
    expect(await screen.findByText('Masukkan kata kunci untuk mulai mencari.')).toBeInTheDocument()
    await screen.findByRole('option', { name: 'Dinas PU' })
    expect(screen.queryByLabelText('Metode pencarian')).not.toBeInTheDocument()
    await user.type(screen.getByLabelText('Kata kunci'), 'jembatan')
    await user.selectOptions(screen.getByLabelText('OPD'), '1')
    await user.type(screen.getByLabelText('Tahun'), '2020')
    await user.selectOptions(screen.getByLabelText('Status'), '1')
    await user.selectOptions(screen.getByLabelText('Hasil per halaman'), '10')
    await user.click(screen.getByRole('button', { name: 'Cari arsip' }))
    expect(await screen.findByText('Arsip #1')).toBeInTheDocument()
    const params = new URLSearchParams(window.location.search)
    expect(Object.fromEntries(params)).toEqual({
      q: 'jembatan',
      opd_id: '1',
      year: '2020',
      status: '1',
      limit: '10',
    })
    expect(window.location.href).not.toContain('test-token')
    expect(screen.getByRole('link', { name: 'Arsip #1' })).toHaveAttribute(
      'href',
      '/app/archives/1?q=jembatan&opd_id=1&year=2020&status=1&limit=10',
    )
    expect(view.container.querySelector('mark')?.textContent).toBe('Jembatan')
    expect(
      screen.getByText('LIKE menunjukkan kecocokan kata, tanpa peringkat kemiripan.'),
    ).toBeInTheDocument()
  })

  it('admin membuka URL fuzzy dan melihat skor tanpa mengubah teks mentah menjadi HTML', async () => {
    const view = renderSearch({
      path: '/app/search?q=jembatan&method=levenshtein',
      search: (url) =>
        Promise.resolve(searchResult(url, [item(5, 'Jembatan <script>alert(1)</script>')])),
    })
    expect(await screen.findByText('Arsip #5')).toBeInTheDocument()
    expect(screen.getByLabelText('Metode pencarian')).toHaveValue('levenshtein')
    expect(screen.getByText('Skor 0.730')).toBeInTheDocument()
    expect(screen.getByText(/bukan probabilitas relevansi/)).toBeInTheDocument()
    expect(view.container.querySelector('mark')?.textContent).toBe('Jembatan')
    expect(view.container.querySelector('script')).toBeNull()
    expect(view.container.textContent).toContain('<script>alert(1)</script>')
  })

  it('menampilkan hasil kosong dan membolehkan membersihkan pencarian', async () => {
    const user = userEvent.setup()
    renderSearch({
      path: '/app/search?q=tidak-ada',
      search: (url) => Promise.resolve(searchResult(url, [], 0)),
    })
    expect(
      await screen.findByText('Tidak ada arsip yang cocok. Coba kata kunci atau filter lain.'),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Bersihkan' }))
    expect(await screen.findByText('Masukkan kata kunci untuk mulai mencari.')).toBeInTheDocument()
    expect(window.location.search).toBe('')
  })

  it('menangani loading, galat, dan ulangi pencarian', async () => {
    const user = userEvent.setup()
    let rejectFirst: (reason: Error) => void = () => {}
    let calls = 0
    renderSearch({
      path: '/app/search?q=jembatan',
      search: (url) => {
        calls += 1
        if (calls === 1)
          return new Promise((_resolve, reject) => {
            rejectFirst = reject
          })
        return Promise.resolve(searchResult(url))
      },
    })
    expect(await screen.findByRole('status', { name: 'Mencari arsip' })).toBeInTheDocument()
    rejectFirst(new Error('offline'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Pencarian belum dapat ditampilkan.')
    await user.click(screen.getByRole('button', { name: 'Coba lagi' }))
    expect(await screen.findByText('Arsip #1')).toBeInTheDocument()
  })

  it('memindahkan halaman hasil lewat URL tanpa mengubah ranking API', async () => {
    const user = userEvent.setup()
    renderSearch({
      path: '/app/search?q=arsip&limit=10',
      search: (url) => {
        const offset = Number(new URL(url, 'http://localhost').searchParams.get('offset') ?? 0)
        const rows =
          offset === 0
            ? Array.from({ length: 10 }, (_, i) => item(i + 1, `Arsip ${i + 1}`))
            : [item(11, 'Arsip 11')]
        return Promise.resolve(searchResult(url, rows, 11))
      },
    })
    expect(await screen.findByText('Arsip #1')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Berikutnya' }))
    expect(await screen.findByText('Arsip #11')).toBeInTheDocument()
    expect(new URLSearchParams(window.location.search).get('offset')).toBe('10')
    await user.click(screen.getByRole('button', { name: 'Sebelumnya' }))
    expect(await screen.findByText('Arsip #1')).toBeInTheDocument()
    await waitFor(() =>
      expect(new URLSearchParams(window.location.search).get('offset')).toBeNull(),
    )
  })
})
