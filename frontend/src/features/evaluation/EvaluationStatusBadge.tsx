import { Badge } from '@/components/ui/badge'
import type { EvaluationStatus } from '@/lib/api/evaluation'

const STATUS_META: Record<
  EvaluationStatus,
  { label: string; variant: 'secondary' | 'default' | 'outline' }
> = {
  empty: { label: 'Belum tersedia', variant: 'outline' },
  draft: { label: 'Draf (sementara)', variant: 'secondary' },
  pending: { label: 'Menunggu kesepakatan (PM-19)', variant: 'secondary' },
  final: { label: 'Final terverifikasi', variant: 'default' },
}

export function EvaluationStatusBadge({ status }: { status: EvaluationStatus }) {
  const meta = STATUS_META[status]
  return <Badge variant={meta.variant}>{meta.label}</Badge>
}
