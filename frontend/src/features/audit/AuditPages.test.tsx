import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '@/App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})
const json = (data: unknown, status = 200) => ({ ok: status < 400, status, json: async () => data })

function setup(path: string, role: 'admin' | 'petugas' = 'admin') {
  window.history.replaceState(null, '', path)
  let saved: string | null = null
  let confirmed = false
  const fetchMock = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
    if (url === '/api/v1/session')
      return Promise.resolve(
        json({
          data: { authenticated: true, user: { id: 1, username: role, role }, csrf_token: 'csrf' },
        }),
      )
    if (url === '/api/v1/extraction-audit/reviewers') return Promise.resolve(json({ data: [] }))
    if (url === '/api/v1/extraction-audit?index=0')
      return Promise.resolve(
        json({
          data: {
            fingerprint: 'abc',
            extractor_version: 'v1.0.0',
            source_filename: 'sample.csv',
            index: 0,
            total_samples: 1,
            completed_samples: 0,
            completed_cells: saved ? 1 : 0,
            total_cells: 5,
            final: false,
            sample: {
              sample_id: 1,
              archive_id: 7,
              archive_status: 'valid',
              summary_raw: 'Ringkasan dokumen',
              extracted_spm: 'SPM 1',
              extracted_sp2d: '',
              extracted_date: '',
              extracted_amount: '',
              extracted_party: '',
            },
            judgments: Object.fromEntries(
              ['spm', 'sp2d', 'date', 'amount', 'party'].map((field) => [
                field,
                { verdict: field === 'spm' ? saved : null, note: '' },
              ]),
            ),
            results: Object.fromEntries(
              ['spm', 'sp2d', 'date', 'amount', 'party'].map((field) => [
                field,
                {
                  rated: field === 'spm' && saved ? 1 : 0,
                  total: 1,
                  status: 'sementara',
                  metrics: null,
                },
              ]),
            ),
          },
        }),
      )
    if (url === '/api/v1/extraction-audit/7/fields/spm' && options?.method === 'PATCH') {
      saved = JSON.parse(options.body as string).verdict
      return Promise.resolve(json({ data: { saved: true } }))
    }
    if (url === '/api/v1/spm-types')
      return Promise.resolve(
        json({
          data: [
            {
              code: 'A1',
              label: 'Dugaan awal',
              confidence: confirmed ? 'terkonfirmasi' : 'dugaan',
              source_note: confirmed ? 'Konfirmasi dari petugas' : null,
              confirmed_by: confirmed ? 'admin' : null,
              confirmed_at: confirmed ? '2026-11-23' : null,
              archive_count: 2,
            },
          ],
        }),
      )
    if (url === '/api/v1/spm-types/A1/confirm' && options?.method === 'POST') {
      confirmed = true
      return Promise.resolve(json({ data: {} }))
    }
    throw new Error(`Permintaan tidak terduga: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)
  return fetchMock
}

describe('audit ekstraksi dan kamus SPM', () => {
  it('menyimpan verdict, menampilkan progres sementara, dan belum menawarkan ekspor', async () => {
    const user = userEvent.setup()
    const fetchMock = setup('/app/extraction-audit')
    expect(await screen.findByText(/0 dari 5 sel dinilai/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Unduh CSV/ })).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Penilaian Nomor SPM'), 'benar')
    await user.click(screen.getByRole('button', { name: 'Simpan Nomor SPM' }))
    expect(await screen.findByText(/1 dari 5 sel dinilai/)).toBeInTheDocument()
    const patch = fetchMock.mock.calls.find(
      ([url, options]) =>
        url === '/api/v1/extraction-audit/7/fields/spm' && options?.method === 'PATCH',
    )
    expect(patch?.[1].headers['X-CSRF-Token']).toBe('csrf')
    expect(JSON.parse(patch?.[1].body)).toEqual({ verdict: 'benar', note: '', fingerprint: 'abc' })
  })

  it('memerlukan sumber saat admin mengonfirmasi dugaan SPM', async () => {
    const user = userEvent.setup()
    const fetchMock = setup('/app/spm-types')
    const card = (await screen.findByText('A1')).closest('[data-slot="card"]') as HTMLElement
    const button = within(card).getByRole('button', { name: 'Konfirmasi kode' })
    expect(button).toBeDisabled()
    await user.clear(within(card).getByLabelText('Label hasil konfirmasi'))
    await user.type(within(card).getByLabelText('Label hasil konfirmasi'), 'Jenis A')
    await user.type(
      within(card).getByLabelText('Sumber atau bukti konfirmasi'),
      'Konfirmasi dari petugas',
    )
    await user.click(button)
    expect(await screen.findByText(/2 arsip · Terkonfirmasi/)).toBeInTheDocument()
    const post = fetchMock.mock.calls.find(
      ([url, options]) => url === '/api/v1/spm-types/A1/confirm' && options?.method === 'POST',
    )
    expect(JSON.parse(post?.[1].body)).toEqual({
      label: 'Jenis A',
      source_note: 'Konfirmasi dari petugas',
    })
  })

  it('menolak tampilan kamus SPM bagi petugas', async () => {
    const fetchMock = setup('/app/spm-types', 'petugas')
    expect(await screen.findByText('403 · Akses ditolak')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/v1/spm-types')).toBe(false)
  })
})
