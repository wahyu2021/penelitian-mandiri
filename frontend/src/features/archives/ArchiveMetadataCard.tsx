import { Info } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { ArchiveDetail } from '@/lib/api/archives'
import { formatCurrencyIdr } from '@/lib/format'

function display(value: string | number | null) {
  return value === null || value === '' ? 'Tidak tersedia' : String(value)
}

function MetadataRow({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="grid gap-1 border-t border-border py-3 first:border-t-0 sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-4">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words text-sm font-medium">{display(value)}</dd>
    </div>
  )
}

export function ArchiveMetadataCard({ extraction }: { extraction: ArchiveDetail['extraction'] }) {
  const type = extraction.spm_type

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>Metadata hasil ekstraksi</h2>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <dl>
          <MetadataRow label="Nomor SPM" value={extraction.spm_number} />
          <MetadataRow
            label="Jenis SPM"
            value={type ? `${type.code}${type.label ? ` · ${type.label}` : ''}` : null}
          />
          <MetadataRow label="Status jenis SPM" value={type?.confidence ?? null} />
          <MetadataRow label="Nomor SP2D" value={extraction.sp2d_number} />
          <MetadataRow label="Tanggal dokumen" value={extraction.document_date} />
          <MetadataRow
            label="Nominal"
            value={extraction.amount_rp === null ? null : formatCurrencyIdr(extraction.amount_rp)}
          />
          <MetadataRow label="Pihak" value={extraction.party_name} />
        </dl>
        {type?.confidence === 'dugaan' && (
          <Alert role="note" className="mt-3 border-amber-200 bg-amber-50 text-amber-950">
            <AlertDescription className="text-amber-950">
              Jenis SPM masih dugaan. Cocokkan dengan ringkasan asli.
            </AlertDescription>
          </Alert>
        )}
        <p className="mt-4 flex items-start gap-2 text-xs leading-5 text-muted-foreground">
          <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          Nilai ini dibuat oleh ekstraktor. Bandingkan dengan ringkasan asli sebelum dipakai sebagai
          bukti.
        </p>
      </CardContent>
    </Card>
  )
}
