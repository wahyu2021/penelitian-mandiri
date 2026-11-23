import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
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

describe('alur sesi React', () => {
  it('masuk, memulihkan sesi, lalu keluar tanpa localStorage', async () => {
    const user = userEvent.setup()
    let authenticated = false
    const fetchMock = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url === '/api/v1/dashboard')
        return Promise.resolve(
          json({
            data: {
              counts: { total: 0, active: 0, inactive: 0, with_file: 0 },
              recent: [],
            },
          }),
        )
      if (options?.method === 'POST') {
        authenticated = true
        return Promise.resolve(
          json({
            data: {
              authenticated: true,
              user: { id: 1, username: 'admin', role: 'admin' },
              csrf_token: 'baru',
            },
          }),
        )
      }
      if (options?.method === 'DELETE') {
        authenticated = false
        return Promise.resolve(json({ data: { authenticated: false } }))
      }
      return Promise.resolve(
        json({
          data: {
            authenticated,
            user: authenticated ? { id: 1, username: 'admin', role: 'admin' } : null,
            csrf_token: authenticated ? 'baru' : 'awal',
          },
        }),
      )
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)

    await screen.findByRole('heading', { name: 'Masuk ke aplikasi arsip' })
    await user.type(screen.getByLabelText('Nama pengguna'), 'admin')
    await user.type(screen.getByLabelText('Kata sandi'), 'kata-sandi-aman')
    await user.click(screen.getByRole('button', { name: 'Masuk' }))
    expect(await screen.findByText('admin · Admin')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Dashboard arsip' })).toBeInTheDocument()
    const mainNav = within(screen.getByRole('navigation', { name: 'Navigasi utama' }))
    expect(mainNav.getAllByRole('link').map((link) => link.textContent)).toEqual([
      'Dashboard',
      'Pencarian',
      'Impor',
      'Akun & Log',
    ])
    expect(mainNav.queryByRole('link', { name: 'Status' })).not.toBeInTheDocument()
    expect(mainNav.queryByRole('link', { name: 'Set uji' })).not.toBeInTheDocument()
    expect(mainNav.queryByRole('link', { name: 'Audit ekstraksi' })).not.toBeInTheDocument()
    expect(mainNav.queryByRole('link', { name: 'Perbandingan' })).not.toBeInTheDocument()
    const post = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
    expect(post?.[1].headers['X-CSRF-Token']).toBe('awal')
    expect(window.localStorage.length).toBe(0)

    await user.click(screen.getByRole('button', { name: 'Keluar' }))
    expect(
      await screen.findByRole('heading', { name: 'Masuk ke aplikasi arsip' }),
    ).toBeInTheDocument()
    const deletion = fetchMock.mock.calls.find(([, options]) => options?.method === 'DELETE')
    expect(deletion?.[1].headers['X-CSRF-Token']).toBe('baru')
  })

  it('melindungi route dan menampilkan menu sesuai peran', async () => {
    window.history.replaceState(null, '', '/app/status')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) =>
        Promise.resolve(
          url === '/api/v1/session'
            ? json({
                data: {
                  authenticated: true,
                  user: { id: 2, username: 'petugas', role: 'petugas' },
                  csrf_token: 't',
                },
              })
            : json({ data: { status: 'ok' } }),
        ),
      ),
    )
    render(<App />)
    expect(await screen.findByText('petugas · Petugas')).toBeInTheDocument()
    const nav = within(screen.getByRole('navigation', { name: 'Navigasi utama' }))
    expect(nav.getAllByRole('link').map((link) => link.textContent)).toEqual([
      'Dashboard',
      'Pencarian',
    ])
    expect(nav.queryByRole('link', { name: 'Status' })).not.toBeInTheDocument()
    expect(nav.queryByRole('link', { name: 'Audit ekstraksi' })).not.toBeInTheDocument()
    expect(nav.queryByRole('region', { name: 'Pengelolaan data' })).not.toBeInTheDocument()
    expect(nav.queryByRole('link', { name: 'Perbandingan' })).not.toBeInTheDocument()

    const user = userEvent.setup()
    const trigger = screen.getByRole('button', { name: 'Buka menu' })
    await user.click(trigger)
    let dialog = within(await screen.findByRole('dialog', { name: 'Menu aplikasi' }))
    expect(dialog.getByRole('region', { name: 'Akun' })).toHaveTextContent('petugas · Petugas')
    await user.keyboard('{Escape}')
    await waitFor(() => expect(trigger).toHaveFocus())

    await user.click(trigger)
    dialog = within(await screen.findByRole('dialog', { name: 'Menu aplikasi' }))
    await user.click(dialog.getByRole('link', { name: 'Pencarian' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('mengalihkan sesi anonim dan menampilkan galat login', async () => {
    window.history.replaceState(null, '', '/app/status')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url: string, options?: RequestInit) =>
        Promise.resolve(
          options?.method === 'POST'
            ? json(
                {
                  error: {
                    code: 'unauthorized',
                    message: 'Nama pengguna atau kata sandi tidak sesuai.',
                  },
                },
                401,
              )
            : json({ data: { authenticated: false, user: null, csrf_token: 'token' } }),
        ),
      ),
    )
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('heading', { name: 'Masuk ke aplikasi arsip' })
    await user.type(screen.getByLabelText('Nama pengguna'), 'petugas')
    await user.type(screen.getByLabelText('Kata sandi'), 'salah')
    await user.click(screen.getByRole('button', { name: 'Masuk' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Nama pengguna atau kata sandi tidak sesuai.',
    )
    await waitFor(() => expect(window.location.pathname).toBe('/login'))
  })

  it('menampilkan keadaan galat sesi dan tombol ulang', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Sesi belum dapat diperiksa.')
    expect(screen.getByRole('button', { name: 'Coba lagi' })).toBeEnabled()
  })

  it('mengalihkan rute penelitian lama ke ruang penelitian beserta query string', async () => {
    window.history.replaceState(null, '', '/app/compare?q=jembatan')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        if (url === '/api/v1/session') {
          return Promise.resolve(
            json({
              data: {
                authenticated: true,
                user: { id: 1, username: 'admin', role: 'admin' },
                csrf_token: 'token',
              },
            }),
          )
        }
        if (url === '/api/v1/search/filters') {
          return Promise.resolve(
            json({
              data: {
                opds: [{ id: 1, name: 'Dinas PU' }],
                default_method: 'like',
                methods: [],
              },
            }),
          )
        }
        if (url.startsWith('/api/v1/search/compare?')) {
          return Promise.resolve(
            json({
              data: {
                query: 'jembatan',
                limit: 10,
                filters: { opd_id: null, year: null, status: null },
                methods: [{ name: 'like', label: 'LIKE (pembanding)', items: [] }],
                score_note: 'Skor antarmetode tidak selalu sebanding.',
              },
            }),
          )
        }
        throw new Error(`Permintaan tidak terduga: ${url}`)
      }),
    )

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Perbandingan metode' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/app/research/compare')
    expect(window.location.search).toBe('?q=jembatan')
    expect(screen.getAllByText('Ruang Penelitian').length).toBeGreaterThan(0)
    const nav = within(screen.getByRole('navigation', { name: 'Navigasi utama' }))
    expect(nav.getByRole('link', { name: 'Perbandingan' })).toBeInTheDocument()
    expect(nav.getByRole('link', { name: 'Set uji' })).toBeInTheDocument()
    expect(nav.getByRole('link', { name: 'Buka pencarian arsip' })).toHaveAttribute(
      'href',
      '/app/search',
    )
    expect(nav.queryByRole('link', { name: 'Dashboard' })).not.toBeInTheDocument()
  })
})
