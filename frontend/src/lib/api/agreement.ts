import { z } from 'zod'
import { apiGet } from '@/lib/api/client'

export const agreementStatusSchema = z.enum(['pending', 'complete', 'complete_kappa_undefined'])

const reviewerProgressSchema = z.object({
  slot: z.union([z.literal(1), z.literal(2)]),
  user_id: z.number().int(),
  username: z.string(),
  submitted_at: z.string().nullable(),
  rated: z.number().int(),
  total: z.number().int(),
})

const confusionMatrixSchema = z.object({
  both_relevant: z.number().int(),
  rater1_only_relevant: z.number().int(),
  rater2_only_relevant: z.number().int(),
  both_irrelevant: z.number().int(),
})

const queryTypeAgreementSchema = z.object({
  n_samples: z.number().int(),
  n_agreed: z.number().int(),
  agreement: z.number(),
})

export const relevanceAgreementSchema = z.object({
  version: z.string(),
  created_at: z.string(),
  n_sample_rows: z.number().int(),
  reviewers: z.array(reviewerProgressSchema),
  status: agreementStatusSchema,
  n_total: z.number().int(),
  n_paired: z.number().int(),
  n_agreed: z.number().int().nullable(),
  percentage_agreement: z.number().nullable(),
  relevant_class_agreement: z.number().nullable(),
  cohen_kappa: z.number().nullable(),
  confusion_matrix: confusionMatrixSchema.nullable(),
  agreement_by_query_type: z.record(z.string(), queryTypeAgreementSchema),
  limitations: z.array(z.string()),
})

const auditReviewerSchema = z.object({
  user_id: z.number().int(),
  username: z.string(),
  role: z.string(),
  is_assigned: z.boolean(),
  rated_cells: z.number().int(),
})

const auditSummaryCoreSchema = z.object({
  status: agreementStatusSchema,
  n_total: z.number().int(),
  n_paired: z.number().int(),
  n_agreed: z.number().int().nullable(),
  percentage_agreement: z.number().nullable(),
  cohen_kappa: z.number().nullable(),
  limitations: z.array(z.string()),
})

const auditFieldSummarySchema = auditSummaryCoreSchema.extend({
  field: z.string(),
})

export const auditAgreementSchema = z.object({
  status: agreementStatusSchema,
  dataset: z
    .object({
      fingerprint: z.string(),
      sample_count: z.number().int(),
      source_filename: z.string(),
      created_at: z.string(),
      total_cells: z.number().int(),
    })
    .nullable(),
  reviewers: z.array(auditReviewerSchema),
  selected_raters: z.array(auditReviewerSchema),
  overall: auditSummaryCoreSchema.nullable(),
  fields: z.array(auditFieldSummarySchema),
  limitations: z.array(z.string()),
})

export const agreementReportSchema = z.object({
  generated_at: z.string(),
  relevance: z.array(relevanceAgreementSchema),
  audit: auditAgreementSchema,
})

const agreementResponseSchema = z.object({ data: agreementReportSchema })

export type AgreementStatus = z.infer<typeof agreementStatusSchema>
export type RelevanceAgreement = z.infer<typeof relevanceAgreementSchema>
export type AuditAgreement = z.infer<typeof auditAgreementSchema>
export type AgreementReport = z.infer<typeof agreementReportSchema>

export interface AgreementQueryParams {
  version?: string
  auditRater1?: number
  auditRater2?: number
}

function buildSearchParams(params?: AgreementQueryParams): string {
  const search = new URLSearchParams()
  if (params?.version) search.set('version', params.version)
  if (params?.auditRater1 !== undefined && params?.auditRater2 !== undefined) {
    search.set('audit_rater1', String(params.auditRater1))
    search.set('audit_rater2', String(params.auditRater2))
  }
  const encoded = search.toString()
  return encoded ? `?${encoded}` : ''
}

export function fetchAgreementSummary(params?: AgreementQueryParams): Promise<AgreementReport> {
  return apiGet(`/api/v1/research/agreement${buildSearchParams(params)}`, agreementResponseSchema)
}

export function agreementExportUrl(params?: AgreementQueryParams): string {
  return `/api/v1/research/agreement/export${buildSearchParams(params)}`
}
