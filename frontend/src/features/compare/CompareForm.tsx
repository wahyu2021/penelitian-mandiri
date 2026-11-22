import { useState, type FormEvent } from 'react'
import { RotateCcw, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import type { SearchFilters } from '@/lib/api/search'

export type CompareFormValues = {
  q: string
  opd_id: string
  year: string
  status: string
  limit: string
}

type Props = {
  initial: CompareFormValues
  options?: SearchFilters
  optionsError: boolean
  retryOptions: () => void
  onCompare: (values: CompareFormValues) => void
  onClear: () => void
}

export function CompareForm({
  initial,
  options,
  optionsError,
  retryOptions,
  onCompare,
  onClear,
}: Props) {
  const [form, setForm] = useState(initial)

  function update(key: keyof CompareFormValues, value: string) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onCompare(form)
  }

  function clear() {
    setForm({ q: '', opd_id: '', year: '', status: '', limit: '10' })
    onClear()
  }

  return (
    <Card>
      <CardContent>
        <form onSubmit={submit} className="space-y-5">
          <div className="space-y-2">
            <label htmlFor="compare-query" className="text-sm font-medium">
              Kata kunci
            </label>
            <Input
              id="compare-query"
              type="search"
              value={form.q}
              onChange={(event) => update('q', event.target.value)}
              maxLength={200}
              placeholder="Contoh: pembangunan jembatan"
              className="h-10"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <label htmlFor="compare-opd" className="text-sm font-medium">
                OPD
              </label>
              <NativeSelect
                className="w-full"
                id="compare-opd"
                value={form.opd_id}
                onChange={(event) => update('opd_id', event.target.value)}
              >
                <NativeSelectOption value="">Semua OPD</NativeSelectOption>
                {options?.opds.map((opd) => (
                  <NativeSelectOption key={opd.id} value={String(opd.id)}>
                    {opd.name}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </div>
            <div className="space-y-2">
              <label htmlFor="compare-year" className="text-sm font-medium">
                Tahun
              </label>
              <Input
                id="compare-year"
                type="number"
                min={1900}
                max={2100}
                value={form.year}
                onChange={(event) => update('year', event.target.value)}
                placeholder="Semua tahun"
                className="h-10"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="compare-status" className="text-sm font-medium">
                Status
              </label>
              <NativeSelect
                className="w-full"
                id="compare-status"
                value={form.status}
                onChange={(event) => update('status', event.target.value)}
              >
                <NativeSelectOption value="">Semua status</NativeSelectOption>
                <NativeSelectOption value="1">Aktif</NativeSelectOption>
                <NativeSelectOption value="2">Nonaktif</NativeSelectOption>
                <NativeSelectOption value="3">Lainnya</NativeSelectOption>
              </NativeSelect>
            </div>
            <div className="space-y-2">
              <label htmlFor="compare-limit" className="text-sm font-medium">
                Hasil per metode
              </label>
              <NativeSelect
                className="w-full"
                id="compare-limit"
                value={form.limit}
                onChange={(event) => update('limit', event.target.value)}
              >
                {[5, 10, 20].map((limit) => (
                  <NativeSelectOption key={limit} value={String(limit)}>
                    {limit}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </div>
          </div>
          {optionsError && (
            <p role="alert" className="text-sm text-destructive">
              Pilihan OPD belum dapat dimuat.{' '}
              <button type="button" className="underline" onClick={retryOptions}>
                Coba lagi
              </button>
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button type="submit">
              <Search aria-hidden="true" /> Bandingkan
            </Button>
            <Button type="button" variant="outline" onClick={clear}>
              <RotateCcw aria-hidden="true" /> Bersihkan
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
