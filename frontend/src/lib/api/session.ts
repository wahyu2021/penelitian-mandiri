import { z } from 'zod'

const userSchema = z.object({
  id: z.number(),
  username: z.string(),
  role: z.enum(['admin', 'petugas']),
})

const sessionSchema = z.object({
  data: z.object({
    authenticated: z.boolean(),
    user: userSchema.nullable(),
    csrf_token: z.string(),
  }),
})

export type Session = z.infer<typeof sessionSchema>['data']

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function readResponse(response: Response): Promise<unknown> {
  const body: unknown = await response.json()
  if (!response.ok) {
    const parsed = z.object({ error: z.object({ message: z.string() }) }).safeParse(body)
    throw new ApiError(
      response.status,
      parsed.success ? parsed.data.error.message : 'Permintaan gagal.',
    )
  }
  return body
}

export async function getSession(): Promise<Session> {
  const response = await fetch('/api/v1/session', { credentials: 'same-origin', cache: 'no-store' })
  return sessionSchema.parse(await readResponse(response)).data
}

export async function login(
  username: string,
  password: string,
  csrfToken: string,
): Promise<Session> {
  const response = await fetch('/api/v1/session', {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ username, password }),
  })
  return sessionSchema.parse(await readResponse(response)).data
}

export async function logout(csrfToken: string): Promise<void> {
  const response = await fetch('/api/v1/session', {
    method: 'DELETE',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'X-CSRF-Token': csrfToken },
  })
  await readResponse(response)
}
