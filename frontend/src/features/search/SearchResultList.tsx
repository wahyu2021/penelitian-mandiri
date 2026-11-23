import { EmptyState } from '@/components/shared/EmptyState'
import { PaginationControls } from '@/components/shared/PaginationControls'
import { SearchResultCard } from '@/features/search/SearchResultCard'
import type { SearchResults } from '@/lib/api/search'

export function SearchResultList({
  data,
  onPage,
  returnSearch,
}: {
  data: SearchResults
  onPage: (offset: number) => void
  returnSearch: string
}) {
  const { limit, offset, total } = data.pagination
  const start = data.items.length === 0 ? 0 : offset + 1
  const end = Math.min(offset + data.items.length, total)

  return (
    <section aria-labelledby="results-title" className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="results-title" className="text-lg font-semibold">
            Hasil pencarian
          </h2>
          <p className="text-sm text-muted-foreground">{total} arsip cocok</p>
        </div>
        {data.items.length > 0 && (
          <p className="text-sm text-muted-foreground">
            Menampilkan {start}–{end} dari {total}
          </p>
        )}
      </div>
      <p className="text-xs leading-5 text-muted-foreground">
        {data.method === 'like'
          ? 'Menampilkan kecocokan kata tepat, tanpa peringkat kemiripan.'
          : 'Diurutkan berdasarkan kemiripan kata kunci; skor hanya untuk urutan hasil.'}
      </p>
      {data.items.length === 0 ? (
        <EmptyState
          asCard
          message={
            total === 0
              ? 'Tidak ada arsip yang cocok. Coba kata kunci atau filter lain.'
              : 'Halaman ini tidak berisi hasil. Kembali ke halaman sebelumnya.'
          }
        />
      ) : (
        <div className="space-y-3">
          {data.items.map((item) => (
            <SearchResultCard
              key={item.id}
              item={item}
              query={data.query}
              method={data.method}
              returnSearch={returnSearch}
            />
          ))}
        </div>
      )}
      <PaginationControls offset={offset} limit={limit} total={total} onPage={onPage} />
    </section>
  )
}
