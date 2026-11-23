import { z } from 'zod'
import { readResponse } from '@/lib/api/session'

const adminUserSchema = z.object({
  id: z.number().int().positive(),
  username: z.string(),
  role: z.enum(['admin', 'petugas']),
  is_active: z.boolean(),
  created_at: z.string(),
})

const usersListSchema = z.object({
  data: z.object({
    users: z.array(adminUserSchema),
  }),
})

const singleUserSchema = z.object({
  data: z.object({
    user: adminUserSchema,
  }),
})

const activityItemSchema = z.object({
  id: z.number().int().positive(),
  user_id: z.number().int().positive().nullable(),
  username: z.string().nullable(),
  action: z.string(),
  detail: z.string().nullable(),
  created_at: z.string(),
})

const activityListSchema = z.object({
  data: z.object({
    items: z.array(activityItemSchema),
  }),
})

export type AdminUser = z.infer<typeof adminUserSchema>
export type ActivityLogItem = z.infer<typeof activityItemSchema>

export async function listAdminUsers(): Promise<AdminUser[]> {
  const response = await fetch('/api/v1/admin/users', {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return usersListSchema.parse(await readResponse(response)).data.users
}

export async function createAdminUser(
  payload: { username: string; role: 'admin' | 'petugas'; password: string },
  csrfToken: string,
): Promise<AdminUser> {
  const response = await fetch('/api/v1/admin/users', {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify(payload),
  })
  return singleUserSchema.parse(await readResponse(response)).data.user
}

export async function updateAdminUserStatus(
  userId: number,
  isActive: boolean,
  csrfToken: string,
): Promise<AdminUser> {
  const response = await fetch(`/api/v1/admin/users/${userId}/status`, {
    method: 'PATCH',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ is_active: isActive }),
  })
  return singleUserSchema.parse(await readResponse(response)).data.user
}

export async function resetAdminUserPassword(
  userId: number,
  password: string,
  csrfToken: string,
): Promise<AdminUser> {
  const response = await fetch(`/api/v1/admin/users/${userId}/reset-password`, {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ password }),
  })
  return singleUserSchema.parse(await readResponse(response)).data.user
}

export async function listActivityLogs(
  filters: { action?: string; username?: string; limit?: number } = {},
): Promise<ActivityLogItem[]> {
  const params = new URLSearchParams()
  if (filters.action?.trim()) params.set('action', filters.action.trim())
  if (filters.username?.trim()) params.set('username', filters.username.trim())
  if (filters.limit) params.set('limit', String(filters.limit))
  const query = params.toString()
  const response = await fetch(`/api/v1/admin/activity${query ? `?${query}` : ''}`, {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return activityListSchema.parse(await readResponse(response)).data.items
}
