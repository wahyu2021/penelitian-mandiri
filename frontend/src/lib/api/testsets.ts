import { z } from 'zod'
import { apiGet } from '@/lib/api/client'
import { readResponse } from '@/lib/api/session'

const summary = z.object({
  version: z.string(),
  content_sha256: z.string(),
  locked_at: z.string().nullable(),
  locked_by: z.number().int().nullable(),
  updated_at: z.string(),
  n_queries: z.number().int(),
  n_tuning: z.number().int(),
  n_test: z.number().int(),
  n_base_queries: z.number().int(),
  n_tuning_base_queries: z.number().int(),
  n_test_base_queries: z.number().int(),
  sources: z.object({ sintetis: z.number().int(), arsiparis: z.number().int() }),
})
const detail = summary.extend({
  queries: z.array(
    z.object({
      query_id: z.string(),
      base_query_id: z.string(),
      query_text: z.string(),
      query_type: z.string(),
      noise_type: z.string(),
      source: z.enum(['sintetis', 'arsiparis']),
      split: z.enum(['tuning', 'test']),
    }),
  ),
})
const summaryListResponseSchema = z.object({ data: z.array(summary) })
const detailResponseSchema = z.object({ data: detail })
const summaryResponseSchema = z.object({ data: summary })

export type TestsetSummary = z.infer<typeof summary>
export type TestsetDetail = z.infer<typeof detail>

const base = '/api/v1/testsets'
const requestOptions = { credentials: 'same-origin', cache: 'no-store' } as const
const versionUrl = (version: string) => `${base}/${encodeURIComponent(version)}`

export const testsetExportUrl = (version: string) => `${versionUrl(version)}/export`

export function getTestsets() {
  return apiGet(base, summaryListResponseSchema)
}

export function getTestset(version: string) {
  return apiGet(versionUrl(version), detailResponseSchema)
}

export async function saveTestset(file: File, csrf: string, draft?: TestsetSummary) {
  const headers = new Headers({ 'Content-Type': 'application/json', 'X-CSRF-Token': csrf })
  if (draft) headers.set('If-Match', `"${draft.content_sha256}"`)
  const response = await fetch(draft ? versionUrl(draft.version) : base, {
    ...requestOptions,
    method: draft ? 'PUT' : 'POST',
    headers,
    body: file,
  })
  return summaryResponseSchema.parse(await readResponse(response)).data
}

export async function lockTestset(draft: TestsetSummary, csrf: string) {
  const response = await fetch(`${versionUrl(draft.version)}/lock`, {
    ...requestOptions,
    method: 'POST',
    headers: { 'X-CSRF-Token': csrf, 'If-Match': `"${draft.content_sha256}"` },
  })
  return summaryResponseSchema.parse(await readResponse(response)).data
}
