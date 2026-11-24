import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Copy, Link2, RotateCcw, ShieldOff } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  type CreatedPublicLink,
  type FormDetail,
  generatePublicLink,
  resetLinkDevice,
  revokePublicLink,
} from '@/lib/api/publicForms'
import { ApiError } from '@/lib/api/session'
import { formatDateTimeId } from '@/lib/format'

const STATUS_BADGE: Record<
  FormDetail['links'][number]['status'],
  { label: string; variant: 'outline' | 'secondary' | 'default' | 'destructive' }
> = {
  unopened: { label: 'Belum dibuka', variant: 'outline' },
  claimed: { label: 'Terkunci di perangkat', variant: 'secondary' },
  submitted: { label: 'Sudah dikirim', variant: 'default' },
  revoked: { label: 'Dicabut', variant: 'destructive' },
}

export function FormLinksCard({
  detail,
  csrfToken,
  onChanged,
}: {
  detail: FormDetail
  csrfToken: string
  onChanged: () => void
}) {
  const nextIndex = detail.links.length + 1
  const [participantCode, setParticipantCode] = useState(`P${String(nextIndex).padStart(2, '0')}`)
  const [participantRole, setParticipantRole] = useState<'petugas' | 'admin'>('petugas')
  const [lockSingleDevice, setLockSingleDevice] = useState(true)
  const [latestLink, setLatestLink] = useState<CreatedPublicLink | null>(null)
  const [copied, setCopied] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const createMutation = useMutation({
    mutationFn: () =>
      generatePublicLink(
        detail.form.id,
        {
          participant_code: participantCode,
          participant_role: participantRole,
          lock_single_device: lockSingleDevice,
        },
        csrfToken,
      ),
    onSuccess: (created) => {
      setErrorMsg(null)
      setLatestLink(created)
      setCopied(false)
      setParticipantCode(`P${String(detail.links.length + 2).padStart(2, '0')}`)
      onChanged()
    },
    onError: (err) => setErrorMsg(err instanceof ApiError ? err.message : 'Gagal membuat tautan.'),
  })

  const resetMutation = useMutation({
    mutationFn: (linkId: number) => resetLinkDevice(linkId, csrfToken),
    onSuccess: onChanged,
  })

  const revokeMutation = useMutation({
    mutationFn: (linkId: number) => revokePublicLink(linkId, csrfToken),
    onSuccess: onChanged,
  })

  const shareUrl = latestLink ? `${window.location.origin}${latestLink.public_path}` : ''

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tautan publik per peserta ({detail.links.length})</CardTitle>
        <CardDescription>
          Generate 1 tautan unik untuk setiap responden. Saat kunci perangkat aktif, tautan otomatis
          terkunci ke HP/browser pertama yang membukanya.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        <form
          className="grid gap-3 sm:grid-cols-[1fr_10rem_auto] sm:items-end"
          onSubmit={(event) => {
            event.preventDefault()
            setErrorMsg(null)
            createMutation.mutate()
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="link-participant-code">Kode peserta anonim</Label>
            <Input
              id="link-participant-code"
              value={participantCode}
              onChange={(e) => setParticipantCode(e.target.value)}
              placeholder="Mis. P01"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="link-participant-role">Peran peserta</Label>
            <Select
              value={participantRole}
              onValueChange={(v) => setParticipantRole(v as 'petugas' | 'admin')}
            >
              <SelectTrigger id="link-participant-role" aria-label="Peran peserta">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="petugas">Petugas</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button type="submit" disabled={createMutation.isPending}>
            <Link2 aria-hidden="true" />
            {createMutation.isPending ? 'Membuat…' : 'Generate tautan'}
          </Button>

          <div className="flex items-center gap-2 sm:col-span-3">
            <Checkbox
              id="link-lock-device"
              checked={lockSingleDevice}
              onCheckedChange={(checked) => setLockSingleDevice(checked === true)}
            />
            <Label htmlFor="link-lock-device" className="text-xs font-normal">
              Kunci ke 1 perangkat (browser pertama yang membuka tautan)
            </Label>
          </div>
        </form>

        {errorMsg && (
          <p role="alert" className="text-xs text-destructive">
            {errorMsg}
          </p>
        )}

        {latestLink && (
          <Alert role="status">
            <AlertTitle>Tautan baru siap dibagikan untuk {latestLink.participant_code}</AlertTitle>
            <AlertDescription className="mt-2 space-y-2">
              <p className="text-xs">
                Salin tautan berikut sekarang. Demi keamanan, token penuh tidak disimpan ulang di
                database.
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <Input
                  readOnly
                  aria-label="URL tautan publik baru"
                  value={shareUrl}
                  className="font-mono text-xs sm:max-w-md"
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

        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Kode</TableHead>
                <TableHead>Peran</TableHead>
                <TableHead>Token</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Dibuat</TableHead>
                <TableHead className="text-right">Aksi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {detail.links.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    Belum ada tautan yang diterbitkan untuk formulir ini.
                  </TableCell>
                </TableRow>
              ) : (
                detail.links.map((link) => {
                  const meta = STATUS_BADGE[link.status]
                  return (
                    <TableRow key={link.id}>
                      <TableCell className="font-medium">{link.participant_code}</TableCell>
                      <TableCell>{link.participant_role}</TableCell>
                      <TableCell className="font-mono text-xs">{link.token_preview}</TableCell>
                      <TableCell>
                        <Badge variant={meta.variant}>{meta.label}</Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDateTimeId(link.created_at)}
                      </TableCell>
                      <TableCell className="space-x-1.5 text-right whitespace-nowrap">
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
                        {link.status !== 'revoked' && (
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
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
