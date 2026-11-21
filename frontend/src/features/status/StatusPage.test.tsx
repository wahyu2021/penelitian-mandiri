import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StatusPage } from '@/features/status/StatusPage'

function renderStatus() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <StatusPage />
    </QueryClientProvider>,
  )
}

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

    renderStatus()

    expect(await screen.findByText('Layanan tersambung.')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith('/api/v1/health', {
      credentials: 'same-origin',
      cache: 'no-store',
    })
  })

  it('menampilkan galat dan tombol periksa ulang bila API gagal', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    renderStatus()

    expect(await screen.findByText('Layanan belum tersambung.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Periksa ulang' })).toBeEnabled()
  })
})
