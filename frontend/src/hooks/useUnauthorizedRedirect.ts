import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { sessionKey } from '@/features/auth/useSession'
import { ApiError } from '@/lib/api/session'

export function useUnauthorizedRedirect(errors: readonly unknown[]) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const hasUnauthorized = errors.some((error) => error instanceof ApiError && error.status === 401)

  useEffect(() => {
    if (hasUnauthorized) {
      queryClient.removeQueries({ queryKey: sessionKey })
      navigate('/login', { replace: true })
    }
  }, [hasUnauthorized, queryClient, navigate])
}
