import { z } from 'zod'
import { apiGet, apiMutate } from '@/lib/api/client'

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

export function listAdminUsers(): Promise<AdminUser[]> {
  return apiGet('/api/v1/admin/users', usersListSchema).then((data) => data.users)
}

export function createAdminUser(
  payload: { username: string; role: 'admin' | 'petugas'; password: string },
  csrfToken: string,
): Promise<AdminUser> {
  return apiMutate('/api/v1/admin/users', 'POST', singleUserSchema, {
    csrfToken,
    body: payload,
  }).then((data) => data.user)
}

export function updateAdminUserStatus(
  userId: number,
  isActive: boolean,
  csrfToken: string,
): Promise<AdminUser> {
  return apiMutate(`/api/v1/admin/users/${userId}/status`, 'PATCH', singleUserSchema, {
    csrfToken,
    body: { is_active: isActive },
  }).then((data) => data.user)
}

export function resetAdminUserPassword(
  userId: number,
  password: string,
  csrfToken: string,
): Promise<AdminUser> {
  return apiMutate(`/api/v1/admin/users/${userId}/reset-password`, 'POST', singleUserSchema, {
    csrfToken,
    body: { password },
  }).then((data) => data.user)
}

export function listActivityLogs(
  filters: { action?: string; username?: string; limit?: number } = {},
): Promise<ActivityLogItem[]> {
  const params = new URLSearchParams()
  if (filters.action?.trim()) params.set('action', filters.action.trim())
  if (filters.username?.trim()) params.set('username', filters.username.trim())
  if (filters.limit) params.set('limit', String(filters.limit))
  const query = params.toString()
  return apiGet(`/api/v1/admin/activity${query ? `?${query}` : ''}`, activityListSchema).then(
    (data) => data.items,
  )
}
