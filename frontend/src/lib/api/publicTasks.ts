import { z } from 'zod'
import { apiGet, apiMutate } from '@/lib/api/client'
import { auditStateDataSchema, type AuditField, type Verdict } from '@/lib/api/extractionAudit'
import { relevanceItemStateSchema, type Answer } from '@/lib/api/relevance'
import { readResponse } from '@/lib/api/session'

export type TaskKind = 'relevance' | 'extraction_audit'

const taskLinkSchema = z.object({
  id: z.number().int(),
  task_kind: z.enum(['relevance', 'extraction_audit']),
  token_preview: z.string(),
  target_user_id: z.number().int(),
  target_username: z.string(),
  target_version: z.string().nullable(),
  target_slot: z.union([z.literal(1), z.literal(2)]).nullable(),
  label: z.string(),
  lock_single_device: z.boolean(),
  status: z.enum(['unopened', 'claimed', 'submitted', 'revoked']),
  claimed_at: z.string().nullable(),
  submitted_at: z.string().nullable(),
  revoked_at: z.string().nullable(),
  created_at: z.string(),
})

const createdTaskLinkSchema = z.object({
  id: z.number().int(),
  task_kind: z.enum(['relevance', 'extraction_audit']),
  token: z.string(),
  token_preview: z.string(),
  public_path: z.string(),
  target_user_id: z.number().int(),
  target_username: z.string(),
  target_version: z.string().nullable(),
  target_slot: z.union([z.literal(1), z.literal(2)]).nullable(),
  label: z.string(),
  lock_single_device: z.boolean(),
  status: z.string(),
  created_at: z.string(),
})

const publicLinkSummarySchema = z.object({
  label: z.string(),
  target_username: z.string(),
  target_version: z.string().nullable(),
  target_slot: z.union([z.literal(1), z.literal(2)]).nullable(),
  lock_single_device: z.boolean(),
  submitted_at: z.string().nullable(),
})

const publicRelevanceResponseSchema = z.object({
  link: publicLinkSummarySchema,
  review: relevanceItemStateSchema,
})

const publicAuditResponseSchema = z.object({
  link: publicLinkSummarySchema,
  audit: auditStateDataSchema,
})

export type TaskLinkItem = z.infer<typeof taskLinkSchema>
export type CreatedTaskLink = z.infer<typeof createdTaskLinkSchema>
export type PublicRelevanceData = z.infer<typeof publicRelevanceResponseSchema>
export type PublicAuditData = z.infer<typeof publicAuditResponseSchema>

async function publicRequest<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {
    credentials: 'same-origin',
    cache: 'no-store',
    ...init,
  })
  return z.object({ data: schema }).parse(await readResponse(response)).data
}

export function fetchTaskLinks(filters?: {
  task_kind?: TaskKind
  version?: string
}): Promise<TaskLinkItem[]> {
  const params = new URLSearchParams()
  if (filters?.task_kind) params.set('task_kind', filters.task_kind)
  if (filters?.version) params.set('version', filters.version)
  const qs = params.toString()
  return apiGet(
    `/api/v1/research/task-links${qs ? `?${qs}` : ''}`,
    z.object({ data: z.array(taskLinkSchema) }),
  )
}

export function createTaskLink(
  payload: {
    task_kind: TaskKind
    version?: string
    slot?: 1 | 2
    user_id?: number
    label?: string
    lock_single_device?: boolean
  },
  csrfToken: string,
): Promise<CreatedTaskLink> {
  return apiMutate(
    '/api/v1/research/task-links',
    'POST',
    z.object({ data: createdTaskLinkSchema }),
    { csrfToken, body: payload },
  )
}

export function resetTaskLinkDevice(linkId: number, csrfToken: string) {
  return apiMutate(
    `/api/v1/research/task-links/${linkId}/reset-device`,
    'POST',
    z.object({ data: z.object({ id: z.number(), reset: z.boolean() }) }),
    { csrfToken },
  )
}

export function revokeTaskLink(linkId: number, csrfToken: string) {
  return apiMutate(
    `/api/v1/research/task-links/${linkId}/revoke`,
    'POST',
    z.object({ data: z.object({ id: z.number(), revoked_at: z.string() }) }),
    { csrfToken },
  )
}

export function adminAuditExportUrl(userId: number): string {
  return `/api/v1/extraction-audit/reviewers/${userId}/export`
}

export function fetchPublicRelevance(
  token: string,
  index: number | null,
): Promise<PublicRelevanceData> {
  const suffix = index === null ? '' : `?index=${index}`
  return publicRequest(
    `/api/v1/public/tasks/${encodeURIComponent(token)}/relevance${suffix}`,
    publicRelevanceResponseSchema,
  )
}

export function savePublicRelevanceAnswer(token: string, pairId: number, value: Answer) {
  return publicRequest(
    `/api/v1/public/tasks/${encodeURIComponent(token)}/relevance/${pairId}`,
    z.object({ revision: z.number(), rated: z.number(), total: z.number() }),
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(value),
    },
  )
}

export function submitPublicRelevance(token: string) {
  return publicRequest(
    `/api/v1/public/tasks/${encodeURIComponent(token)}/relevance/submit`,
    z.object({ submitted_at: z.string() }),
    { method: 'POST' },
  )
}

export function fetchPublicAudit(token: string, index: number): Promise<PublicAuditData> {
  return publicRequest(
    `/api/v1/public/tasks/${encodeURIComponent(token)}/audit?index=${index}`,
    publicAuditResponseSchema,
  )
}

export async function savePublicAuditField(
  token: string,
  archiveId: number,
  field: AuditField,
  verdict: Verdict | null,
  note: string,
  fingerprint: string,
): Promise<void> {
  await publicRequest(
    `/api/v1/public/tasks/${encodeURIComponent(token)}/audit/${archiveId}/fields/${field}`,
    z.object({ saved: z.boolean() }),
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ verdict, note, fingerprint }),
    },
  )
}

export function submitPublicAudit(token: string) {
  return publicRequest(
    `/api/v1/public/tasks/${encodeURIComponent(token)}/audit/submit`,
    z.object({ submitted_at: z.string() }),
    { method: 'POST' },
  )
}
