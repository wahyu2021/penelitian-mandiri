import { z } from 'zod'
import { apiGet } from '@/lib/api/client'

export const evaluationStatusSchema = z.enum(['empty', 'draft', 'pending', 'final'])
export const evaluationSplitSchema = z.enum(['test', 'tuning'])

const provenanceSchema = z.object({
  commit_sha: z.string(),
  tree_clean: z.boolean(),
  mode: z.string(),
  seed: z.number().nullable(),
  data_hash: z.string(),
  testset_hash: z.string(),
  extractor_version: z.string(),
  exported_at: z.string(),
})

const manifestSchema = z.object({
  valid: z.boolean(),
  checked_files: z.number().int(),
  reason: z.string(),
})

const splitCountsSchema = z.object({
  n_queries: z.number().int(),
  n_tuning_queries: z.number().int(),
  n_test_queries: z.number().int(),
  n_base_queries: z.number().int(),
  n_tuning_base_queries: z.number().int(),
  n_test_base_queries: z.number().int(),
  split_leakage_count: z.number().int(),
  leaked_base_ids: z.array(z.string()),
})

const methodSummarySchema = z.object({
  method: z.string(),
  config: z.string(),
  label: z.string(),
  n_queries: z.number().int(),
  mean_p5: z.number(),
  mean_r10: z.number(),
  mrr_at_10: z.number(),
  hit_at_5_rate: z.number(),
  hit_at_10_rate: z.number(),
  zero_result_rate: z.number(),
  mean_latency_ms: z.number(),
  median_latency_ms: z.number(),
  mean_unjudged_top10: z.number(),
})

const tuningBestSchema = z.object({
  matcher: z.string(),
  summary_weight: z.number(),
  spm_weight: z.number(),
  party_weight: z.number(),
  mrr_at_10: z.number(),
  precision_at_5: z.number(),
  unjudged_top10: z.number().int(),
  grid_size: z.number().int(),
})

const perQueryItemSchema = z.object({
  query_id: z.string(),
  method: z.string(),
  config: z.string(),
  split: z.string(),
  source: z.string(),
  query_type: z.string(),
  noise_type: z.string(),
  n_relevant: z.number().int(),
  p5: z.number(),
  r10: z.number(),
  rr10: z.number(),
  hit5: z.number().int(),
  hit10: z.number().int(),
  zero_result: z.number().int(),
  latency_ms: z.number(),
  unjudged_in_top10: z.number().int(),
})

export const evaluationRunSchema = z.object({
  available: z.boolean(),
  status: evaluationStatusSchema,
  status_reasons: z.array(z.string()),
  split: evaluationSplitSchema,
  provenance: provenanceSchema.nullable(),
  manifest: manifestSchema,
  split_counts: splitCountsSchema,
  agreement: z.record(z.string(), z.unknown()).nullable(),
  method_summary: z.array(methodSummarySchema),
  tuning_best: z.array(tuningBestSchema),
  filters: z.object({
    methods: z.array(z.string()),
    configs: z.array(z.string()),
    query_types: z.array(z.string()),
    noise_types: z.array(z.string()),
    sources: z.array(z.string()),
  }),
  per_query: z.object({
    items: z.array(perQueryItemSchema),
    total: z.number().int(),
    page: z.number().int(),
    per_page: z.number().int(),
    pages: z.number().int(),
  }),
})

const evaluationResponseSchema = z.object({ data: evaluationRunSchema })

export type EvaluationStatus = z.infer<typeof evaluationStatusSchema>
export type EvaluationSplit = z.infer<typeof evaluationSplitSchema>
export type MethodSummaryItem = z.infer<typeof methodSummarySchema>
export type TuningBestItem = z.infer<typeof tuningBestSchema>
export type EvaluationRun = z.infer<typeof evaluationRunSchema>

export interface EvaluationQueryParams {
  split: EvaluationSplit
  method?: string
  config?: string
  queryType?: string
  noiseType?: string
  source?: string
  page?: number
  perPage?: number
}

function buildSearchParams(params: EvaluationQueryParams): string {
  const search = new URLSearchParams()
  search.set('split', params.split)
  if (params.method) search.set('method', params.method)
  if (params.config) search.set('config', params.config)
  if (params.queryType) search.set('query_type', params.queryType)
  if (params.noiseType) search.set('noise_type', params.noiseType)
  if (params.source) search.set('source', params.source)
  if (params.page !== undefined) search.set('page', String(params.page))
  if (params.perPage !== undefined) search.set('per_page', String(params.perPage))
  return `?${search.toString()}`
}

export function fetchEvaluationRun(params: EvaluationQueryParams): Promise<EvaluationRun> {
  return apiGet(`/api/v1/research/evaluation${buildSearchParams(params)}`, evaluationResponseSchema)
}

export function evaluationExportUrl(split: EvaluationSplit, format: 'json' | 'csv'): string {
  return `/api/v1/research/evaluation/export?${new URLSearchParams({ split, format }).toString()}`
}
