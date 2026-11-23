import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import App from '@/App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

const initial = {
  id: 21,
  is_relevant: null as number | null,
  notes: '',
  ragu: false,
  revision: 0,
  base_query_text: 'Perbaikan pipa',
  query_type: 'topik',
  summary_raw: 'Pembayaran perbaikan jaringan pipa.',
}

function judge() {
  let item = initial
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, options?: RequestInit) => {
      if (url === '/api/v1/session')
        return Response.json({
          data: {
            authenticated: true,
            user: { id: 2, username: 'arsiparis', role: 'petugas' },
            csrf_token: 'csrf',
          },
        })
      if (url === '/api/v1/relevance-reviews') return Response.json({ data: [{ version: 'v2' }] })
      if (url === '/api/v1/relevance-reviews/v2')
        return Response.json({
          data: {
            total: 1,
            index: 0,
            rated: Number(item.is_relevant !== null),
            submitted_at: null,
            item: {
              ...item,
              score: 0.938,
              first_notes: 'jawaban rahasia peneliti',
              noise_type: 'typo-rahasia',
            },
          },
        })
      if (url === '/api/v1/relevance-reviews/v2/21' && options?.method === 'PUT') {
        expect(new Headers(options.headers).get('X-CSRF-Token')).toBe('csrf')
        item = { ...item, ...JSON.parse(String(options.body)), revision: item.revision + 1 }
        return Response.json({
          data: { revision: item.revision, rated: Number(item.is_relevant !== null), total: 1 },
        })
      }
      throw new Error(`Unexpected URL: ${url}`)
    }),
  )
  window.history.replaceState(null, '', '/app/relevance')
}

it('menampilkan kebutuhan asli, menyimpan ragu parsial, lalu memulihkan jawaban akun saat reload', async () => {
  judge()
  const user = userEvent.setup()
  const app = render(<App />)
  expect(await screen.findByText('Perbaikan pipa')).toBeInTheDocument()
  expect(screen.getByText('Pembayaran perbaikan jaringan pipa.')).toBeInTheDocument()
  expect(screen.queryByText(/jawaban rahasia|0\.938|typo-rahasia/i)).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Kelola penilaian' })).not.toBeInTheDocument()
  expect(screen.getByRole('radio', { name: 'Belum dinilai' })).toBeChecked()
  await user.click(screen.getByRole('checkbox', { name: 'Tandai ragu' }))
  await user.type(screen.getByLabelText('Catatan (opsional)'), 'Perlu periksa tahun')
  await user.click(screen.getByRole('button', { name: 'Simpan jawaban' }))
  await screen.findByText('Jawaban tersimpan.')
  expect(screen.getByText('0 dari 1 pasangan dinilai')).toBeInTheDocument()
  app.unmount()
  render(<App />)
  expect(await screen.findByDisplayValue('Perlu periksa tahun')).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Tandai ragu' })).toBeChecked()
  await user.click(screen.getByRole('radio', { name: 'Tidak relevan' }))
  await user.click(screen.getByRole('button', { name: 'Simpan jawaban' }))
  expect(await screen.findByText('1 dari 1 pasangan dinilai')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Serahkan jawaban' })).toBeDisabled()
})

it('menolak halaman admin untuk petugas', async () => {
  judge()
  window.history.replaceState(null, '', '/app/relevance-admin')
  render(<App />)
  expect(await screen.findByRole('heading', { name: /Akses ditolak/ })).toBeInTheDocument()
})
