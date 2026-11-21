import { useQuery } from '@tanstack/react-query'
import { getSession } from '@/lib/api/session'

export const sessionKey = ['session'] as const

export function useSession() {
  return useQuery({
    queryKey: sessionKey,
    queryFn: getSession,
    staleTime: 0,
    refetchOnWindowFocus: true,
  })
}
