import { z } from 'zod'
import { apiGet } from '@/lib/api/client'

const coverageItemSchema = z.object({
  field: z.string(),
  label: z.string(),
  filled: z.number().int(),
  missing: z.number().int(),
  fill_rate: z.number(),
})

const issueCategorySchema = z.object({
  issue_type: z.string(),
  field_name: z.string(),
  count: z.number().int(),
})

const qualityIssueItemSchema = z.object({
  id: z.number().int(),
  archive_id: z.number().int(),
  issue_type: z.string(),
  field_name: z.string(),
  raw_value: z.string().nullable(),
  detail: z.string().nullable(),
  year: z.number().int().nullable(),
  opd_name: z.string(),
  spm_type_code: z.string().nullable(),
  spm_confidence: z.string().nullable(),
  summary_preview: z.string(),
})

export const metadataQualitySchema = z.object({
  total_archives: z.number().int(),
  total_issues: z.number().int(),
  spm_confidence_summary: z.object({
    dugaan: z.number().int(),
    terkonfirmasi: z.number().int(),
    tanpa_kode: z.number().int(),
  }),
  metadata_coverage: z.array(coverageItemSchema),
  issue_categories: z.array(issueCategorySchema),
  filters: z.object({
    issue_types: z.array(z.string()),
    field_names: z.array(z.string()),
  }),
  issues: z.object({
    items: z.array(qualityIssueItemSchema),
    total: z.number().int(),
    page: z.number().int(),
    per_page: z.number().int(),
    pages: z.number().int(),
  }),
})

const qualityResponseSchema = z.object({ data: metadataQualitySchema })

export type MetadataCoverageItem = z.infer<typeof coverageItemSchema>
export type MetadataQualitySummary = z.infer<typeof metadataQualitySchema>

export interface QualityQueryParams {
  issueType?: string
  fieldName?: string
  spmConfidence?: string
  page?: number
  perPage?: number
}

export function fetchMetadataQuality(params?: QualityQueryParams): Promise<MetadataQualitySummary> {
  const search = new URLSearchParams()
  if (params?.issueType) search.set('issue_type', params.issueType)
  if (params?.fieldName) search.set('field_name', params.fieldName)
  if (params?.spmConfidence) search.set('spm_confidence', params.spmConfidence)
  if (params?.page !== undefined) search.set('page', String(params.page))
  if (params?.perPage !== undefined) search.set('per_page', String(params.perPage))
  const qs = search.toString()
  return apiGet(`/api/v1/research/quality${qs ? `?${qs}` : ''}`, qualityResponseSchema)
}
