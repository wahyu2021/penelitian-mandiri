import { useState, type FormEvent } from 'react'
import { RotateCcw, Search } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { SearchFilters } from '@/lib/api/search'

const ALL_VALUE = '__all__'

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
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="filter-opd">OPD</Label>
              <Select
                value={form.opd_id || ALL_VALUE}
                onValueChange={(value) => update('opd_id', value === ALL_VALUE ? '' : value)}
              >
                <SelectTrigger id="filter-opd" className="w-full">
                  <SelectValue placeholder="Semua OPD" />
                </SelectTrigger>
                <SelectContent position="popper">
                  <SelectItem value={ALL_VALUE}>Semua OPD</SelectItem>
                  {options?.opds.map((opd) => (
                    <SelectItem key={opd.id} value={String(opd.id)}>
                      {opd.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="filter-status">Status</Label>
              <Select
                value={form.status || ALL_VALUE}
                onValueChange={(value) => update('status', value === ALL_VALUE ? '' : value)}
              >
                <SelectTrigger id="filter-status" className="w-full">
                  <SelectValue placeholder="Semua status" />
                </SelectTrigger>
                <SelectContent position="popper">
                  <SelectItem value={ALL_VALUE}>Semua status</SelectItem>
                  <SelectItem value="1">Aktif</SelectItem>
                  <SelectItem value="2">Nonaktif</SelectItem>
                  <SelectItem value="3">Lainnya</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="filter-limit">Hasil per halaman</Label>
              <Select value={form.limit} onValueChange={(value) => update('limit', value)}>
                <SelectTrigger id="filter-limit" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent position="popper">
                  {[10, 20, 50].map((limit) => (
                    <SelectItem key={limit} value={String(limit)}>
                      {limit}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
