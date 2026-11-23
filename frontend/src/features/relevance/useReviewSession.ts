import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { sessionKey } from '@/features/auth/useSession'
import { ApiError } from '@/lib/api/session'

export function useReviewExpiry(...errors: (Error | null)[]) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const expired = errors.some((error) => error instanceof ApiError && error.status === 401)
  useEffect(() => {
    if (expired) {
      queryClient.removeQueries({ queryKey: sessionKey })
      navigate('/login', { replace: true })
    }
  }, [expired, navigate, queryClient])
}

export function reviewError(error: Error, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}
