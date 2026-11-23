import type { z } from 'zod'
import { readResponse } from '@/lib/api/session'

type HttpMethod = 'POST' | 'PATCH' | 'PUT' | 'DELETE'

export async function apiGet<T>(url: string, schema: z.ZodType<{ data: T }>): Promise<T> {
  const response = await fetch(url, {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return schema.parse(await readResponse(response)).data
}

export async function apiMutate<T>(
  url: string,
  method: HttpMethod,
  schema: z.ZodType<{ data: T }>,
  options: { csrfToken: string; body?: unknown },
): Promise<T> {
  const headers: Record<string, string> = { 'X-CSRF-Token': options.csrfToken }
  const init: RequestInit = {
    method,
    credentials: 'same-origin',
    cache: 'no-store',
    headers,
  }
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    init.body = JSON.stringify(options.body)
  }
  const response = await fetch(url, init)
  return schema.parse(await readResponse(response)).data
}
