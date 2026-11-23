import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

export function ErrorStateCard({
  title,
  description,
  onRetry,
}: {
  title: string
  description?: string
  onRetry: () => void
}) {
  return (
    <Card role="alert">
      <CardContent className="space-y-3">
        <p className="font-medium">{title}</p>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
        <Button variant="outline" onClick={onRetry}>
          <RefreshCw aria-hidden="true" /> Coba lagi
        </Button>
      </CardContent>
    </Card>
  )
}
