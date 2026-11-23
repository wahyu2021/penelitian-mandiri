import { z } from 'zod'
import { readResponse } from '@/lib/api/session'

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

export type AuditState = z.infer<typeof stateSchema>['data']
export type Reviewer = z.infer<typeof reviewerSchema>
export type SpmType = z.infer<typeof spmTypeSchema>

export async function getAuditState(index: number): Promise<AuditState> {
  const response = await fetch(`/api/v1/extraction-audit?index=${index}`, {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return stateSchema.parse(await readResponse(response)).data
}

export async function saveAuditField(
  archiveId: number,
  field: AuditField,
  verdict: Verdict | null,
  note: string,
  fingerprint: string,
  csrfToken: string,
): Promise<void> {
  const response = await fetch(`/api/v1/extraction-audit/${archiveId}/fields/${field}`, {
    method: 'PATCH',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ verdict, note, fingerprint }),
  })
  await readResponse(response)
}

export async function getAuditReviewers(): Promise<Reviewer[]> {
  const response = await fetch('/api/v1/extraction-audit/reviewers', {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return reviewersSchema.parse(await readResponse(response)).data
}

export async function setAuditReviewer(
  id: number,
  assigned: boolean,
  csrfToken: string,
): Promise<void> {
  const response = await fetch(`/api/v1/extraction-audit/reviewers/${id}`, {
    method: assigned ? 'PUT' : 'DELETE',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'X-CSRF-Token': csrfToken },
  })
  await readResponse(response)
}

export async function getSpmTypes(): Promise<SpmType[]> {
  const response = await fetch('/api/v1/spm-types', {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return spmTypesSchema.parse(await readResponse(response)).data
}

export async function confirmSpmType(
  code: string,
  label: string,
  sourceNote: string,
  csrfToken: string,
): Promise<void> {
  const response = await fetch(`/api/v1/spm-types/${encodeURIComponent(code)}/confirm`, {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ label, source_note: sourceNote }),
  })
  await readResponse(response)
}
