import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
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

const initialUsers = [
  {
    id: 1,
    username: 'admin',
    role: 'admin' as const,
    is_active: true,
    created_at: '2026-11-23T09:00:00Z',
  },
  {
    id: 2,
    username: 'petugas',
    role: 'petugas' as const,
    is_active: true,
    created_at: '2026-11-23T09:10:00Z',
  },
]

describe('administrasi akun dan log aktivitas React', () => {
  it('menolak petugas mengakses halaman admin tanpa memanggil endpoint admin', async () => {
    window.history.replaceState(null, '', '/app/users')
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === '/api/v1/session') {
        return Promise.resolve(
          json({
            data: {
              authenticated: true,
              user: { id: 2, username: 'petugas', role: 'petugas' },
              csrf_token: 'csrf-petugas',
            },
          }),
        )
      }
      throw new Error(`Permintaan tidak terduga: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    expect(await screen.findByRole('heading', { name: '403 · Akses ditolak' })).toBeInTheDocument()
    expect(fetchMock.mock.calls.every(([url]) => url === '/api/v1/session')).toBe(true)
  })

  it('mengelola akun, mencegah nonaktifkan diri sendiri, dan menampilkan log aktivitas', async () => {
    const user = userEvent.setup()
    window.history.replaceState(null, '', '/app/users')
    let users = [...initialUsers]
    let logs = [
      {
        id: 1,
        user_id: 1,
        username: 'admin',
        action: 'login',
        detail: null as string | null,
        created_at: '2026-11-23T09:15:00Z',
      },
    ]

    const fetchMock = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url === '/api/v1/session') {
        return Promise.resolve(
          json({
            data: {
              authenticated: true,
              user: { id: 1, username: 'admin', role: 'admin' },
              csrf_token: 'csrf-admin',
            },
          }),
        )
      }
      if (url === '/api/v1/admin/users' && !options?.method) {
        return Promise.resolve(json({ data: { users } }))
      }
      if (url === '/api/v1/admin/users' && options?.method === 'POST') {
        const body = JSON.parse(String(options.body)) as {
          username: string
          role: 'admin' | 'petugas'
          password: string
        }
        if (users.some((item) => item.username === body.username)) {
          return Promise.resolve(
            json({ error: { code: 'conflict', message: 'Nama pengguna sudah dipakai.' } }, 409),
          )
        }
        const created = {
          id: 3,
          username: body.username,
          role: body.role,
          is_active: true,
          created_at: '2026-11-23T10:00:00Z',
        }
        users = [...users, created]
        logs = [
          {
            id: 2,
            user_id: 1,
            username: 'admin',
            action: 'user_create',
            detail: `{"target_user_id":3,"username":"${body.username}"}`,
            created_at: '2026-11-23T10:00:00Z',
          },
          ...logs,
        ]
        return Promise.resolve(json({ data: { user: created } }, 201))
      }
      if (url === '/api/v1/admin/users/2/status' && options?.method === 'PATCH') {
        const body = JSON.parse(String(options.body)) as { is_active: boolean }
        users = users.map((item) => (item.id === 2 ? { ...item, is_active: body.is_active } : item))
        const updated = users.find((item) => item.id === 2)!
        return Promise.resolve(json({ data: { user: updated } }))
      }
      if (url === '/api/v1/admin/users/2/reset-password' && options?.method === 'POST') {
        const updated = users.find((item) => item.id === 2)!
        return Promise.resolve(json({ data: { user: updated } }))
      }
      if (url.startsWith('/api/v1/admin/activity')) {
        return Promise.resolve(json({ data: { items: logs } }))
      }
      throw new Error(`Permintaan tidak terduga: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    expect(await screen.findByText('Akun aktif Anda')).toBeInTheDocument()
    const adminRow = screen.getByText('Akun Anda').closest('tr')!
    expect(within(adminRow).queryByRole('button', { name: 'Nonaktifkan' })).not.toBeInTheDocument()

    // Buat akun baru
    await user.type(screen.getByLabelText('Nama pengguna'), 'petugas_baru')
    await user.type(screen.getByLabelText('Kata sandi (min. 10 karakter)'), 'sandi-kuat-2026')
    await user.click(screen.getByRole('button', { name: 'Buat akun' }))

    expect(
      await screen.findByText('Akun petugas_baru (petugas) berhasil dibuat.'),
    ).toBeInTheDocument()
    expect(screen.getByText('user_create')).toBeInTheDocument()

    const postCall = fetchMock.mock.calls.find(
      ([url, opts]) => url === '/api/v1/admin/users' && opts?.method === 'POST',
    )
    const headers = postCall?.[1]?.headers as Record<string, string> | undefined
    expect(headers?.['X-CSRF-Token']).toBe('csrf-admin')

    // Tangani error konflik username duplikat
    await user.type(screen.getByLabelText('Nama pengguna'), 'petugas_baru')
    await user.type(screen.getByLabelText('Kata sandi (min. 10 karakter)'), 'sandi-kuat-2026')
    await user.click(screen.getByRole('button', { name: 'Buat akun' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Nama pengguna sudah dipakai.')

    // Nonaktifkan petugas lalu reset kata sandinya
    const petugasRow = screen.getByText('petugas').closest('tr')!
    await user.click(within(petugasRow).getByRole('button', { name: 'Nonaktifkan' }))
    expect(await screen.findByText('Akun petugas kini berstatus Nonaktif.')).toBeInTheDocument()

    await user.click(within(petugasRow).getByRole('button', { name: 'Reset sandi' }))
    await user.type(screen.getByLabelText('Kata sandi baru untuk petugas'), 'sandi-reset-2026')
    await user.click(within(petugasRow).getByRole('button', { name: 'Simpan sandi' }))
    expect(
      await screen.findByText('Kata sandi untuk petugas telah diperbarui.'),
    ).toBeInTheDocument()
  })
})
