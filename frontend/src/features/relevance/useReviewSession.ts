import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { ApiError } from '@/lib/api/session'

export function useReviewExpiry(...errors: (Error | null)[]) {
  useUnauthorizedRedirect(errors)
}

export function reviewError(error: Error, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}
