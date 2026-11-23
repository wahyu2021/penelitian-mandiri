import { z } from 'zod'
import { apiGet, apiMutate } from '@/lib/api/client'

export const fields = ['spm', 'sp2d', 'date', 'amount', 'party'] as const
export type AuditField = (typeof fields)[number]
export const verdicts = ['benar', 'salah', 'terlewat', 'tidak_ada_di_teks'] as const
export type Verdict = (typeof verdicts)[number]

const judgment = z.object({ verdict: z.enum(verdicts).nullable(), note: z.string() })
const fieldResult = z.object({
  rated: z.number(),
  total: z.number(),
  status: z.string(),
  metrics: z
    .object({
      n_benar: z.number(),
      n_salah: z.number(),
      n_terlewat: z.number(),
      n_tidak_ada_di_teks: z.number(),
      ketepatan: z.number().nullable(),
      keterambilan: z.number().nullable(),
    })
    .nullable(),
})
const stateSchema = z.object({
  data: z.object({
    fingerprint: z.string(),
    extractor_version: z.string(),
    source_filename: z.string(),
    index: z.number(),
    total_samples: z.number(),
    completed_samples: z.number(),
    completed_cells: z.number(),
    total_cells: z.number(),
    final: z.boolean(),
    sample: z.object({
      sample_id: z.number(),
      archive_id: z.number(),
      archive_status: z.string(),
      summary_raw: z.string(),
      extracted_spm: z.string(),
      extracted_sp2d: z.string(),
      extracted_date: z.string(),
      extracted_amount: z.string(),
      extracted_party: z.string(),
    }),
    judgments: z.record(z.string(), judgment),
    results: z.record(z.string(), fieldResult),
  }),
})
const reviewerSchema = z.object({
  id: z.number(),
  username: z.string(),
  role: z.string(),
  is_active: z.number(),
  assigned_at: z.string().nullable(),
  assigned_by: z.number().nullable(),
})
const reviewersSchema = z.object({ data: z.array(reviewerSchema) })
const spmTypeSchema = z.object({
  code: z.string(),
  label: z.string().nullable(),
  confidence: z.string(),
  source_note: z.string().nullable(),
  confirmed_by: z.string().nullable(),
  confirmed_at: z.string().nullable(),
  archive_count: z.number(),
})
const spmTypesSchema = z.object({ data: z.array(spmTypeSchema) })
const voidResponseSchema = z.object({ data: z.unknown() })

export type AuditState = z.infer<typeof stateSchema>['data']
export type Reviewer = z.infer<typeof reviewerSchema>
export type SpmType = z.infer<typeof spmTypeSchema>

export function getAuditState(index: number): Promise<AuditState> {
  return apiGet(`/api/v1/extraction-audit?index=${index}`, stateSchema)
}

export async function saveAuditField(
  archiveId: number,
  field: AuditField,
  verdict: Verdict | null,
  note: string,
  fingerprint: string,
  csrfToken: string,
): Promise<void> {
  await apiMutate(
    `/api/v1/extraction-audit/${archiveId}/fields/${field}`,
    'PATCH',
    voidResponseSchema,
    {
      csrfToken,
      body: { verdict, note, fingerprint },
    },
  )
}

export function getAuditReviewers(): Promise<Reviewer[]> {
  return apiGet('/api/v1/extraction-audit/reviewers', reviewersSchema)
}

export async function setAuditReviewer(
  id: number,
  assigned: boolean,
  csrfToken: string,
): Promise<void> {
  await apiMutate(
    `/api/v1/extraction-audit/reviewers/${id}`,
    assigned ? 'PUT' : 'DELETE',
    voidResponseSchema,
    { csrfToken },
  )
}

export function getSpmTypes(): Promise<SpmType[]> {
  return apiGet('/api/v1/spm-types', spmTypesSchema)
}

export async function confirmSpmType(
  code: string,
  label: string,
  sourceNote: string,
  csrfToken: string,
): Promise<void> {
  await apiMutate(
    `/api/v1/spm-types/${encodeURIComponent(code)}/confirm`,
    'POST',
    voidResponseSchema,
    {
      csrfToken,
      body: { label, source_note: sourceNote },
    },
  )
}
