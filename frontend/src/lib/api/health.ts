import { z } from 'zod'

const healthResponse = z.object({ data: z.object({ status: z.literal('ok') }) })

export async function getHealth(): Promise<'ok'> {
  const response = await fetch('/api/v1/health', { credentials: 'same-origin', cache: 'no-store' })
  if (!response.ok) throw new Error('Layanan tidak dapat dihubungi.')
  const payload: unknown = await response.json()
  return healthResponse.parse(payload).data.status
}
