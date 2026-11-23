import { Card, CardContent } from '@/components/ui/card'

export function ForbiddenCard({ message }: { message: string }) {
  return (
    <main className="py-5 sm:py-6">
      <Card role="alert">
        <CardContent>
          <h1 className="text-xl font-semibold">403 · Akses ditolak</h1>
          <p className="mt-2 text-sm text-muted-foreground">{message}</p>
        </CardContent>
      </Card>
    </main>
  )
}
