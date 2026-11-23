import type { ReactNode } from 'react'
import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string
  title: string
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-muted-foreground">{eyebrow}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
        {description && <p className="mt-2 text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions}
    </header>
  )
}

export function ForbiddenCard({ message }: { message: string }) {
  return (
    <main className="py-8 sm:py-10">
      <Card role="alert">
        <CardContent>
          <h1 className="text-xl font-semibold">403 · Akses ditolak</h1>
          <p className="mt-2 text-sm text-muted-foreground">{message}</p>
        </CardContent>
      </Card>
    </main>
  )
}

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
