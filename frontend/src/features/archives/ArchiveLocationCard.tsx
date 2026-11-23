import { MapPin } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { ArchiveDetail } from '@/lib/api/archives'

function display(value: string | null) {
  return value === null || value === '' ? 'Tidak tersedia' : value
}

function LocationCell({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-lg border border-border bg-stone-50/70 px-3 py-2.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-words text-sm font-semibold">{display(value)}</dd>
    </div>
  )
}

export function ArchiveLocationCard({ location }: { location: ArchiveDetail['location'] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2 className="flex items-center gap-2">
            <MapPin aria-hidden="true" className="size-4" /> Lokasi fisik
          </h2>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <LocationCell label="Blok" value={location.block} />
          <LocationCell label="Rak" value={location.rack} />
          <LocationCell label="Baris" value={location.row} />
          <LocationCell label="Nomor boks" value={location.box_number} />
        </dl>
        <p className="mt-3 text-xs text-muted-foreground">
          Lokasi mengikuti data yang tersedia pada salinan arsip.
        </p>
      </CardContent>
    </Card>
  )
}
