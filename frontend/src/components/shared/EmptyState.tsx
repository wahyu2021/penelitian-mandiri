import { Card, CardContent } from '@/components/ui/card'

export function EmptyState({ message, asCard = false }: { message: string; asCard?: boolean }) {
  if (asCard) {
    return (
      <Card>
        <CardContent>
          <p className="text-sm text-muted-foreground">{message}</p>
        </CardContent>
      </Card>
    )
  }

  return <p className="py-2 text-sm text-muted-foreground">{message}</p>
}
