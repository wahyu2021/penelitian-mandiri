import { Skeleton } from '@/components/ui/skeleton'

export function LoadingState({
  label,
  rows = 2,
  rowClassName = 'h-16 w-full',
}: {
  label: string
  rows?: number
  rowClassName?: string
}) {
  return (
    <div role="status" aria-label={label} className="space-y-3">
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className={rowClassName} />
      ))}
    </div>
  )
}
