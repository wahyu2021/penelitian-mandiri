import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import App from '@/App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

function stubSession(role: 'admin' | 'petugas') {
  return Response.json({
    data: {
      authenticated: true,
      user: {
        id: role === 'admin' ? 1 : 2,
        username: role === 'admin' ? 'peneliti' : 'arsiparis',
        role,
      },
      csrf_token: 'csrf',
    },
  })
}

function sampleRun(split: 'test' | 'tuning', status: 'final' | 'pending' | 'draft') {
  return {
    available: true,
    status,
    status_reasons: ['Alasan status untuk pengujian.'],
    split,
    provenance: {
      commit_sha: 'abc1234567890',
      tree_clean: status !== 'draft',
      mode: status === 'draft' ? 'draft' : 'final',
      seed: 42,
      data_hash: '1'.repeat(64),
      testset_hash: '2'.repeat(64),
      extractor_version: 'v1.0.0',
      exported_at: '2026-11-23T14:00:00Z',
    },
    manifest: { valid: true, checked_files: 5, reason: 'Valid' },
    split_counts: {
      n_queries: 112,
      n_tuning_queries: 32,
      n_test_queries: 80,
      n_base_queries: 56,
      n_tuning_base_queries: 16,
      n_test_base_queries: 40,
      split_leakage_count: 0,
      leaked_base_ids: [],
    },
    agreement: null,
    method_summary: [
      {
        method: 'levenshtein',
        config: 'tuned',
        label: 'levenshtein (tuned)',
        n_queries: split === 'test' ? 80 : 32,
        mean_p5: split === 'test' ? 0.4125 : 0.55,
        mean_r10: 0.72,
        mrr_at_10: split === 'test' ? 0.6875 : 0.81,
        hit_at_5_rate: 0.85,
        hit_at_10_rate: 0.9,
        zero_result_rate: 0.05,
        mean_latency_ms: 42.3,
        median_latency_ms: 38.4,
        mean_unjudged_top10: 0.5,
      },
    ],
    tuning_best: [
      {
        matcher: 'levenshtein',
        summary_weight: 0.6,
        spm_weight: 0.2,
        party_weight: 0.2,
        mrr_at_10: 0.81,
        precision_at_5: 0.55,
        unjudged_top10: 4,
        grid_size: 66,
      },
    ],
    filters: {
      methods: ['levenshtein'],
      configs: ['tuned'],
      query_types: ['topik'],
      noise_types: ['tanpa_gangguan'],
      sources: ['sintetis'],
    },
    per_query: {
      items: [
        {
          query_id: split === 'test' ? 'Q001' : 'Q090',
          method: 'levenshtein',
          config: 'tuned',
          split,
          source: 'sintetis',
          query_type: 'topik',
          noise_type: 'tanpa_gangguan',
          n_relevant: 2,
          p5: 0.4,
          r10: 1.0,
          rr10: 1.0,
          hit5: 1,
          hit10: 1,
          zero_result: 0,
          latency_ms: 38.4,
          unjudged_in_top10: 0,
        },
      ],
      total: 1,
      page: 1,
      per_page: 25,
      pages: 1,
    },
  }
}

it('menampilkan run evaluasi, tabel alternatif grafik, pindah split, dan ekspor untuk admin', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url === '/api/v1/session') return stubSession('admin')
      if (url.startsWith('/api/v1/research/evaluation?split=test')) {
        return Response.json({ data: sampleRun('test', 'pending') })
      }
      if (url.startsWith('/api/v1/research/evaluation?split=tuning')) {
        return Response.json({ data: sampleRun('tuning', 'pending') })
      }
      throw new Error(`Unexpected URL: ${url}`)
    }),
  )

  window.history.replaceState(null, '', '/app/research/evaluation')
  const user = userEvent.setup()
  render(<App />)

  expect(
    await screen.findByText('Menunggu kesepakatan (PM-19)', {}, { timeout: 8000 }),
  ).toBeInTheDocument()
  expect(screen.getByText('Manifest SHA-256 valid')).toBeInTheDocument()
  expect(screen.getByText('Tuning/test terpisah')).toBeInTheDocument()
  // Tabel alternatif aksesibel untuk grafik
  expect(screen.getByText('Tabel metrik lengkap per metode')).toBeInTheDocument()
  expect(screen.getByText('0,6875')).toBeInTheDocument()
  expect(screen.getByText('Q001')).toBeInTheDocument()

  expect(screen.getByRole('link', { name: /Ekspor CSV/i })).toHaveAttribute(
    'href',
    '/api/v1/research/evaluation/export?split=test&format=csv',
  )
  expect(screen.getByRole('link', { name: /Ekspor JSON/i })).toHaveAttribute(
    'href',
    '/api/v1/research/evaluation/export?split=test&format=json',
  )

  await user.click(screen.getByRole('button', { name: 'Split Tuning' }))
  expect((await screen.findAllByText('0,8100')).length).toBeGreaterThanOrEqual(1)
  expect(screen.getByText('Q090')).toBeInTheDocument()
}, 10000)

it('menampilkan empty state saat bundle belum tersedia dan menolak petugas 403', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url === '/api/v1/session') return stubSession('admin')
      if (url.startsWith('/api/v1/research/evaluation')) {
        return Response.json({
          data: {
            available: false,
            status: 'empty',
            status_reasons: ['Belum ada artefak run evaluasi pada direktori bundle.'],
            split: 'test',
            provenance: null,
            manifest: { valid: false, checked_files: 0, reason: 'Kosong' },
            split_counts: {
              n_queries: 0,
              n_tuning_queries: 0,
              n_test_queries: 0,
              n_base_queries: 0,
              n_tuning_base_queries: 0,
              n_test_base_queries: 0,
              split_leakage_count: 0,
              leaked_base_ids: [],
            },
            agreement: null,
            method_summary: [],
            tuning_best: [],
            filters: { methods: [], configs: [], query_types: [], noise_types: [], sources: [] },
            per_query: { items: [], total: 0, page: 1, per_page: 25, pages: 1 },
          },
        })
      }
      throw new Error(`Unexpected URL: ${url}`)
    }),
  )

  window.history.replaceState(null, '', '/app/research/evaluation')
  const app = render(<App />)
  expect(
    await screen.findByText(
      'Belum ada artefak run evaluasi pada direktori bundle.',
      {},
      { timeout: 4000 },
    ),
  ).toBeInTheDocument()
  app.unmount()

  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url === '/api/v1/session') return stubSession('petugas')
      throw new Error(`Unexpected URL: ${url}`)
    }),
  )
  window.history.replaceState(null, '', '/app/research/evaluation')
  render(<App />)
  expect(
    await screen.findByText('Hasil evaluasi dan bukti run hanya tersedia untuk admin.'),
  ).toBeInTheDocument()
})
