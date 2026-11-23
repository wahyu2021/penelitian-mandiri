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

function renderImport(role: 'admin' | 'petugas' = 'admin', fail = false) {
  window.history.replaceState(null, '', '/app/imports')
  const fetchMock = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
    if (url === '/api/v1/session')
      return Promise.resolve(
        json({
          data: {
            authenticated: true,
            user: { id: 1, username: role, role },
            csrf_token: 'csrf-test',
          },
        }),
      )
    if (url === '/api/v1/imports' && options?.method === 'POST') {
      if (fail) return Promise.resolve(json({ error: { message: 'Impor dibatalkan.' } }, 422))
      return Promise.resolve(
        json(
          {
            data: {
              batch_id: 2,
              source_sha256: 'a'.repeat(64),
              raw_count: 1,
              clean_count: 1,
              issue_count: 0,
              reference_counts_match: false,
              backup_filename: 'backup.sqlite',
            },
          },
          201,
        ),
      )
    }
    if (url === '/api/v1/imports')
      return Promise.resolve(
        json({
          data: {
            configured: true,
            verify_reference_counts: false,
            sources: [{ name: 'sample.sql', size_bytes: 120 }],
            history: [],
          },
        }),
      )
    if (url === '/api/v1/imports/preview?source=sample.sql')
      return Promise.resolve(
        json({
          data: {
            source: 'sample.sql',
            source_sha256: 'a'.repeat(64),
            size_bytes: 120,
            counts: { archives: 1, opds: 1, classifications: 1 },
            reference_archive_count: 1737,
            reference_total_matches: false,
          },
        }),
      )
    throw new Error(`Permintaan tidak terduga: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)
  return fetchMock
}

describe('impor salinan React', () => {
  it('admin melihat pratinjau, menyetujui penggantian, dan melihat hasil', async () => {
    const user = userEvent.setup()
    const fetchMock = renderImport()
    expect(await screen.findByRole('heading', { name: 'Impor salinan arsip' })).toBeInTheDocument()
    expect(await screen.findByText('Belum ada impor.')).toBeInTheDocument()
    await user.click(screen.getByRole('combobox', { name: 'Berkas dump' }))
    await user.click(await screen.findByRole('option', { name: 'sample.sql' }))
    expect(await screen.findByText('Pratinjau sample.sql')).toBeInTheDocument()
    const button = screen.getByRole('button', { name: 'Impor salinan' })
    expect(button).toBeDisabled()
    await user.click(screen.getByRole('checkbox'))
    await user.click(button)
    expect(await screen.findByText('Impor selesai · batch #2')).toBeInTheDocument()
    const post = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
    expect(post?.[0]).toBe('/api/v1/imports')
    expect(post?.[1].headers['X-CSRF-Token']).toBe('csrf-test')
    expect(JSON.parse(post?.[1].body)).toEqual({
      source: 'sample.sql',
      source_sha256: 'a'.repeat(64),
    })
  })

  it('menampilkan kegagalan impor tanpa menyatakan berhasil', async () => {
    const user = userEvent.setup()
    renderImport('admin', true)
    await screen.findByRole('heading', { name: 'Impor salinan arsip' })
    await screen.findByText('Belum ada impor.')
    await user.click(screen.getByRole('combobox', { name: 'Berkas dump' }))
    await user.click(await screen.findByRole('option', { name: 'sample.sql' }))
    await screen.findByText('Pratinjau sample.sql')
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Impor salinan' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Impor dibatalkan.')
    expect(screen.queryByText(/Impor selesai/)).not.toBeInTheDocument()
  })

  it('petugas tidak melihat menu impor dan tidak dapat membuka halaman', async () => {
    const fetchMock = renderImport('petugas')
    expect(await screen.findByText('403 · Akses ditolak')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Impor' })).not.toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalledWith('/api/v1/imports', expect.anything())
  })
})
