import { z } from 'zod'
import { apiGet, apiMutate } from '@/lib/api/client'

export const duplicateDecisionSchema = z.enum(['duplikat', 'bukan_duplikat', 'perlu_cek'])

const archiveSideSchema = z.object({
  id: z.number().int(),
  year: z.number().int().nullable(),
  opd_name: z.string(),
  summary_raw: z.string(),
  spm_number: z.string().nullable(),
  sp2d_number: z.string().nullable(),
  document_date: z.string().nullable(),
  amount_rp: z.number().int().nullable(),
  party_name: z.string().nullable(),
  location: z.object({
    block: z.string().nullable(),
    rack: z.string().nullable(),
    row: z.string().nullable(),
    box: z.string().nullable(),
  }),
})

const historyEntrySchema = z.object({
  old_decision: z.string().nullable(),
  new_decision: z.string(),
  notes: z.string(),
  actor_username: z.string(),
  changed_at: z.string(),
})

const duplicateCandidateSchema = z.object({
  archive_a_id: z.number().int(),
  archive_b_id: z.number().int(),
  reason: z.string(),
  similarity: z.number(),
  decision: duplicateDecisionSchema.nullable(),
  notes: z.string(),
  reviewed_by: z.string().nullable(),
  reviewed_at: z.string().nullable(),
  history: z.array(historyEntrySchema),
  archive_a: archiveSideSchema,
  archive_b: archiveSideSchema,
})

const duplicateListSchema = z.object({
  summary: z.object({
    total_candidates: z.number().int(),
    unreviewed: z.number().int(),
    duplikat: z.number().int(),
    bukan_duplikat: z.number().int(),
    perlu_cek: z.number().int(),
  }),
  items: z.array(duplicateCandidateSchema),
  total: z.number().int(),
  page: z.number().int(),
  per_page: z.number().int(),
  pages: z.number().int(),
})

const savedDecisionSchema = z.object({
  archive_a_id: z.number().int(),
  archive_b_id: z.number().int(),
  decision: duplicateDecisionSchema,
  notes: z.string(),
  reviewed_by: z.string().nullable(),
  reviewed_at: z.string(),
})

export type DuplicateDecision = z.infer<typeof duplicateDecisionSchema>
export type DuplicateArchiveSide = z.infer<typeof archiveSideSchema>
export type DuplicateCandidate = z.infer<typeof duplicateCandidateSchema>
export type DuplicateCandidateList = z.infer<typeof duplicateListSchema>

export interface DuplicateQueryParams {
  reason?: string
  status?: string
  page?: number
  perPage?: number
}

export function fetchDuplicateCandidates(
  params?: DuplicateQueryParams,
): Promise<DuplicateCandidateList> {
  const search = new URLSearchParams()
  if (params?.reason) search.set('reason', params.reason)
  if (params?.status) search.set('status', params.status)
  if (params?.page !== undefined) search.set('page', String(params.page))
  if (params?.perPage !== undefined) search.set('per_page', String(params.perPage))
  const qs = search.toString()
  return apiGet(
    `/api/v1/research/duplicates${qs ? `?${qs}` : ''}`,
    z.object({ data: duplicateListSchema }),
  )
}

export function saveDuplicateDecision(
  archiveAId: number,
  archiveBId: number,
  decision: DuplicateDecision,
  notes: string,
  csrfToken: string,
) {
  return apiMutate(
    `/api/v1/research/duplicates/${archiveAId}/${archiveBId}`,
    'PUT',
    z.object({ data: savedDecisionSchema }),
    { csrfToken, body: { decision, notes } },
  )
}
