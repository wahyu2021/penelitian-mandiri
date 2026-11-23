import { Link } from 'react-router'
import { EmptyState } from '@/components/shared/EmptyState'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Dashboard } from '@/lib/api/dashboard'

export function RecentArchivesCard({ items }: { items: Dashboard['recent'] }) {
  return (
    <Card>
      <CardHeader className="border-b border-border">
        <CardTitle>
          <h2>Arsip terakhir dalam data</h2>
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Berdasarkan ID arsip, bukan tanggal dokumen.
        </p>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <EmptyState message="Belum ada arsip dalam salinan data." />
        ) : (
          <ol className="divide-y divide-border">
            {items.map((item) => (
              <li key={item.id}>
                <Link
                  to={`/app/archives/${item.id}`}
                  className="-mx-2 flex flex-col gap-1 rounded-lg px-2 py-3 text-sm transition-colors hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary sm:flex-row sm:items-start sm:gap-4"
                >
                  <span className="w-16 shrink-0 font-mono text-xs font-medium text-primary">
                    #{item.id}
                  </span>
                  <span className="min-w-0 flex-1 space-y-1">
                    <span className="block break-words text-foreground">
                      {item.summary_raw || 'Ringkasan tidak tersedia'}
                    </span>
                    {item.opd_name && (
                      <span className="block text-xs text-muted-foreground">{item.opd_name}</span>
                    )}
                  </span>
                  <span className="shrink-0 text-muted-foreground">
                    {item.year ?? 'Tahun tidak tersedia'}
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  )
}
