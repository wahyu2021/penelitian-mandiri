import { useState, type FormEvent } from 'react'
import { RotateCcw, Search } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import type { SearchFilters } from '@/lib/api/search'

export type FormValues = {
  q: string
  opd_id: string
  year: string
  status: string
  limit: string
}

type SearchFormProps = {
  initial: FormValues
  options?: SearchFilters
  optionsError: boolean
  retryOptions: () => void
  onSearch: (values: FormValues) => void
  onClear: () => void
}

export function SearchForm({
  initial,
  options,
  optionsError,
  retryOptions,
  onSearch,
  onClear,
}: SearchFormProps) {
  const [form, setForm] = useState(initial)

  function update(key: keyof FormValues, value: string) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSearch(form)
  }

  function clear() {
    setForm({ q: '', opd_id: '', year: '', status: '', limit: '20' })
    onClear()
  }

  return (
    <Card>
      <CardContent>
        <form onSubmit={submit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="search-query">Kata kunci</Label>
            <Input
              id="search-query"
              type="search"
              value={form.q}
              onChange={(event) => update('q', event.target.value)}
              maxLength={200}
              placeholder="Contoh: pembangunan jembatan, nomor SPM, atau nama pihak"
              className="h-10"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="filter-opd">OPD</Label>
              <NativeSelect
                className="w-full"
                id="filter-opd"
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
              <Label htmlFor="filter-year">Tahun</Label>
              <Input
                id="filter-year"
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
              <Label htmlFor="filter-status">Status</Label>
              <NativeSelect
                className="w-full"
                id="filter-status"
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
              <Label htmlFor="filter-limit">Hasil per halaman</Label>
              <NativeSelect
                className="w-full"
                id="filter-limit"
                value={form.limit}
                onChange={(event) => update('limit', event.target.value)}
              >
                {[10, 20, 50].map((limit) => (
                  <NativeSelectOption key={limit} value={String(limit)}>
                    {limit}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </div>
          </div>
          {optionsError && (
            <Alert variant="destructive">
              <AlertDescription className="flex flex-wrap items-center gap-2">
                <span>Pilihan OPD belum dapat dimuat.</span>
                <button type="button" className="underline" onClick={retryOptions}>
                  Coba lagi
                </button>
              </AlertDescription>
            </Alert>
          )}
          <div className="flex flex-wrap gap-2">
            <Button type="submit">
              <Search aria-hidden="true" /> Cari arsip
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
