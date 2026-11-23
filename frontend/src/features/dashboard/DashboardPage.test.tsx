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

function renderDashboard(dashboard: () => Promise<unknown>, isAuthenticated = () => true) {
  window.history.replaceState(null, '', '/app/dashboard')
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((url: string) =>
      url === '/api/v1/session'
        ? Promise.resolve(
            json({
              data: {
                authenticated: isAuthenticated(),
                user: isAuthenticated() ? { id: 1, username: 'admin', role: 'admin' } : null,
                csrf_token: 't',
              },
            }),
          )
        : dashboard(),
    ),
  )
  render(<App />)
}

describe('dashboard React', () => {
  it('menampilkan angka, pembaruan data, dan tautan arsip dari API', async () => {
    renderDashboard(() =>
      Promise.resolve(
        json({
          data: {
            counts: { total: 1234, active: 900, inactive: 300, with_file: 45 },
            recent: [
              { id: 13, year: 2022, summary_raw: 'Surat izin', opd_name: 'Dinas PU' },
              { id: 9, year: null, summary_raw: null, opd_name: null },
            ],
            latest_import: {
              source_filename: 'simanis_2026.sql',
              imported_at: '2026-11-23T10:00:00Z',
              clean_count: 1234,
            },
          },
        }),
      ),
    )
    expect(await screen.findByText('1.234')).toBeInTheDocument()
    expect(screen.getByText(/simanis_2026\.sql/)).toBeInTheDocument()
    expect(screen.getByText('Surat izin')).toBeInTheDocument()
    expect(screen.getByText('Dinas PU')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /#13/ })).toHaveAttribute('href', '/app/archives/13')
    expect(screen.getByText('Ringkasan tidak tersedia')).toBeInTheDocument()
    expect(screen.getByText('Tahun tidak tersedia')).toBeInTheDocument()
    expect(screen.getByText('Berdasarkan ID arsip, bukan tanggal dokumen.')).toBeInTheDocument()
  })

  it('mengarahkan pencarian cepat ke halaman pencarian', async () => {
    const user = userEvent.setup()
    window.history.replaceState(null, '', '/app/dashboard')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        if (url === '/api/v1/session') {
          return Promise.resolve(
            json({
              data: {
                authenticated: true,
                user: { id: 1, username: 'petugas', role: 'petugas' },
                csrf_token: 't',
              },
            }),
          )
        }
        if (url === '/api/v1/dashboard') {
          return Promise.resolve(
            json({
              data: {
                counts: { total: 0, active: 0, inactive: 0, with_file: 0 },
                recent: [],
                latest_import: null,
              },
            }),
          )
        }
        if (url === '/api/v1/search/filters') {
          return Promise.resolve(
            json({
              data: { opds: [], default_method: 'levenshtein', methods: [] },
            }),
          )
        }
        if (url.startsWith('/api/v1/search?')) {
          return Promise.resolve(
            json({
              data: {
                query: 'jembatan',
                method: 'levenshtein',
                items: [],
                pagination: { limit: 20, offset: 0, total: 0 },
              },
            }),
          )
        }
        throw new Error(`Permintaan tidak terduga: ${url}`)
      }),
    )

    render(<App />)
    await screen.findByRole('heading', { name: 'Dashboard arsip' })
    expect(await screen.findByText('Belum ada riwayat impor data.')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Pencarian cepat arsip'), 'jembatan')
    await user.click(screen.getByRole('button', { name: 'Cari arsip' }))
    expect(await screen.findByRole('heading', { name: 'Pencarian arsip' })).toBeInTheDocument()
    expect(window.location.pathname + window.location.search).toBe('/app/search?q=jembatan')
  })

  it('menampilkan keadaan kosong tanpa angka contoh', async () => {
    renderDashboard(() =>
      Promise.resolve(
        json({
          data: {
            counts: { total: 0, active: 0, inactive: 0, with_file: 0 },
            recent: [],
          },
        }),
      ),
    )
    expect(await screen.findByText('Belum ada arsip dalam salinan data.')).toBeInTheDocument()
    expect(screen.getAllByText('0')).toHaveLength(4)
  })

  it('menampilkan loading dan galat serta dapat mencoba ulang', async () => {
    const user = userEvent.setup()
    let rejectFirst: (reason: Error) => void = () => {}
    let calls = 0
    renderDashboard(() => {
      calls += 1
      if (calls === 1)
        return new Promise((_resolve, reject) => {
          rejectFirst = reject
        })
      return Promise.resolve(
        json({
          data: {
            counts: { total: 0, active: 0, inactive: 0, with_file: 0 },
            recent: [],
          },
        }),
      )
    })
    expect(await screen.findByRole('status', { name: 'Memuat ringkasan' })).toBeInTheDocument()
    rejectFirst(new Error('offline'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Ringkasan belum dapat dimuat.')
    await user.click(screen.getByRole('button', { name: 'Coba lagi' }))
    expect(await screen.findByText('Belum ada arsip dalam salinan data.')).toBeInTheDocument()
  })

  it('mengalihkan ke login jika sesi API habis', async () => {
    let expired = false
    renderDashboard(
      () => {
        expired = true
        return Promise.resolve(
          json({ error: { code: 'unauthorized', message: 'Sesi habis.' } }, 401),
        )
      },
      () => !expired,
    )
    expect(
      await screen.findByRole('heading', { name: 'Masuk ke aplikasi arsip' }),
    ).toBeInTheDocument()
  })
})
