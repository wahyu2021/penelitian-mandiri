import { z } from 'zod'
import { readResponse } from '@/lib/api/session'

const reviewer = z.object({
  slot: z.union([z.literal(1), z.literal(2)]),
  user_id: z.number(),
  username: z.string(),
  submitted_at: z.string().nullable(),
  total: z.number(),
  rated: z.number(),
})
const adminOverview = z.object({
  available_versions: z.array(z.string()),
  accounts: z.array(
    z.object({ id: z.number(), username: z.string(), role: z.enum(['admin', 'petugas']) }),
  ),
  reviews: z.array(
    z.object({ version: z.string(), sample_rows: z.number(), reviewers: z.array(reviewer) }),
  ),
})
export const relevanceAnswerSchema = z.object({
  is_relevant: z.union([z.literal(0), z.literal(1)]).nullable(),
  ragu: z.boolean(),
  notes: z.string(),
  revision: z.number().int(),
})
export const relevanceItemStateSchema = z.object({
  item: relevanceAnswerSchema.extend({
    id: z.number(),
    base_query_text: z.string(),
    query_type: z.string(),
    summary_raw: z.string(),
  }),
  index: z.number().int(),
  total: z.number().int(),
  rated: z.number().int(),
  submitted_at: z.string().nullable(),
})
const answer = relevanceAnswerSchema
const itemState = relevanceItemStateSchema
const migration = z.object({
  inserted: z.number(),
  preserved: z.number(),
  matched_rows: z.number(),
  outside_rows: z.number(),
})

export type RelevanceAdmin = z.infer<typeof adminOverview>
export type RelevanceState = z.infer<typeof itemState>
export type Answer = z.infer<typeof answer>

const adminBase = '/api/v1/relevance-admin'
const reviewBase = '/api/v1/relevance-reviews'
const adminVersion = (version: string) => `${adminBase}/${encodeURIComponent(version)}`
const reviewVersion = (version: string) => `${reviewBase}/${encodeURIComponent(version)}`

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { credentials: 'same-origin', cache: 'no-store', ...init })
  return z.object({ data: schema }).parse(await readResponse(response)).data
}

export const getRelevanceAdmin = () => request(adminBase, adminOverview)
export const getReviewAssignments = () =>
  request(reviewBase, z.array(z.object({ version: z.string() })))
export const getReviewItem = (version: string, index: number | null) =>
  request(reviewVersion(version) + (index === null ? '' : `?index=${index}`), itemState)

export const createReview = (
  version: string,
  first: string,
  second: string,
  file: File,
  csrf: string,
) =>
  request(
    `${adminVersion(version)}?${new URLSearchParams({ first, second })}`,
    z.object({
      version: z.string(),
      pairs: z.number(),
      sample_rows: z.number(),
    }),
    { method: 'POST', body: file, headers: { 'Content-Type': 'text/csv', 'X-CSRF-Token': csrf } },
  )

export const migrateReview = (version: string, slot: number, file: File, csrf: string) =>
  request(`${adminVersion(version)}/${slot}/migration`, migration, {
    method: 'POST',
    body: file,
    headers: { 'Content-Type': 'text/csv', 'X-CSRF-Token': csrf },
  })

export const relevanceExportUrl = (version: string, slot: number) =>
  `${adminVersion(version)}/${slot}/export`

export const saveReviewAnswer = (version: string, id: number, value: Answer, csrf: string) =>
  request(
    `${reviewVersion(version)}/${id}`,
    z.object({ revision: z.number(), rated: z.number(), total: z.number() }),
    {
      method: 'PUT',
      body: JSON.stringify(value),
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    },
  )

export const submitReview = (version: string, csrf: string) =>
  request(`${reviewVersion(version)}/submit`, z.object({ submitted_at: z.string() }), {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrf },
  })
