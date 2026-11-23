import { Button } from '@/components/ui/button'

export function PaginationControls({
  offset,
  limit,
  total,
  onPage,
}: {
  offset: number
  limit: number
  total: number
  onPage: (offset: number) => void
}) {
  if (total <= limit) return null

  return (
    <div className="flex items-center justify-end gap-2">
      <Button
        variant="outline"
        disabled={offset === 0}
        onClick={() => onPage(Math.max(0, offset - limit))}
      >
        Sebelumnya
      </Button>
      <Button
        variant="outline"
        disabled={offset + limit >= total}
        onClick={() => onPage(offset + limit)}
      >
        Berikutnya
      </Button>
    </div>
  )
}
