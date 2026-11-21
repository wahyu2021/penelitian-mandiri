import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import App from '@/App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('status layanan', () => {
  it('menampilkan status dari Flask API', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ data: { status: 'ok' } }),
      }),
    )

    render(<App />)

    expect(await screen.findByText('Layanan tersambung.')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith('/api/v1/health', {
      credentials: 'same-origin',
      cache: 'no-store',
    })
  })

  it('menampilkan galat dan tombol periksa ulang bila API gagal', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    render(<App />)

    expect(await screen.findByText('Layanan belum tersambung.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Periksa ulang' })).toBeEnabled()
  })
})
