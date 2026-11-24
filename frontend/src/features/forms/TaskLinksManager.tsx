import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, Link2, RotateCcw, ShieldOff } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  type CreatedTaskLink,
  createTaskLink,
  fetchTaskLinks,
  resetTaskLinkDevice,
  revokeTaskLink,
  type TaskKind,
  type TaskLinkItem,
} from '@/lib/api/publicTasks'
import { ApiError } from '@/lib/api/session'
import { formatDateTimeId } from '@/lib/format'

const STATUS_META: Record<
  TaskLinkItem['status'],
  { label: string; variant: 'outline' | 'secondary' | 'default' | 'destructive' }
> = {
  unopened: { label: 'Belum dibuka', variant: 'outline' },
  claimed: { label: 'Terkunci di perangkat', variant: 'secondary' },
  submitted: { label: 'Sudah diserahkan', variant: 'default' },
  revoked: { label: 'Dicabut', variant: 'destructive' },
}

export function TaskLinksManager({
  taskKind,
  version,
  slot,
  userId,
  csrfToken,
  disabled = false,
}: {
  taskKind: TaskKind
  version?: string
  slot?: 1 | 2
  userId?: number
  csrfToken: string
  disabled?: boolean
}) {
  const queryClient = useQueryClient()
  const [latestLink, setLatestLink] = useState<CreatedTaskLink | null>(null)
  const [copied, setCopied] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const queryKey = ['research-task-links', taskKind, version ?? null] as const
  const linksQuery = useQuery({
    queryKey,
    queryFn: () => fetchTaskLinks({ task_kind: taskKind, version }),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey })

  const createMutation = useMutation({
    mutationFn: () =>
      createTaskLink(
        {
          task_kind: taskKind,
          version,
          slot,
          user_id: userId,
          lock_single_device: true,
        },
        csrfToken,
      ),
    onSuccess: (created) => {
      setErrorMsg(null)
      setLatestLink(created)
      setCopied(false)
      void invalidate()
    },
    onError: (err) => setErrorMsg(err instanceof ApiError ? err.message : 'Gagal membuat tautan.'),
  })

  const resetMutation = useMutation({
    mutationFn: (linkId: number) => resetTaskLinkDevice(linkId, csrfToken),
    onSuccess: () => void invalidate(),
    onError: (err) => setErrorMsg(err instanceof ApiError ? err.message : 'Gagal mereset tautan.'),
  })

  const revokeMutation = useMutation({
    mutationFn: (linkId: number) => revokeTaskLink(linkId, csrfToken),
    onSuccess: () => void invalidate(),
    onError: (err) => setErrorMsg(err instanceof ApiError ? err.message : 'Gagal mencabut tautan.'),
  })

  const matchingLinks = (linksQuery.data ?? []).filter((item) => {
    if (taskKind === 'relevance') {
      return item.target_version === version && item.target_slot === slot
    }
    return item.target_user_id === userId
  })

  const shareUrl = latestLink ? `${window.location.origin}${latestLink.public_path}` : ''

  return (
    <div className="space-y-2.5 rounded-md border bg-muted/20 p-3 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium text-muted-foreground">
          Tautan 1-perangkat tanpa login ({matchingLinks.length})
        </span>
        {!disabled && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={createMutation.isPending}
            onClick={() => {
              setErrorMsg(null)
              createMutation.mutate()
            }}
          >
            <Link2 aria-hidden="true" />
            {createMutation.isPending ? 'Membuat…' : 'Buat tautan 1-perangkat'}
          </Button>
        )}
      </div>

      {errorMsg && (
        <p role="alert" className="text-destructive">
          {errorMsg}
        </p>
      )}

      {latestLink && (
        <Alert role="status">
          <AlertTitle className="text-xs">Tautan baru siap dibagikan</AlertTitle>
          <AlertDescription className="mt-1.5 space-y-2">
            <p className="text-xs">
              Salin tautan berikut sekarang. Tautan ini otomatis terkunci pada perangkat pertama
              yang membukanya.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <Input
                readOnly
                aria-label="URL tautan tugas"
                value={shareUrl}
                className="h-8 font-mono text-xs sm:max-w-md"
              />
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  void navigator.clipboard?.writeText(shareUrl)
                  setCopied(true)
                }}
              >
                <Copy aria-hidden="true" /> {copied ? 'Tersalin' : 'Salin tautan'}
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {matchingLinks.length > 0 && (
        <div className="space-y-1.5">
          {matchingLinks.map((link) => {
            const meta = STATUS_META[link.status]
            return (
              <div
                key={link.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded border bg-background px-2.5 py-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono">{link.token_preview}</span>
                  <Badge variant={meta.variant}>{meta.label}</Badge>
                  <span className="text-muted-foreground">{formatDateTimeId(link.created_at)}</span>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  {link.lock_single_device && link.status === 'claimed' && (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={resetMutation.isPending}
                      onClick={() => resetMutation.mutate(link.id)}
                    >
                      <RotateCcw aria-hidden="true" /> Reset perangkat
                    </Button>
                  )}
                  {link.status !== 'revoked' && link.status !== 'submitted' && (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={revokeMutation.isPending}
                      onClick={() => revokeMutation.mutate(link.id)}
                    >
                      <ShieldOff aria-hidden="true" /> Cabut
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
