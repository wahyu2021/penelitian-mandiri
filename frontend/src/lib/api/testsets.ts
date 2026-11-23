import { z } from 'zod'
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

export type TestsetSummary = z.infer<typeof summary>
export type TestsetDetail = z.infer<typeof detail>

const base = '/api/v1/testsets'
const requestOptions = { credentials: 'same-origin', cache: 'no-store' } as const
const versionUrl = (version: string) => `${base}/${encodeURIComponent(version)}`

export const testsetExportUrl = (version: string) => `${versionUrl(version)}/export`

export async function getTestsets() {
  const response = await fetch(base, requestOptions)
  return z.object({ data: z.array(summary) }).parse(await readResponse(response)).data
}

export async function getTestset(version: string) {
  const response = await fetch(versionUrl(version), requestOptions)
  return z.object({ data: detail }).parse(await readResponse(response)).data
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
  return z.object({ data: summary }).parse(await readResponse(response)).data
}

export async function lockTestset(draft: TestsetSummary, csrf: string) {
  const response = await fetch(`${versionUrl(draft.version)}/lock`, {
    ...requestOptions,
    method: 'POST',
    headers: { 'X-CSRF-Token': csrf, 'If-Match': `"${draft.content_sha256}"` },
  })
  return z.object({ data: summary }).parse(await readResponse(response)).data
}
