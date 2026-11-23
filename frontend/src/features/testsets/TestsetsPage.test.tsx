import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '@/App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

const digest = 'a'.repeat(64)
const summary = {
  version: 'v2-uji',
  content_sha256: digest,
  locked_at: null,
  locked_by: null,
  updated_at: '2026-11-23T00:00:00Z',
  n_queries: 2,
  n_base_queries: 2,
  n_tuning: 1,
  n_test: 1,
  n_tuning_base_queries: 1,
  n_test_base_queries: 1,
  sources: { sintetis: 1, arsiparis: 1 },
}
const queries = [
  {
    query_id: 'Q1',
    base_query_id: 'B1',
    query_text: 'Perbaikan jalan',
    query_type: 'topik',
    noise_type: 'typo',
    source: 'sintetis',
    split: 'tuning',
  },
  {
    query_id: 'Q2',
    base_query_id: 'B2',
    query_text: 'Pengadaan pipa',
    query_type: 'topik',
    noise_type: 'tanpa_gangguan',
    source: 'arsiparis',
    split: 'test',
  },
]

function setup(role: 'admin' | 'petugas' = 'admin') {
  let registered = false
  let locked = false
  window.history.replaceState(null, '', '/app/testsets')
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    const state = locked ? { ...summary, locked_at: summary.updated_at, locked_by: 1 } : summary
    if (url === '/api/v1/session')
      return Response.json({
        data: { authenticated: true, user: { id: 1, username: role, role }, csrf_token: 'token' },
      })
    if (url === '/api/v1/testsets' && options?.method === 'POST') {
      registered = true
      return Response.json({ data: summary }, { status: 201 })
    }
    if (url === '/api/v1/testsets') return Response.json({ data: registered ? [state] : [] })
    if (url === '/api/v1/testsets/v2-uji') return Response.json({ data: { ...state, queries } })
    if (url === '/api/v1/testsets/v2-uji/lock') {
      locked = true
      return Response.json({ data: { ...summary, locked_at: summary.updated_at, locked_by: 1 } })
    }
    throw new Error(`URL tidak terduga: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)
  return fetchMock
}

it('mendaftarkan draf, menyaring kueri, lalu mengunci dengan hash yang ditinjau', async () => {
  const user = userEvent.setup()
  const fetchMock = setup()
  await screen.findByText(/Belum ada versi/)
  const file = new File(['{}'], 'testset.json', { type: 'application/json' })
  await user.upload(screen.getByLabelText('Berkas JSON set uji baru'), file)
  const register = screen.getByRole('button', { name: 'Daftarkan versi' })
  expect(register).toBeEnabled()
  await user.click(register)
  expect(await screen.findByText('Versi v2-uji disimpan.')).toBeInTheDocument()
  await screen.findByRole('heading', { name: 'v2-uji · Terbuka' })
  expect(fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')?.[1]?.body).toBe(
    file,
  )
  expect(screen.getByText('1 sintetis · 1 nyata (arsiparis)')).toBeInTheDocument()
  await user.selectOptions(screen.getByLabelText('Asal kueri'), 'arsiparis')
  expect(screen.queryByText('Perbaikan jalan')).not.toBeInTheDocument()
  expect(screen.getByText('Pengadaan pipa')).toBeInTheDocument()
  const lock = screen.getByRole('button', { name: 'Kunci versi' })
  expect(lock).toBeDisabled()
  await user.click(screen.getByRole('checkbox'))
  await user.click(lock)
  expect(await screen.findByRole('link', { name: 'Unduh JSON' })).toHaveAttribute(
    'href',
    '/api/v1/testsets/v2-uji/export',
  )
  expect(screen.queryByRole('button', { name: 'Ganti isi draf' })).not.toBeInTheDocument()
  const lockCall = fetchMock.mock.calls.find(([url]) => url.endsWith('/lock'))
  expect(new Headers(lockCall?.[1]?.headers).get('If-Match')).toBe(`"${digest}"`)
})

it('membatasi halaman dan menu untuk admin', async () => {
  const fetchMock = setup('petugas')
  expect(await screen.findByRole('heading', { name: /Akses ditolak/ })).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Set uji' })).not.toBeInTheDocument()
  expect(fetchMock.mock.calls.some(([url]) => url.startsWith('/api/v1/testsets'))).toBe(false)
})
