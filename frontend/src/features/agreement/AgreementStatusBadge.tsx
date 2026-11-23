import { Badge } from '@/components/ui/badge'
import type { AgreementStatus } from '@/lib/api/agreement'

const STATUS_META: Record<
  AgreementStatus,
  { label: string; variant: 'secondary' | 'default' | 'outline' }
> = {
  pending: { label: 'Tertunda (belum lengkap)', variant: 'secondary' },
  complete: { label: 'Lengkap & final', variant: 'default' },
  complete_kappa_undefined: { label: 'Lengkap (kappa tak terdefinisi)', variant: 'outline' },
}

export function AgreementStatusBadge({ status }: { status: AgreementStatus }) {
  const meta = STATUS_META[status]
  return <Badge variant={meta.variant}>{meta.label}</Badge>
}
