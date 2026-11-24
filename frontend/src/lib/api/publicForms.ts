import { z } from 'zod'
import { apiGet, apiMutate } from '@/lib/api/client'
import { readResponse } from '@/lib/api/session'

export const questionSchema = z.object({
  id: z.string(),
  type: z.enum(['scale', 'choice', 'text', 'textarea']),
  label: z.string(),
  required: z.boolean().default(true),
  options: z.array(z.string()).optional(),
})

const formSummarySchema = z.object({
  id: z.number().int(),
  slug: z.string(),
  title: z.string(),
  description: z.string(),
  form_kind: z.enum(['sus', 'custom']),
  created_at: z.string(),
  total_links: z.number().int(),
  total_responses: z.number().int(),
})

const formLinkSchema = z.object({
  id: z.number().int(),
  token_preview: z.string(),
  participant_code: z.string(),
  participant_role: z.enum(['admin', 'petugas']),
  lock_single_device: z.boolean(),
  status: z.enum(['unopened', 'claimed', 'submitted', 'revoked']),
  claimed_at: z.string().nullable(),
  submitted_at: z.string().nullable(),
  revoked_at: z.string().nullable(),
  created_at: z.string(),
})

const formResponseRowSchema = z.object({
  id: z.number().int(),
  link_id: z.number().int(),
  participant_code: z.string(),
  participant_role: z.string(),
  answers: z.record(z.string(), z.unknown()),
  sus_score: z.number().nullable(),
  submitted_at: z.string(),
})

const susSummarySchema = z
  .object({
    status: z.string(),
    n_respondents: z.number().int(),
    mean_sus: z.number().nullable(),
    median_sus: z.number().nullable(),
    min_sus: z.number().nullable(),
    max_sus: z.number().nullable(),
    std_sus: z.number().nullable(),
    limitations: z.array(z.string()),
  })
  .nullable()

const formDetailSchema = z.object({
  form: z.object({
    id: z.number().int(),
    slug: z.string(),
    title: z.string(),
    description: z.string(),
    form_kind: z.enum(['sus', 'custom']),
    questions: z.array(questionSchema),
    created_at: z.string(),
  }),
  links: z.array(formLinkSchema),
  responses: z.array(formResponseRowSchema),
  sus_summary: susSummarySchema,
})

const createdFormSchema = z.object({
  id: z.number().int(),
  slug: z.string(),
  title: z.string(),
  description: z.string(),
  form_kind: z.enum(['sus', 'custom']),
  questions: z.array(questionSchema),
  created_at: z.string(),
})

const createdLinkSchema = z.object({
  id: z.number().int(),
  form_id: z.number().int(),
  token: z.string(),
  token_preview: z.string(),
  public_path: z.string(),
  participant_code: z.string(),
  participant_role: z.enum(['admin', 'petugas']),
  lock_single_device: z.boolean(),
  status: z.string(),
  created_at: z.string(),
})

const publicFormStateSchema = z.object({
  already_submitted: z.boolean(),
  submitted_at: z.string().nullable(),
  participant_code: z.string(),
  participant_role: z.string(),
  lock_single_device: z.boolean(),
  form: z.object({
    id: z.number().int(),
    title: z.string(),
    description: z.string(),
    form_kind: z.enum(['sus', 'custom']),
    questions: z.array(questionSchema),
  }),
})

const publicSubmitResultSchema = z.object({
  submitted: z.boolean(),
  submitted_at: z.string(),
  participant_code: z.string(),
  sus_score: z.number().nullable(),
})

export type SurveyQuestion = z.infer<typeof questionSchema>
export type FormSummary = z.infer<typeof formSummarySchema>
export type FormDetail = z.infer<typeof formDetailSchema>
export type CreatedPublicLink = z.infer<typeof createdLinkSchema>
export type PublicFormState = z.infer<typeof publicFormStateSchema>
export type PublicSubmitResult = z.infer<typeof publicSubmitResultSchema>

export function fetchForms(): Promise<FormSummary[]> {
  return apiGet('/api/v1/research/forms', z.object({ data: z.array(formSummarySchema) }))
}

export function fetchFormDetail(formId: number): Promise<FormDetail> {
  return apiGet(`/api/v1/research/forms/${formId}`, z.object({ data: formDetailSchema }))
}

export function createSurveyForm(
  payload: {
    title: string
    description: string
    form_kind: 'sus' | 'custom'
    questions?: Array<{
      id: string
      type: 'scale' | 'choice' | 'text' | 'textarea'
      label: string
      required: boolean
      options?: string[]
    }>
  },
  csrfToken: string,
) {
  return apiMutate('/api/v1/research/forms', 'POST', z.object({ data: createdFormSchema }), {
    csrfToken,
    body: payload,
  })
}

export function generatePublicLink(
  formId: number,
  payload: {
    participant_code: string
    participant_role: 'petugas' | 'admin'
    lock_single_device: boolean
  },
  csrfToken: string,
): Promise<CreatedPublicLink> {
  return apiMutate(
    `/api/v1/research/forms/${formId}/links`,
    'POST',
    z.object({ data: createdLinkSchema }),
    { csrfToken, body: payload },
  )
}

export function resetLinkDevice(linkId: number, csrfToken: string) {
  return apiMutate(
    `/api/v1/research/forms/links/${linkId}/reset-device`,
    'POST',
    z.object({ data: z.object({ id: z.number(), reset: z.boolean() }) }),
    { csrfToken },
  )
}

export function revokePublicLink(linkId: number, csrfToken: string) {
  return apiMutate(
    `/api/v1/research/forms/links/${linkId}/revoke`,
    'POST',
    z.object({ data: z.object({ id: z.number(), revoked_at: z.string() }) }),
    { csrfToken },
  )
}

export function formExportUrl(formId: number, format: 'csv' | 'json'): string {
  return `/api/v1/research/forms/${formId}/export?format=${format}`
}

export function fetchPublicForm(token: string): Promise<PublicFormState> {
  return apiGet(
    `/api/v1/public/forms/${encodeURIComponent(token)}`,
    z.object({ data: publicFormStateSchema }),
  )
}

export async function submitPublicForm(
  token: string,
  answers: Record<string, unknown>,
): Promise<PublicSubmitResult> {
  const response = await fetch(`/api/v1/public/forms/${encodeURIComponent(token)}/submit`, {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  })
  return z.object({ data: publicSubmitResultSchema }).parse(await readResponse(response)).data
}
