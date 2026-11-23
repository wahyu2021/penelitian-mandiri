import { useState, type FormEvent } from 'react'
import { ErrorStateCard } from '@/components/shared/PageLayout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { ActivityLogItem } from '@/lib/api/adminUsers'
import { formatDateTimeId } from '@/lib/format'

export type ActivityFilters = {
  action?: string
  username?: string
}

export function ActivityLogCard({
  items,
  isPending,
  isError,
  onRetry,
  appliedFilters,
  onApplyFilters,
}: {
  items?: ActivityLogItem[]
  isPending: boolean
  isError: boolean
  onRetry: () => void
  appliedFilters: ActivityFilters
  onApplyFilters: (filters: ActivityFilters) => void
}) {
  const [draftAction, setDraftAction] = useState(appliedFilters.action ?? '')
  const [draftUsername, setDraftUsername] = useState(appliedFilters.username ?? '')

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onApplyFilters({
      action: draftAction.trim() || undefined,
      username: draftUsername.trim() || undefined,
    })
  }

  return (
    <Card>
      <CardHeader className="border-b border-border">
        <CardTitle>
          <h2>Log aktivitas</h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="filter-action" className="text-xs">
              Filter aksi
            </Label>
            <Input
              id="filter-action"
              value={draftAction}
              onChange={(event) => setDraftAction(event.target.value)}
              placeholder="mis. login, user_create"
              className="h-9 w-48"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="filter-username" className="text-xs">
              Filter pengguna
            </Label>
            <Input
              id="filter-username"
              value={draftUsername}
              onChange={(event) => setDraftUsername(event.target.value)}
              placeholder="Nama pengguna"
              className="h-9 w-44"
            />
          </div>
          <Button type="submit" variant="outline" size="sm">
            Terapkan
          </Button>
          {(appliedFilters.action || appliedFilters.username) && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setDraftAction('')
                setDraftUsername('')
                onApplyFilters({})
              }}
            >
              Bersihkan
            </Button>
          )}
        </form>

        {isPending ? (
          <div role="status" aria-label="Memuat log aktivitas" className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : isError ? (
          <ErrorStateCard title="Log aktivitas belum dapat dimuat." onRetry={onRetry} />
        ) : !items || items.length === 0 ? (
          <p className="text-sm text-muted-foreground">Belum ada catatan aktivitas yang cocok.</p>
        ) : (
          <Table className="min-w-[36rem]">
            <TableHeader>
              <TableRow>
                <TableHead>Waktu</TableHead>
                <TableHead>Pengguna</TableHead>
                <TableHead>Aksi</TableHead>
                <TableHead>Detail</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDateTimeId(entry.created_at)}
                  </TableCell>
                  <TableCell>{entry.username ?? 'Sistem'}</TableCell>
                  <TableCell className="font-mono text-xs">{entry.action}</TableCell>
                  <TableCell className="whitespace-normal break-all text-xs text-muted-foreground">
                    {entry.detail || '—'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
