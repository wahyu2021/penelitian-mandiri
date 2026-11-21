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

const fullArchive = {
  id: 41,
  status: 1,
  year: 2020,
  opd_name: 'Dinas PU',
  classification_label: 'Pekerjaan Umum',
  file_number: 'BRK-41',
  index_label: 'Jembatan',
  summary_raw: 'Permohonan jembatan <script>alert(1)</script>',
  has_document: true,
  location: { block: 'A', rack: '2', row: '3', box_number: 'Box 4' },
  extraction: {
    spm_number: 'SPM-41',
    sp2d_number: 'SP2D-41',
    document_date: '2020-04-20',
    amount_rp: 2500000,
    party_name: 'CV Contoh',
    spm_type: { code: 'ZZ_TEST', label: 'Jenis dugaan', confidence: 'dugaan' },
  },
}

function renderDetail(
  options: {
    path?: string
    detail?: () => Promise<ReturnType<typeof json>>
  } = {},
) {
  window.history.replaceState(null, '', options.path ?? '/app/archives/41?q=jembatan&offset=10')
  let sessionExpired = false
  const fetchMock = vi.fn().mockImplementation((url: string) => {
    if (url === '/api/v1/session')
      return Promise.resolve(
        json({
          data: {
            authenticated: !sessionExpired,
            user: sessionExpired ? null : { id: 1, username: 'petugas', role: 'petugas' },
            csrf_token: 'secret-test-token',
          },
        }),
      )
    if (url.startsWith('/api/v1/archives/'))
      return (options.detail?.() ?? Promise.resolve(json({ data: fullArchive }))).then(
        (response) => {
          if (response.status === 401) sessionExpired = true
          return response
        },
      )
    if (url === '/api/v1/search/filters')
      return Promise.resolve(
        json({
          data: { opds: [], default_method: 'like', methods: [] },
        }),
      )
    if (url.startsWith('/api/v1/search?'))
      return Promise.resolve(
        json({
          data: {
            query: 'jembatan',
            method: 'like',
            items: [],
            pagination: { limit: 20, offset: 10, total: 0 },
          },
        }),
      )
    throw new Error(`Permintaan tidak terduga: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return { view: render(<App />), fetchMock }
}

describe('detail arsip React', () => {
  it('menampilkan teks asli, metadata, lokasi, dugaan, dan kembali ke hasil pencarian', async () => {
    const user = userEvent.setup()
    const { view, fetchMock } = renderDetail({
      path: '/app/archives/41?q=jembatan&offset=10&token=should-not-leak',
    })
    expect(
      await screen.findByText('Permohonan jembatan <script>alert(1)</script>'),
    ).toBeInTheDocument()
    expect(view.container.querySelector('script')).toBeNull()
    expect(screen.getByText(/2\.500\.000/)).toBeInTheDocument()
    expect(screen.getByText('ZZ_TEST · Jenis dugaan')).toBeInTheDocument()
    expect(
      screen.getByText('Jenis SPM masih dugaan. Cocokkan dengan ringkasan asli.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Box 4')).toBeInTheDocument()
    expect(screen.getByText('Ada')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/archives/41',
      expect.objectContaining({ cache: 'no-store' }),
    )
    const back = screen.getByRole('link', { name: 'Kembali ke pencarian' })
    expect(back).toHaveAttribute('href', '/app/search?q=jembatan&offset=10')
    expect(back.getAttribute('href')).not.toContain('secret-test-token')
    await user.click(back)
    expect(window.location.pathname + window.location.search).toBe(
      '/app/search?q=jembatan&offset=10',
    )
  })

  it('menandai field kosong tanpa mengarang lokasi atau hasil ekstraksi', async () => {
    renderDetail({
      detail: () =>
        Promise.resolve(
          json({
            data: {
              ...fullArchive,
              id: 42,
              status: 3,
              year: null,
              opd_name: null,
              classification_label: null,
              file_number: null,
              index_label: null,
              summary_raw: null,
              has_document: false,
              location: { block: null, rack: null, row: null, box_number: null },
              extraction: {
                spm_number: null,
                sp2d_number: null,
                document_date: null,
                amount_rp: null,
                party_name: null,
                spm_type: null,
              },
            },
          }),
        ),
    })
    expect(await screen.findByText('Ringkasan tidak tersedia')).toBeInTheDocument()
    expect(screen.getAllByText('Tidak tersedia').length).toBeGreaterThan(5)
    expect(screen.getByText(/Tahun tidak tersedia/)).toBeInTheDocument()
    expect(screen.getByText('Tidak ada')).toBeInTheDocument()
    expect(screen.queryByText(/masih dugaan/)).not.toBeInTheDocument()
  })

  it('membedakan ID tidak valid dan arsip yang tidak ditemukan', async () => {
    const invalid = renderDetail({ path: '/app/archives/0' })
    expect(await screen.findByText('ID arsip pada alamat tidak valid.')).toBeInTheDocument()
    expect(invalid.fetchMock).not.toHaveBeenCalledWith('/api/v1/archives/0', expect.anything())
    cleanup()
    renderDetail({
      detail: () => Promise.resolve(json({ error: { message: 'Arsip tidak ditemukan.' } }, 404)),
    })
    expect(
      await screen.findByText('Arsip ini tidak ditemukan dalam salinan data.'),
    ).toBeInTheDocument()
  })

  it('menampilkan loading, galat, dan dapat mencoba lagi', async () => {
    const user = userEvent.setup()
    let rejectFirst: (error: Error) => void = () => {}
    let calls = 0
    renderDetail({
      detail: () => {
        calls += 1
        if (calls === 1)
          return new Promise((_resolve, reject) => {
            rejectFirst = reject
          })
        return Promise.resolve(json({ data: fullArchive }))
      },
    })
    expect(await screen.findByRole('status', { name: 'Memuat detail arsip' })).toBeInTheDocument()
    rejectFirst(new Error('offline'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Detail arsip belum dapat dimuat.')
    await user.click(screen.getByRole('button', { name: 'Coba lagi' }))
    expect(await screen.findByText('SPM-41')).toBeInTheDocument()
  })

  it('mengalihkan ke login bila sesi API habis', async () => {
    renderDetail({
      detail: () => Promise.resolve(json({ error: { message: 'Sesi berakhir.' } }, 401)),
    })
    expect(
      await screen.findByRole('heading', { name: 'Masuk ke aplikasi arsip' }),
    ).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
  })
})
